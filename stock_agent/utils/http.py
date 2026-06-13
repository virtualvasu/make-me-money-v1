# utils/http.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.settings import settings

def get_session(with_screener_auth=False):
    session = requests.Session()
    
    # Retry strategy: 3 retries, backoff factor 0.3
    retry = Retry(
        total=3,
        read=3,
        connect=3,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504)
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    if with_screener_auth:
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.screener.in/',
            'X-CSRFToken': settings.SCREENER_CSRF_TOKEN
        })
        session.cookies.set('sessionid', settings.SCREENER_SESSION_ID, domain='.screener.in')
        session.cookies.set('csrftoken', settings.SCREENER_CSRF_TOKEN, domain='.screener.in')
        
    return session
