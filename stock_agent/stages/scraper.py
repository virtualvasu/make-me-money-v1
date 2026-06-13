# stages/scraper.py
import urllib.parse
from bs4 import BeautifulSoup
import pandas as pd
from config.settings import settings
from utils.logger import log
from utils.http import get_session
from utils.cache import get_cached_html, save_cached_html

class ScreenerAuthError(Exception):
    pass

class NoResultsError(Exception):
    pass

def fetch(query_name: str, query: dict, use_cache: bool = True) -> pd.DataFrame:
    if use_cache and settings.CACHE_SCREENER:
        html = get_cached_html(query_name)
        if html:
            log.info(f"Using cached screener results for {query_name}")
            return _parse_html(html)

    log.info(f"Fetching screener results for {query_name}...")
    encoded_query = urllib.parse.quote_plus(query['screener_query'])
    sort_by = urllib.parse.quote_plus(query.get('sort_by', ''))
    sort_order = query.get('sort_order', '')
    url = f"https://www.screener.in/screen/raw/?sort={sort_by}&order={sort_order}&query={encoded_query}"
    
    session = get_session(with_screener_auth=True)
    response = session.get(url)
    
    if response.status_code in (403, 302):
        raise ScreenerAuthError("Screener session expired or invalid. Please update SCREENER_SESSION_ID and SCREENER_CSRF_TOKEN in .env.")
    response.raise_for_status()
    
    html = response.text
    if use_cache and settings.CACHE_SCREENER:
        save_cached_html(query_name, html)
        
    return _parse_html(html)

def _parse_html(html: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    
    if not table:
        raise NoResultsError("No table found in the screener response. The query might have returned no results.")
        
    rows = table.find_all('tr')
    if not rows:
        raise NoResultsError("No rows found in the table.")
        
    # Find the header row (first row with th elements)
    header_row = rows[0]
    for r in rows:
        if r.find('th'):
            header_row = r
            break
            
    headers = [th.text.strip() for th in header_row.find_all('th')]
    if not headers:
        headers = [td.text.strip() for td in header_row.find_all('td')]
    
    data = []
    for row in rows:
        if row == header_row:
            continue
            
        cells = row.find_all('td')
        if not cells:
            continue
        
        row_data = [cell.text.strip() for cell in cells]
        if len(row_data) != len(headers):
            continue
            
        row_dict = dict(zip(headers, row_data))
        
        # Extract symbol
        name_cell = row.find('td', {'data-stat': 'Name'})
        if not name_cell and 'Name' in headers:
            name_cell = cells[headers.index('Name')]
            
        symbol = None
        if name_cell and name_cell.find('a'):
            href = name_cell.find('a')['href']
            parts = [p for p in href.split('/') if p]
            if len(parts) >= 2 and parts[0] == 'company':
                symbol = parts[1]
                
        row_dict['NSE Symbol'] = symbol
        data.append(row_dict)
        
    df = pd.DataFrame(data)
    if df.empty:
        raise NoResultsError("No results found for this query.")
        
    # Convert numeric columns
    for col in df.columns:
        if col not in ['Name', 'NSE Symbol', 'S.No.']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
            
    if 'S.No.' in df.columns:
        df = df.drop(columns=['S.No.'])
            
    return df
