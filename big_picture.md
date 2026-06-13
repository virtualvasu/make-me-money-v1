# Stock Analysis Agent — Architecture Plan

> A multi-stage Python agent that scrapes Screener.in, researches news, and produces a ranked confidence report for stocks likely to move 10%+ in 60 days.
> Built for local Ollama + Groq API. Use this document with Claude Code to implement the full system.

---

## Project Structure

```
stock_agent/
│
├── .env                        # secrets — never commit
├── requirements.txt
├── main.py                     # CLI entrypoint + orchestrator
│
├── config/
│   ├── settings.py             # loads .env, global constants
│   └── queries.py              # all screener query presets (add new ones here)
│
├── stages/
│   ├── scraper.py              # Stage 1a: hit screener.in, parse table
│   ├── technicals.py           # Stage 1b: clean + score technical indicators
│   ├── prerank.py              # Stage 1c: Groq call — narrow 50 → 15 candidates
│   ├── news.py                 # Stage 2a: Google News RSS fetch per stock
│   ├── articles.py             # Stage 2b: scrape + extract article text
│   ├── summariser.py           # Stage 2c: Ollama — summarise articles locally
│   └── report.py               # Stage 3: Groq final synthesis → ranked MD report
│
├── prompts/
│   ├── prerank.txt             # Groq prompt: pre-filter candidates
│   └── synthesis.txt           # Groq prompt: final ranked report
│
├── output/                     # generated reports land here (gitignored)
│   └── .gitkeep
│
└── utils/
    ├── http.py                 # shared requests session with retry logic
    ├── logger.py               # structured logging
    └── cache.py                # optional: cache screener responses to disk
```

---

## .env File

```env
# Screener.in session (copy from browser devtools → Application → Cookies)
SCREENER_SESSION_ID=your_session_id_here
SCREENER_CSRF_TOKEN=your_csrf_token_here

# Groq
GROQ_API_KEY=gsk_xxxxxxxxxxxx
GROQ_MODEL=llama3-70b-8192

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral

# Agent behaviour
MAX_CANDIDATES=50          # screener results to fetch
TOP_N_FOR_NEWS=15          # stocks to pass to news stage
TOP_N_FINAL_REPORT=10      # stocks in final report
CACHE_SCREENER=true        # cache screener response for 6h (saves re-scraping)
OUTPUT_DIR=./output
```

---

## config/queries.py — Query Presets

This is where you define and manage all your screener filter sets. Each preset maps to a URL query string for screener.in.

```python
# config/queries.py
# Add new query presets here without touching any other file.
# Run with: python main.py --query momentum_breakout

QUERIES = {

    "momentum_breakout": {
        "description": "Mid/large cap stocks with strong momentum and rising volume",
        "horizon": "2 months",
        "screener_query": (
            "Market Capitalization > 500 AND "
            "Volume > 500000 AND "
            "RSI > 55 AND RSI < 75 AND "
            "Return over 3 months > 10 AND "
            "Price to Earning < 40 AND "
            "MACD Signal > 0"
        ),
        "sort_by": "Return over 3 months",
        "sort_order": "desc",
    },

    "oversold_reversal": {
        "description": "Oversold quality stocks with reversal signals",
        "horizon": "2 months",
        "screener_query": (
            "Market Capitalization > 200 AND "
            "RSI < 35 AND "
            "Return over 1 year > 0 AND "
            "Debt to equity < 1 AND "
            "Return on equity > 12"
        ),
        "sort_by": "RSI",
        "sort_order": "asc",
    },

    "smallcap_growth": {
        "description": "Small cap high growth with low PE",
        "horizon": "2 months",
        "screener_query": (
            "Market Capitalization < 500 AND "
            "Market Capitalization > 50 AND "
            "Sales growth > 20 AND "
            "Profit growth > 20 AND "
            "Price to Earning < 25 AND "
            "RSI > 50"
        ),
        "sort_by": "Sales growth",
        "sort_order": "desc",
    },

    "dividend_value": {
        "description": "Value stocks with dividend support",
        "horizon": "2 months",
        "screener_query": (
            "Dividend yield > 2 AND "
            "Price to Earning < 20 AND "
            "Return on equity > 15 AND "
            "Debt to equity < 0.5 AND "
            "Market Capitalization > 1000"
        ),
        "sort_by": "Dividend yield",
        "sort_order": "desc",
    },

    # Add more presets here as needed
}
```

---

