# stages/category_scanner.py
import pandas as pd
from config.queries import get_queries_by_category
from stages import scraper
from utils.logger import log

def scan(category: str, use_cache: bool = True) -> pd.DataFrame:
    log.info(f"Scanning all queries in category: {category}")
    queries = get_queries_by_category(category)
    
    if not queries:
        log.warning(f"No queries found for category: {category}")
        return pd.DataFrame()
        
    all_dfs = []
    
    for query_name, query_data in queries.items():
        try:
            df = scraper.fetch(query_name, query_data, use_cache=use_cache)
            if not df.empty:
                # Add source query for tracing
                df['source_query'] = query_name
                all_dfs.append(df)
        except Exception as e:
            log.error(f"Error fetching {query_name}: {e}")
            
    if not all_dfs:
        log.warning("All queries in category returned no results.")
        return pd.DataFrame()
        
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # Deduplicate by NSE Symbol, keeping the first occurrence
    if 'NSE Symbol' in combined_df.columns:
        original_count = len(combined_df)
        combined_df = combined_df.drop_duplicates(subset=['NSE Symbol'], keep='first')
        log.info(f"Combined and deduplicated {original_count} raw rows into {len(combined_df)} unique stocks.")
        
    return combined_df
