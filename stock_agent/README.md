# AI Equity Research Agent

An automated, quantitative stock analysis pipeline that screens Indian equities, evaluates technical setups, fetches relevant news, and synthesizes comprehensive investment reports using Large Language Models.

## Overview

This project functions as a multi-stage autonomous financial analyst. It is designed to take a predefined technical screening query, evaluate the resulting stocks, cross-reference their technical strength with recent fundamental news, and output a highly curated final report.

The pipeline executes in four main stages:
1. **Data Acquisition**: Connects to Screener.in using session cookies to pull raw financial, fundamental, and technical data for Indian stocks matching a specific query.
2. **Technical Pre-ranking**: Uses a Groq-powered LLM to evaluate technical indicators (RSI, MACD, Volume, P/E) and narrow down the raw results to the top 15 candidates.
3. **News Aggregation & Summarization**: Fetches recent articles via Google News RSS, bypasses link obfuscation to extract raw article text from publisher domains, and utilizes Groq to summarize the news into concise, investment-relevant bullet points.
4. **Final Synthesis**: Combines the technical pre-ranking and the distilled news evidence to generate a fully formatted markdown Equity Research Report for the top 10 candidates.

## Requirements

* Python 3.10+
* A Groq API Key

Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` (or create a `.env` file) in the root of the project directory. You must configure the following variables:

```ini
# Screener.in session (copy from browser devtools -> Application -> Cookies)
SCREENER_SESSION_ID=your_screener_session_id
SCREENER_CSRF_TOKEN=your_screener_csrf_token

# Groq API Configuration
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Ollama (Optional fallback for local inference)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# Agent behavior parameters
MAX_CANDIDATES=50          # Screener results to fetch
TOP_N_FOR_NEWS=15          # Stocks to pass to the news gathering stage
TOP_N_FINAL_REPORT=10      # Stocks to include in the final synthesis report
CACHE_SCREENER=true        # Cache screener response for 6 hours
OUTPUT_DIR=./output
```

## Usage

To run the pipeline, execute `main.py` and pass the name of the predefined query you want to run. Ensure the query name matches an entry in `config/queries.py`.

```bash
python3 main.py --query momentum_breakout
```

Optional arguments:
* `--top N`: Override the number of stocks in the final report.
* `--no-cache`: Force the scraper to ignore the 6-hour cache and fetch fresh data from Screener.in.

### Output

The final synthesized report will be generated and saved in the `output/` directory as a markdown file, formatted as `report_<query_name>_<timestamp>.md`. 

The report includes:
* **Technical Case**: Summary of technical strength and valuation metrics.
* **News Evidence**: Key fundamental catalysts distilled from recent articles.
* **Confidence**: The agent's conviction rating (HIGH, MEDIUM, LOW) for a breakout.
* **Key Risk**: A personalized risk factor highlighting potential invalidation criteria.
