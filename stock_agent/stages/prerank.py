# stages/prerank.py
import json
import os
from groq import Groq
import pandas as pd
from config.settings import settings
from utils.logger import log

def narrow(df: pd.DataFrame, top_n: int) -> list:
    log.info(f"Pre-ranking top {top_n} candidates via Groq...")
    
    stocks_json = df.to_json(orient="records")
    
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'prerank.txt')
    with open(prompt_path, "r") as f:
        prompt_template = f.read()
        
    prompt = prompt_template.format(n=len(df), TOP_N=top_n, stocks_json=stocks_json)
    
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    for attempt in range(2):
        try:
            log.info(f"Groq prerank call attempt {attempt+1}...")
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                temperature=0.1
            )
            response_text = chat_completion.choices[0].message.content
            
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].strip()
                
            candidates = json.loads(response_text)
            log.info(f"Successfully narrowed down to {len(candidates)} candidates.")
            
            # Merge original data
            for c in candidates:
                symbol = c.get('symbol')
                if symbol:
                    row = df[df['NSE Symbol'] == symbol]
                    if not row.empty:
                        c['cmp'] = row.iloc[0].get('CMP') or row.iloc[0].get('Price', 0)
                        c['tech_score'] = row.iloc[0].get('tech_score', 0)
                        c['indicators'] = {
                            'rsi': row.iloc[0].get('RSI'),
                            'pe': row.iloc[0].get('P/E') or row.iloc[0].get('Price to Earning'),
                            'vol_flag': bool(row.iloc[0].get('vol_flag')),
                            'macd_flag': bool(row.iloc[0].get('macd_flag'))
                        }
            
            return candidates
        except Exception as e:
            log.error(f"Error in Groq prerank (attempt {attempt+1}): {e}")
            if attempt == 1:
                log.error("Failed to parse Groq response. Returning top candidates from technical score.")
                fallback_candidates = []
                for _, row in df.head(top_n).iterrows():
                    fallback_candidates.append({
                        "symbol": row.get("NSE Symbol"),
                        "name": row.get("Name"),
                        "brief_reason": f"Fallback: High tech score of {row.get('tech_score')}",
                        "tech_confidence": "MEDIUM",
                        "cmp": row.get("CMP") or row.get("Price", 0),
                        "tech_score": row.get("tech_score"),
                        "indicators": {
                            'rsi': row.get('RSI'),
                            'pe': row.get('P/E') or row.get('Price to Earning'),
                            'vol_flag': bool(row.get('vol_flag')),
                            'macd_flag': bool(row.get('macd_flag'))
                        }
                    })
                return fallback_candidates
    return []
