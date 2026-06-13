# stages/technicals.py
import pandas as pd
from config.settings import settings
from utils.logger import log


def score(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Computing technical scores...")

    df = df.copy()

    df['tech_score'] = 0.0
    df['rsi_flag'] = False
    df['macd_flag'] = False
    df['vol_flag'] = False
    df['pe_flag'] = False

    # ── RSI Score (0–25 pts) ────────────────────────────────────────────────
    # Ideal momentum zone: 50–72. Penalise overbought (>75) and weak (<45).
    # Uses a smooth curve instead of a hard binary flag.
    if 'RSI' in df.columns:
        rsi = df['RSI'].fillna(50)
        df['rsi_flag'] = (rsi >= 50) & (rsi <= 72)

        def rsi_pts(r):
            if 55 <= r <= 68:
                return 25          # sweet spot
            elif 50 <= r < 55 or 68 < r <= 72:
                return 18          # acceptable momentum
            elif 45 <= r < 50 or 72 < r <= 78:
                return 8           # borderline
            else:
                return 0           # oversold or overbought

        df['tech_score'] += rsi.apply(rsi_pts)

    # ── MACD Score (0–20 pts) ───────────────────────────────────────────────
    # Still a bullish signal, but we also check magnitude.
    if 'MACD Signal' in df.columns:
        macd = df['MACD Signal'].fillna(0)
        df['macd_flag'] = macd > 0

        # Percentile rank within the dataset so we reward the strongest crossovers
        macd_rank = macd.rank(pct=True)
        df.loc[df['macd_flag'], 'tech_score'] += (macd_rank[df['macd_flag']] * 20).round()

    # ── 3-Month Return Score (0–20 pts) ────────────────────────────────────
    # Percentile-based: top returners get more points, not just "return > 0".
    ret_3m_col = next((c for c in df.columns if 'Return' in c and '3' in c), None)
    if ret_3m_col:
        ret = df[ret_3m_col].fillna(0)
        ret_rank = ret.rank(pct=True)
        df['tech_score'] += (ret_rank * 20).round()

    # ── Proximity to 52-Week High Score (0–15 pts) ─────────────────────────
    # Being close to a 52w high indicates institutional accumulation.
    cmp_col = next((c for c in df.columns if 'CMP' in c or c == 'Price'), None)
    high_col = next((c for c in df.columns if '52' in c and 'High' in c), None)
    if not high_col:
        high_col = next((c for c in df.columns if 'High' in c), None)
    if cmp_col and high_col:
        cmp = pd.to_numeric(df[cmp_col], errors='coerce').fillna(0)
        high = pd.to_numeric(df[high_col], errors='coerce').fillna(1)
        proximity = cmp / high.replace(0, 1)  # 1.0 = at 52w high

        def proximity_pts(p):
            if p >= 0.90:
                return 15   # within 10% of 52w high: strong
            elif p >= 0.75:
                return 8    # within 25%: moderate
            else:
                return 0

        df['tech_score'] += proximity.apply(proximity_pts)

    # ── Volume Score (0–10 pts) ─────────────────────────────────────────────
    # Relative flag: above 500k absolute (filters illiquid stocks) AND
    # also in the top 40% of the dataset by volume.
    vol_col = next((c for c in df.columns if 'Volume' in c), None)
    if vol_col:
        vol = pd.to_numeric(df[vol_col], errors='coerce').fillna(0)
        df['vol_flag'] = vol > 500000
        vol_rank = vol.rank(pct=True)
        high_vol = df['vol_flag'] & (vol_rank >= 0.60)
        df.loc[high_vol, 'tech_score'] += 10
        df.loc[df['vol_flag'] & ~high_vol, 'tech_score'] += 5

    # ── Valuation Score (0–10 pts) ──────────────────────────────────────────
    # Reward low PE, but don't brutally punish growth stocks.
    pe_col = next((c for c in df.columns if 'P/E' in c or 'Price to Earning' in c), None)
    if pe_col:
        pe = pd.to_numeric(df[pe_col], errors='coerce')
        df['pe_flag'] = pe < 25

        def pe_pts(p):
            if pd.isna(p) or p <= 0:
                return 0    # negative PE or missing: no credit
            elif p <= 15:
                return 10
            elif p <= 25:
                return 7
            elif p <= 40:
                return 3
            else:
                return 0

        df['tech_score'] += pe.apply(pe_pts)

    df['tech_score'] = df['tech_score'].round(1)
    df = df.sort_values(by='tech_score', ascending=False).head(settings.MAX_CANDIDATES)
    return df
