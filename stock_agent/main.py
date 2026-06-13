# main.py
import argparse
import sys
import os

# Add current directory to path so imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.queries import QUERIES
from config.settings import settings
from stages import scraper, technicals, prerank, news, articles, summariser, report
from utils.logger import log

def run(query_name: str, top_n: int, use_cache: bool):
    query = QUERIES[query_name]
    log.info(f"Running query: {query_name} — {query['description']}")

    # Stage 1
    log.info("Stage 1: Scraping screener.in...")
    df_raw = scraper.fetch(query_name, query, use_cache=use_cache)
    df_scored = technicals.score(df_raw)
    candidates = prerank.narrow(df_scored, query=query, top_n=settings.TOP_N_FOR_NEWS)

    # Stage 2
    log.info("Stage 2: Fetching news...")
    rss_data = news.fetch_all(candidates)
    article_data = articles.extract_all(rss_data)
    summaries = summariser.summarise_all(article_data)          # Ollama (local)

    # Stage 3
    log.info("Stage 3: Generating report...")
    merged = report.merge(candidates, summaries)
    markdown = report.synthesise(merged, query, top_n=top_n)    # Ollama call #2
    
    final_report = f"# Stock Analysis Report — {query['description']}\n\n{markdown}"
    filepath = report.save(final_report, query_name)

    log.info(f"Report saved: {filepath}")
    print(f"\n{'='*60}\nReport: {filepath}\n{'='*60}\n")
    print(final_report[:2000])  # preview first 2000 chars in terminal

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True, choices=list(QUERIES.keys()))
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()
    run(args.query, args.top, use_cache=not args.no_cache)
