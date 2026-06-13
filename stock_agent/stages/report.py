# stages/report.py
import json
import os
from datetime import datetime, timezone
from groq import Groq
from config.settings import settings
from utils.logger import log

def merge(candidates: list, summaries: dict) -> list:
    log.info("Merging technical signals with news summaries...")
    merged = []
    
    for c in candidates:
        symbol = c.get('symbol')
        if not symbol:
            continue
            
        c_copy = c.copy()
        c_copy['news'] = summaries.get(symbol, [])
        merged.append(c_copy)
        
    return merged

def synthesise(merged: list, query: dict, top_n: int) -> str:
    log.info(f"Generating final report for top {top_n} candidates via Groq...")
    
    # Only pass the final top_n to the synthesis prompt — keep context tight
    top_candidates = merged[:top_n]
    stocks_json = json.dumps(top_candidates, indent=2, default=str)
    
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'synthesis.txt')
    with open(prompt_path, "r") as f:
        prompt_template = f.read()
        
    today = datetime.now(timezone.utc).strftime("%d %b %Y")
    horizon = query.get('horizon', '60 days')
    
    prompt = prompt_template.format(
        n=len(top_candidates), 
        today=today, 
        horizon=horizon, 
        stocks_json=stocks_json
    )
    
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    try:
        log.info("Groq synthesis call...")
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.GROQ_MODEL,
            temperature=0.2
        )
        report_markdown = chat_completion.choices[0].message.content
        return report_markdown
    except Exception as e:
        log.error(f"Error in Groq synthesis: {e}")
        return "Error generating report."

def save(markdown: str, query_name: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"report_{query_name}_{timestamp}.md"
    filepath = os.path.join(settings.OUTPUT_DIR, filename)
    
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown)
        
    return filepath
