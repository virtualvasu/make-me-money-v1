# stages/news_discovery.py
import urllib.parse
import feedparser
import json
import time
from bs4 import BeautifulSoup
import os
from datetime import datetime, timezone
from groq import Groq

from config.settings import settings
from utils.logger import log
from utils.http import get_session
from googlenewsdecoder import new_decoderv1
from stages import articles, summariser

NEWS_DISCOVERY_QUERIES = [
    "NSE stock rally breakout 2026",
    "Indian stock market multibagger catalyst",
    "NSE stock order win expansion 2026",
    "India defence telecom stock growth",
    "NSE stock quarterly results beat estimate",
    "Indian stock sector rotation momentum",
]

def discover() -> list:
    log.info("Starting broad news discovery scan...")
    
    all_articles = []
    seen_urls = set()
    now = datetime.now(timezone.utc)
    
    # 1. Broad News Scan
    for query in NEWS_DISCOVERY_QUERIES:
        log.info(f"Scanning news for topic: {query}")
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]: # Top 5 per query
            link = entry.link
            try:
                decoded = new_decoderv1(link)
                if decoded.get('status') and decoded.get('decoded_url'):
                    link = decoded['decoded_url']
            except:
                pass
                
            if link in seen_urls:
                continue
                
            published_parsed = entry.get('published_parsed')
            if published_parsed:
                dt = datetime.fromtimestamp(time.mktime(published_parsed), timezone.utc)
                if (now - dt).days > 14: # only recent news
                    continue
                    
            seen_urls.add(link)
            all_articles.append({
                "title": entry.title,
                "url": link,
                "published": entry.get('published', '')
            })
            
    if not all_articles:
        log.warning("No recent articles found in discovery scan.")
        return []
        
    # Extract text (reuse articles stage but wrap it in our expected dict format)
    log.info(f"Extracting text from {len(all_articles)} discovery articles...")
    mock_rss_data = {"DISCOVERY": all_articles}
    extracted_data = articles.extract_all(mock_rss_data)
    valid_articles = [a for a in extracted_data["DISCOVERY"] if not a.get("extraction_failed")]
    
    # 2. Extract Stock Symbols using Groq
    log.info("Extracting stock symbols from news using Groq...")
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'news_discovery.txt')
    with open(prompt_path, "r") as f:
        prompt_template = f.read()
        
    articles_json = json.dumps([{"title": a["title"], "text_excerpt": a["text_excerpt"], "url": a["url"]} for a in valid_articles])
    prompt = prompt_template.replace("{articles_json}", articles_json)
    
    discovered_stocks = []
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.GROQ_MODEL,
            temperature=0.1
        )
        response_text = chat_completion.choices[0].message.content
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()
            
        discovered_stocks = json.loads(response_text)
        log.info(f"Groq extracted {len(discovered_stocks)} potential stock catalysts.")
    except Exception as e:
        log.error(f"Error extracting stocks via Groq: {e}")
        return []
        
    # 3. Screener Validation
    log.info("Validating discovered stocks via Screener.in...")
    session = get_session(with_screener_auth=True)
    validated_stocks = []
    
    for stock in discovered_stocks:
        symbol = stock.get("symbol")
        if not symbol:
            continue
            
        url = f"https://www.screener.in/company/{symbol}/consolidated/"
        resp = session.get(url)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            ratios = soup.find('div', {'class': 'company-ratios'})
            stats = {}
            if ratios:
                for li in ratios.find_all('li'):
                    name = li.find('span', {'class': 'name'})
                    value = li.find('span', {'class': 'number'})
                    if name and value:
                        # Clean up keys: "Market Cap" -> "Market Capitalization"
                        clean_name = name.text.replace('\n', '').strip()
                        clean_val = value.text.replace(',', '').replace('%', '').strip()
                        try:
                            stats[clean_name] = float(clean_val)
                        except ValueError:
                            stats[clean_name] = clean_val
                            
            if stats:
                stock['cmp'] = stats.get('Current Price', 0)
                stock['indicators'] = {
                    'rsi': stats.get('RSI', None), # might not be there depending on custom columns, but we try
                    'pe': stats.get('Stock P/E', None),
                    'market_cap': stats.get('Market Cap', None),
                    'roce': stats.get('ROCE', None)
                }
                # Create mock tech score based on what we have
                score = 0
                if stock['indicators']['pe'] and isinstance(stock['indicators']['pe'], (int, float)) and stock['indicators']['pe'] < 30: score += 10
                if stock['indicators']['roce'] and isinstance(stock['indicators']['roce'], (int, float)) and stock['indicators']['roce'] > 15: score += 10
                stock['tech_score'] = score
                stock['tech_confidence'] = "MEDIUM" # Default
                stock['news'] = [{"title": stock.get('catalyst', ''), "url": stock.get('url', ''), "bullets": [stock.get('catalyst', '')]}]
                stock['brief_reason'] = stock.get('catalyst', '')
                validated_stocks.append(stock)
                log.info(f"Validated {symbol}: {stats.get('Current Price')}")
            else:
                log.debug(f"Could not parse stats for {symbol}")
        else:
            log.debug(f"Symbol {symbol} not found on Screener.in")
            
    return validated_stocks

def rank(stocks: list, top_n: int) -> list:
    log.info(f"Ranking {len(stocks)} discovered stocks...")
    if not stocks:
        return []
        
    client = Groq(api_key=settings.GROQ_API_KEY)
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'news_rank.txt')
    with open(prompt_path, "r") as f:
        prompt_template = f.read()
        
    stocks_json = json.dumps(stocks, default=str)
    prompt = prompt_template.format(n=len(stocks), TOP_N=min(top_n, len(stocks)), stocks_json=stocks_json)
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.GROQ_MODEL,
            temperature=0.1
        )
        response_text = chat_completion.choices[0].message.content
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()
            
        ranked_stocks = json.loads(response_text)
        
        # Merge back full news data for the report stage
        final_list = []
        for r in ranked_stocks:
            for s in stocks:
                if s['symbol'] == r['symbol']:
                    s['brief_reason'] = r.get('brief_reason', s.get('brief_reason'))
                    s['tech_confidence'] = r.get('tech_confidence', 'MEDIUM')
                    final_list.append(s)
                    break
        return final_list
    except Exception as e:
        log.error(f"Error ranking stocks: {e}")
        return stocks[:top_n]
