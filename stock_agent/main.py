# main.py
import argparse
import sys
import os

# Add current directory to path so imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.queries import QUERIES
from config.settings import settings
from stages import scraper, technicals, prerank, news, articles, summariser, report, category_scanner, news_discovery
from utils.logger import log

def run(mode: str, query_name: str, category: str, horizon: str, top_n: int, use_cache: bool):
    if mode == "fundamentals" and not query_name:
        log.error("fundamentals mode requires a --query")
        return
    if mode in ["category-scan", "news-first"] and not category:
        log.error(f"{mode} mode requires a --category")
        return

    # Define mock query object depending on mode
    if mode == "fundamentals":
        query = QUERIES[query_name]
        log.info(f"Running fundamentals mode for query: {query_name} — {query['description']}")
    elif mode == "category-scan":
        query = {"description": f"Category scan: {category}", "horizon": horizon or "2 months"}
        log.info(f"Running category-scan mode for: {category}")
    elif mode == "news-first":
        query = {"description": f"News-first discovery for {category}", "horizon": horizon or "2-5 months"}
        log.info(f"Running news-first discovery mode")

    if horizon:
        query["horizon"] = horizon # override if provided

    # Stage 1: Data Gathering & Scoring
    if mode == "fundamentals":
        log.info("Stage 1: Scraping screener.in...")
        df_raw = scraper.fetch(query_name, query, use_cache=use_cache)
        df_scored = technicals.score(df_raw)
        candidates = prerank.narrow(df_scored, query=query, top_n=settings.TOP_N_FOR_NEWS)
    elif mode == "category-scan":
        log.info(f"Stage 1: Scanning category {category}...")
        df_raw = category_scanner.scan(category, use_cache=use_cache)
        if df_raw.empty:
            return
        df_scored = technicals.score(df_raw)
        candidates = prerank.narrow(df_scored, query=query, top_n=settings.TOP_N_FOR_NEWS)
    elif mode == "news-first":
        log.info("Stage 1: Discovering via news...")
        discovered_stocks = news_discovery.discover()
        candidates = news_discovery.rank(discovered_stocks, top_n=settings.TOP_N_FOR_NEWS)

    if not candidates:
        log.warning("No candidates survived Stage 1. Exiting.")
        return

    # Stage 2: Deep News Context
    log.info("Stage 2: Fetching deep news context...")
    # In news-first, we already have initial catalysts, but we can fetch more if needed
    # (Here we just use existing fetch_all which might find more recent news)
    rss_data = news.fetch_all(candidates)
    article_data = articles.extract_all(rss_data)
    summaries = summariser.summarise_all(article_data)

    # For news-first, ensure original catalyst isn't lost if no new news is found
    if mode == "news-first":
        for c in candidates:
            sym = c['symbol']
            if not summaries.get(sym):
                summaries[sym] = c.get('news', [])

    # Stage 3: Report
    log.info("Stage 3: Generating report...")
    merged = report.merge(candidates, summaries)
    markdown = report.synthesise(merged, query, top_n=top_n)
    
    file_prefix = query_name if mode == "fundamentals" else f"{mode}_{category}"
    final_report = f"# Stock Analysis Report — {query['description']}\n\n{markdown}"
    filepath = report.save(final_report, file_prefix)

    log.info(f"Report saved: {filepath}")
    print(f"\n{'='*60}\nReport: {filepath}\n{'='*60}\n")
    print(final_report[:2000])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["fundamentals", "category-scan", "news-first"], default="fundamentals", help="Run mode")
    parser.add_argument("--query", choices=list(QUERIES.keys()), help="Query preset (for fundamentals mode)")
    parser.add_argument("--category", choices=["bluechip", "midcap_growth", "price_range", "all"], help="Category (for category-scan and news-first modes)")
    parser.add_argument("--horizon", type=str, help="Override investment horizon (e.g. '3 months')")
    parser.add_argument("--top", type=int, default=10, help="Number of stocks to report")
    parser.add_argument("--no-cache", action="store_true", help="Disable screener caching")
    
    args = parser.parse_args()
    
    if args.mode == "fundamentals" and not args.query:
        parser.error("--query is required for fundamentals mode")
        
    run(args.mode, args.query, args.category, args.horizon, args.top, use_cache=not args.no_cache)
