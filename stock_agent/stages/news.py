# stages/news.py
import urllib.parse
import feedparser
import time
from googlenewsdecoder import new_decoderv1
from datetime import datetime, timezone
from utils.logger import log

def fetch_all(candidates: list) -> dict:
    log.info("Fetching news via Google News RSS...")
    
    results = {}
    now = datetime.now(timezone.utc)
    
    for c in candidates:
        symbol = c.get('symbol')
        if not symbol:
            continue
            
        log.info(f"Fetching news for {symbol}")
        encoded_query = urllib.parse.quote(f"{symbol} NSE stock")
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        feed = feedparser.parse(url)
        
        articles = []
        seen_domains = set()
        
        for entry in feed.entries:
            if len(articles) >= 4:
                break
                
            title = entry.title
            link = entry.link
            
            try:
                decoded_res = new_decoderv1(link)
                if decoded_res.get('status') and decoded_res.get('decoded_url'):
                    link = decoded_res['decoded_url']
            except Exception as e:
                log.debug(f"Failed to decode Google News URL: {e}")
            
            domain = urllib.parse.urlparse(link).netloc
            if domain in seen_domains:
                continue
                
            published_parsed = entry.get('published_parsed')
            if published_parsed:
                dt = datetime.fromtimestamp(time.mktime(published_parsed), timezone.utc)
                if (now - dt).days > 45:
                    continue
                    
            seen_domains.add(domain)
            articles.append({
                "title": title,
                "url": link,
                "published": entry.get('published', '')
            })
            
        results[symbol] = articles
        
    return results