## Stage 1a — scraper.py

**Goal**: Authenticate with screener.in using session cookies and scrape the filtered stock table.

**Implementation notes**:
- Use `requests.Session()` with cookies set from `.env`
- Target URL: `https://www.screener.in/screens/query/?sort={sort_by}&order={sort_order}&query={encoded_query}&limit={MAX_CANDIDATES}`
- Set headers: `Referer: https://www.screener.in/`, `X-CSRFToken: <from env>`
- Parse response HTML with `BeautifulSoup`, find `<table>` with stock rows
- Extract columns: Name, NSE Symbol, CMP, PE, RSI, MACD, Volume, Market Cap, 52W High, 52W Low, Return 1Y, Return 3M
- Return a `pandas.DataFrame`
- If `CACHE_SCREENER=true`, write the raw HTML to `output/cache/screener_{query_name}_{date}.html` and reuse within 6h

**Error handling**:
- If response status is 403/302, session has expired — raise `ScreenerAuthError` with instructions to refresh cookie
- If table is empty, raise `NoResultsError`

---

## Stage 1b — technicals.py

**Goal**: Compute derived signals and a numeric score for each stock from the scraped DataFrame.

**Scoring rules** (each adds to `tech_score` out of 100):

| Signal | Condition | Points |
|---|---|---|
| RSI zone | 45–65 (momentum without overbought) | +20 |
| MACD | Signal line crossover positive | +20 |
| Price vs 52W | Within 20% of 52W high | +15 |
| Volume | Above 20-day average | +15 |
| PE | Below sector average proxy (<25) | +15 |
| Return 3M | Positive | +10 |
| Market cap | >500 Cr (stability) | +5 |

**Output**: DataFrame with added columns: `tech_score`, `rsi_flag`, `macd_flag`, `vol_flag`, `pe_flag`. Sort descending by `tech_score`. Keep top `MAX_CANDIDATES` rows.

---

## Stage 1c — prerank.py (Groq Call #1)

**Goal**: Use Groq to intelligently narrow 50 scored stocks to 15, with a short reasoning for each.

**Input**: JSON array of top-50 stocks with all technical fields + tech_score.

**Prompt** (`prompts/prerank.txt`):
```
You are a quantitative equity analyst focused on Indian stock markets.
You will receive a list of {n} stocks with their technical indicators.
Your job is to select the top {TOP_N} most likely to appreciate 10%+ in the next 60 days.

For each selected stock, return:
- symbol
- name
- brief_reason (max 2 sentences, technical reasoning only)
- tech_confidence: HIGH / MEDIUM / LOW

Respond ONLY with a JSON array. No preamble, no markdown fences.

Stocks:
{stocks_json}
```

**Groq call**: Single request with `max_tokens=2000`. Parse JSON response. If parse fails, retry once with a stricter prompt. This uses **1 of your 2 Groq calls**.

**Output**: List of 15 stock dicts with `symbol`, `name`, `brief_reason`, `tech_confidence`.

---

## Stage 2a — news.py

**Goal**: For each of the 15 candidate stocks, fetch recent news article URLs via Google News RSS.

**Implementation**:
- URL pattern: `https://news.google.com/rss/search?q={SYMBOL}+NSE+stock&hl=en-IN&gl=IN&ceid=IN:en`
- Parse RSS with `feedparser`
- Extract top 4 entries per stock: `title`, `link`, `published`
- Filter out articles older than 45 days
- Skip duplicate sources (same domain appearing twice)
- Return dict: `{ symbol: [ {title, url, published}, ... ] }`

**No API key needed.** Google News RSS is free and works without auth.

---

## Stage 2b — articles.py

**Goal**: Fetch and extract clean text from each article URL.

**Implementation**:
- Use `trafilatura` — best library for Indian financial news sites (works on Moneycontrol, Economic Times, Business Standard, LiveMint)
- For each URL: `trafilatura.fetch_url(url)` → `trafilatura.extract(html)`
- If `trafilatura` returns `None`, fall back to `newspaper3k` (`Article(url).download(); article.parse()`)
- Truncate extracted text to 1500 characters (enough for summarisation, avoids context overflow)
- Return dict: `{ symbol: [ {title, url, text_excerpt}, ... ] }`

**Failure handling**: If both extractors fail (paywalled, JS-rendered), store `text_excerpt = ""` and mark `extraction_failed = True`. The summariser will skip it.

---

## Stage 2c — summariser.py (Ollama — unlimited calls)

