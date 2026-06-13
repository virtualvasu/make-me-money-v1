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
            "Return over 3Months > 10 AND "
            "Price to Earning < 40 AND "
            "MACD Signal > 0"
        ),
        "sort_by": "Return over 3Months",
        "sort_order": "desc",
    },

    "oversold_reversal": {
        "description": "Oversold quality stocks with reversal signals",
        "horizon": "2 months",
        "screener_query": (
            "Market Capitalization > 200 AND "
            "RSI < 35 AND "
            "Return over 1Year > 0 AND "
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
