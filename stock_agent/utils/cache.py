# utils/cache.py
import os
import time
from config.settings import settings

CACHE_DIR = os.path.join(settings.OUTPUT_DIR, 'cache')
CACHE_TTL = 6 * 3600  # 6 hours

def _ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)

def get_cached_html(query_name: str) -> str:
    """Returns cached HTML if it exists and is less than 6 hours old, else None."""
    _ensure_cache_dir()
    filepath = os.path.join(CACHE_DIR, f"screener_{query_name}.html")
    if os.path.exists(filepath):
        if time.time() - os.path.getmtime(filepath) < CACHE_TTL:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
    return None

def save_cached_html(query_name: str, html: str):
    """Saves HTML to cache."""
    _ensure_cache_dir()
    filepath = os.path.join(CACHE_DIR, f"screener_{query_name}.html")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
