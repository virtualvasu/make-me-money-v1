# config/queries.py
# All query definitions live in config/queries.json.
# Add new queries there without touching any other file.

import json
import os
import urllib.parse

_queries_path = os.path.join(os.path.dirname(__file__), "queries.json")

with open(_queries_path, "r") as _f:
    QUERIES = json.load(_f)

# Auto-generate screener URLs for all queries
for q_name, q_data in QUERIES.items():
    if 'screener_query' in q_data:
        encoded_query = urllib.parse.quote_plus(q_data['screener_query'])
        sort_by = urllib.parse.quote_plus(q_data.get('sort_by', ''))
        sort_order = q_data.get('sort_order', '')
        q_data['screener_url'] = f"https://www.screener.in/screen/raw/?sort={sort_by}&order={sort_order}&query={encoded_query}"

def get_queries_by_category(category: str) -> dict:
    if category == "all":
        return QUERIES
    return {k: v for k, v in QUERIES.items() if v.get("category") == category}
