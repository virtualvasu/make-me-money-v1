# stages/articles.py
import trafilatura
from newspaper import Article
from utils.logger import log

def extract_all(rss_data: dict) -> dict:
    log.info("Extracting article text...")
    
    results = {}
    
    for symbol, articles in rss_data.items():
        extracted_articles = []
        for a in articles:
            url = a['url']
            title = a['title']
            
            text_excerpt = ""
            extraction_failed = False
            
            try:
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    text_excerpt = trafilatura.extract(downloaded)
                    
                if not text_excerpt:
                    article = Article(url)
                    article.download()
                    article.parse()
                    text_excerpt = article.text
            except Exception as e:
                log.debug(f"Extraction error for {url}: {e}")
                
            if not text_excerpt:
                text_excerpt = ""
                extraction_failed = True
                
            text_excerpt = text_excerpt[:1500] if text_excerpt else ""
            
            extracted_articles.append({
                "title": title,
                "url": url,
                "text_excerpt": text_excerpt,
                "extraction_failed": extraction_failed
            })
            
        results[symbol] = extracted_articles
        
    return results
