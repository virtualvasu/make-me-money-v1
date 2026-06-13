# Make Me Money

An automated AI-powered equity research pipeline for Indian stock markets. The system screens stocks from Screener.in, evaluates technical setups, aggregates and summarizes relevant news, and produces a ranked investment research report — entirely without manual intervention.

---

## Architecture

```mermaid
flowchart TD
    A([CLI: python3 main.py --query momentum_breakout]) --> B

    subgraph STAGE1 ["Stage 1 — Data Acquisition"]
        B[queries.json\nQuery definition + Screener URL] --> C[scraper.py\nFetch raw data from Screener.in\nvia session cookies]
        C --> D[(Cache\n6-hour HTML cache)]
        C --> E[technicals.py\nScore each stock\nRSI · MACD · 3M Return\n52w High · Volume · PE]
    end

    subgraph STAGE2 ["Stage 2 — AI Pre-Ranking"]
        E --> F[prerank.py\nGroq LLM — llama-3.3-70b\nSelect top 15 from 50\nwith reasoning + confidence]
    end

    subgraph STAGE3 ["Stage 3 — News Intelligence"]
        F --> G[news.py\nGoogle News RSS\nFetch top 4 articles per stock]
        G --> H[googlenewsdecoder\nDecode obfuscated\nGoogle redirect URLs]
        H --> I[articles.py\ntrafilatura + newspaper3k\nExtract full article text]
        I --> J[summariser.py\nGroq LLM\nDistil to 2-3 investment\nbullet points per article]
    end

    subgraph STAGE4 ["Stage 4 — Report Synthesis"]
        J --> K[report.py\nMerge technical data\nwith news summaries]
        F --> K
        K --> L[Groq LLM — llama-3.3-70b\nSynthesize final report\nTop 10 stocks ranked by conviction]
        L --> M[(output/\nreport_query_YYYYMMDD.md)]
    end

    style STAGE1 fill:#1a1a2e,stroke:#4a4a8a,color:#e0e0ff
    style STAGE2 fill:#1a2e1a,stroke:#4a8a4a,color:#e0ffe0
    style STAGE3 fill:#2e1a1a,stroke:#8a4a4a,color:#ffe0e0
    style STAGE4 fill:#2e2a1a,stroke:#8a7a4a,color:#fff0e0
```

---

## Report Output Format

Each stock in the final report includes:

- **Technical Case** — RSI zone, MACD signal, 3-month return, proximity to 52-week high, valuation
- **News Evidence** — Investment-relevant bullet points with links to source articles
- **Confidence** — HIGH / MEDIUM / LOW with rationale
- **Key Risk** — The single biggest factor that could invalidate the trade

---

## Queries Available

The agent supports multiple pre-built screening strategies. All queries and their Screener.in URLs are defined in `stock_agent/config/queries.json`.

| Query | Strategy |
|---|---|
| `momentum_breakout` | Mid/large cap with strong momentum and rising volume |
| `oversold_reversal` | Oversold quality stocks with early reversal signals |
| `smallcap_growth` | Small cap with high sales and profit growth |
| `dividend_value` | Blue chip value with strong dividend support |
| `quality_at_fair_value` | High ROCE, low debt, reasonable valuation |
| `high_roce_compounder` | Long-duration compounders, 25%+ ROCE |
| `undervalued_midcap` | Midcap stocks with PE < 15 and solid ROE |
| `sector_rotation_infra` | Infrastructure plays with sales growth momentum |
| `turnaround_candidates` | Beaten-down stocks with improving fundamentals |
| `fii_buying_largecap` | Large cap with price strength and clean balance sheet |

---

## Quickstart

```bash
cd stock_agent
pip install -r requirements.txt

# Copy and fill in your credentials
cp .env.example .env

# Run a query
python3 main.py --query momentum_breakout

# Force fresh data (bypass 6h cache)
python3 main.py --query quality_at_fair_value --no-cache

# Change number of stocks in final report
python3 main.py --query smallcap_growth --top 5
```

See `stock_agent/README.md` for full configuration details.

---

## Tech Stack

| Component | Technology |
|---|---|
| Data source | Screener.in (session-authenticated scrape) |
| Pre-ranking LLM | Groq — llama-3.3-70b-versatile |
| News summarization LLM | Groq — llama-3.3-70b-versatile |
| Report synthesis LLM | Groq — llama-3.3-70b-versatile |
| Article extraction | trafilatura, newspaper3k |
| News aggregation | Google News RSS + googlenewsdecoder |
| Data processing | pandas |
| Local inference (optional) | Ollama |
