# stages/technicals.py
import pandas as pd
from config.settings import settings
from utils.logger import log

def score(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Computing technical scores...")
    
    df = df.copy()
    
    df['tech_score'] = 0
    df['rsi_flag'] = False
    df['macd_flag'] = False
    df['vol_flag'] = False
    df['pe_flag'] = False
    
    if 'RSI' in df.columns:
        df['rsi_flag'] = (df['RSI'] >= 45) & (df['RSI'] <= 65)
        df.loc[df['rsi_flag'], 'tech_score'] += 20
        
    if 'MACD Signal' in df.columns:
        df['macd_flag'] = df['MACD Signal'] > 0
        df.loc[df['macd_flag'], 'tech_score'] += 20
        
    cmp_col = next((c for c in df.columns if 'CMP' in c or 'Price' in c), None)
    high_col = next((c for c in df.columns if 'High' in c), None)
    if cmp_col and high_col:
        df.loc[(df[high_col] - df[cmp_col]) / df[high_col] <= 0.20, 'tech_score'] += 15

    vol_col = next((c for c in df.columns if 'Volume' in c), None)
    if vol_col:
        df['vol_flag'] = df[vol_col] > 500000 
        df.loc[df['vol_flag'], 'tech_score'] += 15
        
    pe_col = next((c for c in df.columns if 'P/E' in c or 'Price to Earning' in c), None)
    if pe_col:
        df['pe_flag'] = df[pe_col] < 25
        df.loc[df['pe_flag'], 'tech_score'] += 15

    ret_3m_col = next((c for c in df.columns if 'Return' in c and '3' in c), None)
    if ret_3m_col:
        df.loc[df[ret_3m_col] > 0, 'tech_score'] += 10
        
    mcap_col = next((c for c in df.columns if 'Market Cap' in c), None)
    if mcap_col:
        df.loc[df[mcap_col] > 500, 'tech_score'] += 5
        
    df = df.sort_values(by='tech_score', ascending=False).head(settings.MAX_CANDIDATES)
    return df