**Goal**: Summarise each article into 2–3 investment-relevant bullet points using local Ollama.

**Implementation**:
- Call `http://localhost:11434/api/generate` with `POST`
- Model: value from `OLLAMA_MODEL` in env (default: `mistral`)
- One call per article. With 15 stocks × 4 articles = up to 60 Ollama calls. All local, no rate limit.
- Run sequentially (or with `asyncio` for speed — optional optimisation)

**Prompt per article**:
```
You are a financial news analyst. Read this news excerpt about a stock and extract
investment-relevant information only.

Stock: {SYMBOL}
Article: {text_excerpt}

Respond with exactly 2-3 bullet points. Each bullet: one sentence, investment focus only.
Ignore general market commentary. Focus on: earnings, orders, expansion, management changes,
regulatory news, sector tailwinds/headwinds.

Bullets:
```

**Output**: `{ symbol: [ {title, url, bullets: ["...", "..."]}, ... ] }`

---

## Stage 3 — report.py (Groq Call #2)

**Goal**: Merge all signals and generate the final ranked report via Groq.

**Input**: For each of the 15 stocks:
```json
{
  "symbol": "RELIANCE",
  "name": "Reliance Industries",
  "cmp": 2840,
  "tech_score": 78,
  "tech_confidence": "HIGH",
  "brief_reason": "RSI at 62 with MACD crossover; strong 3M return of 14%.",
  "indicators": { "rsi": 62, "pe": 24, "vol_flag": true, "macd_flag": true },
  "news": [
    { "title": "Reliance Jio launches new 5G plan", "url": "...", "bullets": ["Jio expands 5G to 100 cities", "Analyst upgrade follows announcement"] },
    ...
  ]
}
```

**Prompt** (`prompts/synthesis.txt`):
```
You are a senior equity research analyst covering Indian markets.

You have been given {n} pre-screened stock candidates with technical scores and recent news.
Your task: produce a final ranked research report for stocks likely to gain 10%+ in 60 days.

Rules:
1. Rank stocks from HIGHEST to LOWEST confidence.
2. For each stock, write:
   a. TECHNICAL CASE first (RSI, MACD, volume, PE, price levels)
   b. NEWS EVIDENCE second (cite specific developments)
   c. CONFIDENCE: HIGH / MEDIUM / LOW with one-line rationale
   d. KEY RISK: one sentence
3. Drop any stock where news contradicts the technical thesis.
4. Output as clean Markdown only. No preamble.

Target horizon: 60 days
Report date: {today}

Stocks data:
{stocks_json}
```

**Groq call**: `max_tokens=4000`. This uses your **2nd Groq call**.

**Output**: Markdown string. Write to `output/report_{query_name}_{YYYYMMDD_HHMM}.md`.

---

## main.py — Orchestrator

```python
# main.py
# Usage:
#   python main.py --query momentum_breakout
#   python main.py --query oversold_reversal --top 10
#   python main.py --query smallcap_growth --no-cache

import argparse
from config.queries import QUERIES
from config.settings import settings
from stages import scraper, technicals, prerank, news, articles, summariser, report
from utils.logger import log

def run(query_name: str, top_n: int, use_cache: bool):
    query = QUERIES[query_name]
    log.info(f"Running query: {query_name} — {query['description']}")

    # Stage 1
    log.info("Stage 1: Scraping screener.in...")
    df_raw = scraper.fetch(query, use_cache=use_cache)
    df_scored = technicals.score(df_raw)
    candidates = prerank.narrow(df_scored, top_n=settings.TOP_N_FOR_NEWS)  # Groq call #1

    # Stage 2
    log.info("Stage 2: Fetching news...")
    rss_data = news.fetch_all(candidates)
    article_data = articles.extract_all(rss_data)
    summaries = summariser.summarise_all(article_data)          # Ollama (local)

    # Stage 3
    log.info("Stage 3: Generating report...")
    merged = report.merge(candidates, summaries)
    markdown = report.synthesise(merged, query, top_n=top_n)    # Groq call #2
    filepath = report.save(markdown, query_name)

    log.info(f"Report saved: {filepath}")
    print(f"\n{'='*60}\nReport: {filepath}\n{'='*60}\n")
    print(markdown[:2000])  # preview first 2000 chars in terminal

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True, choices=list(QUERIES.keys()))
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()
    run(args.query, args.top, use_cache=not args.no_cache)
```

---

## requirements.txt

