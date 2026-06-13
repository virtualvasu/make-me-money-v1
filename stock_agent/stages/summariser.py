# stages/summariser.py
from groq import Groq
from config.settings import settings
from utils.logger import log

def summarise_all(article_data: dict) -> dict:
    log.info("Summarising articles with Groq...")
    
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    results = {}
    
    for symbol, articles in article_data.items():
        summarised_articles = []
        for a in articles:
            if a.get('extraction_failed') or not a.get('text_excerpt'):
                continue
                
            prompt = f"""You are a financial news analyst. Read this news excerpt about a stock and extract
investment-relevant information only.

Stock: {symbol}
Article: {a['text_excerpt']}

Respond with exactly 2-3 bullet points. Each bullet: one sentence, investment focus only.
Ignore general market commentary. Focus on: earnings, orders, expansion, management changes,
regulatory news, sector tailwinds/headwinds.

Bullets:"""

            bullets_text = ""
            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=settings.GROQ_MODEL,
                    temperature=0.1
                )
                bullets_text = chat_completion.choices[0].message.content
            except Exception as e:
                log.error(f"Groq error for {symbol}: {e}")
                
            bullets = [b.strip().lstrip('-').lstrip('*').strip() for b in bullets_text.split('\n') if b.strip()]
            
            summarised_articles.append({
                "title": a['title'],
                "url": a['url'],
                "bullets": bullets
            })
            
        results[symbol] = summarised_articles
        
    return results