```txt
# HTTP + scraping
requests==2.31.0
beautifulsoup4==4.12.3
trafilatura==1.9.0
newspaper3k==0.2.8
feedparser==6.0.11

# Data
pandas==2.2.0

# AI
groq==0.8.0
httpx==0.27.0       # used by groq client

# Utilities
python-dotenv==1.0.1
rich==13.7.0        # pretty terminal logging
```

---

## config/settings.py

```python
# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SCREENER_SESSION_ID = os.environ["SCREENER_SESSION_ID"]
    SCREENER_CSRF_TOKEN = os.environ["SCREENER_CSRF_TOKEN"]
    GROQ_API_KEY = os.environ["GROQ_API_KEY"]
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
    MAX_CANDIDATES = int(os.getenv("MAX_CANDIDATES", 50))
    TOP_N_FOR_NEWS = int(os.getenv("TOP_N_FOR_NEWS", 15))
    TOP_N_FINAL_REPORT = int(os.getenv("TOP_N_FINAL_REPORT", 10))
    CACHE_SCREENER = os.getenv("CACHE_SCREENER", "true").lower() == "true"
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

settings = Settings()
```

---

## Report Output Format

The final markdown report follows this structure:

```markdown
# Stock Analysis Report — Momentum Breakout
**Date**: 14 Jun 2025 | **Horizon**: 60 days | **Confidence threshold**: 10% move

---

## 1. RELIANCE INDUSTRIES (RELIANCE) ★★★ HIGH
**CMP**: ₹2,840 | **PE**: 24 | **RSI**: 62

### Technical Case
- RSI at 62: momentum zone, not overbought. Room to run.
- MACD crossover confirmed 3 sessions ago; histogram expanding.
- Volume 40% above 20-day average — institutional accumulation likely.
- Price within 8% of 52W high; prior resistance now support.

### News Evidence
- **Jio 5G expansion**: Reliance Jio announced rollout to 100 additional cities, analysts
  raised FY26 ARPU estimates by 8%. (Economic Times, 10 Jun 2025)
- **Retail segment**: Q4 store additions exceeded guidance; margin expanded 120bps YoY.

### Confidence: HIGH
Strong technical setup corroborated by two independent fundamental catalysts.

### Key Risk
Crude price spike above $90/bbl compresses refining margins.

---

## 2. TATA MOTORS (TATAMOTORS) ★★☆ MEDIUM
...
```

---

## Groq API Budget Summary

| Call | Stage | Purpose | Approx tokens |
|---|---|---|---|
| #1 | prerank.py | Narrow 50 → 15 stocks with reasoning | ~3,000 in + 2,000 out |
| #2 | report.py | Final ranked synthesis report | ~5,000 in + 4,000 out |

**Total per run: 2 Groq calls, ~14,000 tokens.** Well within free tier limits even at 10 runs/day.

Ollama handles all 60 article summarisation calls locally — no rate limit, no cost.

---

## How to Add a New Query

1. Open `config/queries.py`
2. Add a new key to the `QUERIES` dict with `description`, `horizon`, `screener_query`, `sort_by`, `sort_order`
3. Run: `python main.py --query your_new_query_name`

No other files need to change.

---

## Screener.in Cookie Refresh

Session cookies expire. When you see `ScreenerAuthError`:

1. Open `https://www.screener.in` in your browser and log in
2. Open DevTools → Application → Cookies → `www.screener.in`
3. Copy the value of `sessionid` → paste into `.env` as `SCREENER_SESSION_ID`
4. Copy the value of `csrftoken` → paste into `.env` as `SCREENER_CSRF_TOKEN`
5. Re-run the agent

---

## Implementation Order for Claude Code

Build and test in this order — each stage has a clean input/output contract:

1. `config/settings.py` + `config/queries.py` — foundation, no logic
2. `utils/http.py` + `utils/logger.py` — shared helpers
3. `stages/scraper.py` — test with `--no-cache`, verify DataFrame shape
4. `stages/technicals.py` — unit-testable scoring logic
5. `stages/prerank.py` — test Groq connection, verify JSON parse
6. `stages/news.py` — test RSS parsing for 2–3 symbols
7. `stages/articles.py` — test trafilatura on a Moneycontrol URL
8. `stages/summariser.py` — test Ollama is running, single article
9. `stages/report.py` — test final synthesis with mock merged data
10. `main.py` — wire everything together, end-to-end test with `momentum_breakout`