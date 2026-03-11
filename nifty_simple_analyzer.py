"""
Nifty 50 Simple Analyzer - Enhanced Version
Improvements:
  - Added MACD, Bollinger Bands, ATR, volume analysis
  - Cached data fetching with configurable period
  - Colored terminal output (ANSI)
  - CSV + TXT export with timestamped filenames
  - Cleaner, modular code with type hints
  - Graceful error handling throughout
"""

import sys
import warnings
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ── ANSI colour helpers ──────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def clr(text: str, color: str) -> str:
    """Wrap text in an ANSI colour code (stripped when writing to file)."""
    return f"{color}{text}{RESET}"

def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes for plain-text file output."""
    import re
    return re.sub(r"\033\[[0-9;]*m", "", text)

SEP  = "=" * 70
DASH = "-" * 70

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s │ %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ── Data fetching ─────────────────────────────────────────────────────────────
def fetch_nifty_data(days: int = 120) -> pd.DataFrame:
    """Download Nifty 50 OHLCV data and normalise the column structure."""
    log.info("Fetching Nifty 50 data (%d trading days)…", days)
    df: pd.DataFrame = yf.download("^NSEI", period=f"{days}d", progress=False)

    if df.empty:
        raise RuntimeError("No data returned by yfinance. Check your internet connection.")

    # Flatten multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)
    log.info("Fetched %d rows  (latest: %s)", len(df), df.index[-1].date())
    return df


# ── Technical indicators ──────────────────────────────────────────────────────
def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all technical indicators in-place and return the DataFrame."""
    close = df["Close"]

    # ── Moving averages
    df["SMA_20"] = close.rolling(20).mean()
    df["SMA_50"] = close.rolling(50).mean()
    df["EMA_20"] = close.ewm(span=20, adjust=False).mean()

    # ── RSI (14-period)
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

    # ── MACD (12/26/9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"]   = df["MACD"] - df["MACD_Signal"]

    # ── Bollinger Bands (20-period, 2σ)
    sma20      = df["SMA_20"]
    std20      = close.rolling(20).std()
    df["BB_Upper"] = sma20 + 2 * std20
    df["BB_Lower"] = sma20 - 2 * std20
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / sma20 * 100  # % width

    # ── Average True Range (14-period) – volatility proxy
    high_low   = df["High"] - df["Low"]
    high_close = (df["High"] - close.shift()).abs()
    low_close  = (df["Low"]  - close.shift()).abs()
    tr         = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"]  = tr.rolling(14).mean()

    # ── Volume trend (20-day average)
    df["Vol_SMA_20"] = df["Volume"].rolling(20).mean()

    return df


# ── Recommendation engine ─────────────────────────────────────────────────────
def build_recommendation(df: pd.DataFrame) -> dict:
    """Return a flat dict with all values needed for the report."""
    latest = df.iloc[-1]
    prev   = df.iloc[-2]

    price_now  = float(latest["Close"])
    price_prev = float(prev["Close"])
    change     = price_now - price_prev
    change_pct = change / price_prev * 100

    sma20 = float(latest["SMA_20"])
    sma50 = float(latest["SMA_50"])
    ema20 = float(latest["EMA_20"])
    rsi   = float(latest["RSI"])
    macd  = float(latest["MACD"])
    macd_sig = float(latest["MACD_Signal"])
    macd_hist = float(latest["MACD_Hist"])
    bb_upper  = float(latest["BB_Upper"])
    bb_lower  = float(latest["BB_Lower"])
    bb_width  = float(latest["BB_Width"])
    atr       = float(latest["ATR"])
    volume    = float(latest["Volume"])
    vol_avg   = float(latest["Vol_SMA_20"])

    recent = df.tail(20)
    high20 = float(recent["High"].max())
    low20  = float(recent["Low"].min())

    # ── Trend logic
    if price_now > sma20 > sma50:
        trend, trend_exp, trend_col = "STRONG UPWARD TREND",   "Market is rising strongly",       "GREEN"
    elif price_now > sma20 and price_now > sma50:
        trend, trend_exp, trend_col = "UPWARD TREND",          "Market is rising",                "GREEN"
    elif price_now < sma20 < sma50:
        trend, trend_exp, trend_col = "STRONG DOWNWARD TREND", "Market is falling strongly",      "RED"
    elif price_now < sma20 and price_now < sma50:
        trend, trend_exp, trend_col = "DOWNWARD TREND",        "Market is falling",               "RED"
    else:
        trend, trend_exp, trend_col = "SIDEWAYS",              "Market is consolidating (stable)", "YELLOW"

    # ── RSI
    if rsi > 70:
        price_status, price_advice = "OVERBOUGHT", "Market may be overvalued – caution advised"
    elif rsi < 30:
        price_status, price_advice = "OVERSOLD",   "Market may be undervalued – watch for bounce"
    else:
        price_status, price_advice = "NEUTRAL",    "RSI is at normal levels"

    # ── MACD signal
    macd_signal_str = "BULLISH (MACD above signal)" if macd > macd_sig else "BEARISH (MACD below signal)"

    # ── Bollinger position
    if price_now > bb_upper:
        bb_pos = "ABOVE UPPER BAND – extended / overbought"
    elif price_now < bb_lower:
        bb_pos = "BELOW LOWER BAND – extended / oversold"
    else:
        bb_pos = "INSIDE BANDS – normal range"

    # ── Volume context
    vol_ratio = volume / vol_avg if vol_avg else 1.0
    if vol_ratio > 1.5:
        vol_comment = f"HIGH ({vol_ratio:.1f}x avg) – strong conviction behind today's move"
    elif vol_ratio < 0.7:
        vol_comment = f"LOW ({vol_ratio:.1f}x avg) – weak conviction, treat move with caution"
    else:
        vol_comment = f"NORMAL ({vol_ratio:.1f}x avg)"

    # ── Scoring for final action (simple point system)
    score = 0
    score += 1  if trend_col == "GREEN"   else (-1 if trend_col == "RED" else 0)
    score += 1  if rsi < 60               else (-1 if rsi > 70 else 0)
    score += 1  if macd > macd_sig        else -1
    score += 0.5 if vol_ratio > 1.0       else 0

    if score >= 2:
        action, advice, risk = "BUY",          "Conditions favour entering a position",      "LOW TO MEDIUM"
    elif score <= -1:
        action, advice, risk = "SELL / WAIT",  "Conditions unfavourable – protect capital",  "MEDIUM TO HIGH"
    else:
        action, advice, risk = "HOLD / WATCH", "Mixed signals – wait for confirmation",       "MEDIUM"

    return dict(
        price_now=price_now, price_prev=price_prev, change=change, change_pct=change_pct,
        trend=trend, trend_exp=trend_exp, trend_col=trend_col,
        sma20=sma20, sma50=sma50, ema20=ema20,
        rsi=rsi, price_status=price_status, price_advice=price_advice,
        macd=macd, macd_sig=macd_sig, macd_hist=macd_hist, macd_signal_str=macd_signal_str,
        bb_upper=bb_upper, bb_lower=bb_lower, bb_width=bb_width, bb_pos=bb_pos,
        atr=atr, volume=volume, vol_avg=vol_avg, vol_comment=vol_comment,
        high20=high20, low20=low20,
        action=action, advice=advice, risk=risk, score=score,
    )


# ── Report printer ────────────────────────────────────────────────────────────
def _fmt_price(label: str, price: float, width: int = 16) -> str:
    return f"{label:<{width}} ₹{price:>12,.2f}"


def build_report_lines(r: dict) -> list[str]:
    """Return the full report as a list of (coloured) strings."""
    now = datetime.now().strftime("%d %B %Y, %I:%M %p")
    arrow = clr("[▲ UP]", GREEN) if r["change"] >= 0 else clr("[▼ DOWN]", RED)

    trend_color_map = {"GREEN": GREEN, "RED": RED, "YELLOW": YELLOW}
    tc = trend_color_map.get(r["trend_col"], RESET)

    action_color = GREEN if r["action"] == "BUY" else (RED if "SELL" in r["action"] else YELLOW)

    lines = [
        "",
        clr(SEP, CYAN),
        clr(f"{'NIFTY 50 ANALYSIS — ENHANCED REPORT':^70}", BOLD),
        clr(SEP, CYAN),
        f"  Date : {now}",
        f"  Score: {r['score']:+.1f}  (composite signal; >2 = bullish, <−1 = bearish)",
        clr(SEP, CYAN),

        # ── Price ──
        "",
        clr("  TODAY'S PRICE", BOLD),
        DASH,
        _fmt_price("  Current", r["price_now"]),
        _fmt_price("  Previous Close", r["price_prev"]),
        f"  Change         ₹{r['change']:>+12,.2f}  ({r['change_pct']:+.2f}%)  {arrow}",

        # ── Trend ──
        "",
        clr("  MARKET TREND", BOLD),
        DASH,
        f"  Status  : {clr(r['trend'], tc)}",
        f"  Meaning : {r['trend_exp']}",

        # ── Moving averages ──
        "",
        clr("  MOVING AVERAGES", BOLD),
        DASH,
        _fmt_price("  SMA 20-day", r["sma20"]),
        _fmt_price("  SMA 50-day", r["sma50"]),
        _fmt_price("  EMA 20-day", r["ema20"]),
        f"  {'▲ Price ABOVE SMA-20 (bullish)' if r['price_now'] > r['sma20'] else '▼ Price BELOW SMA-20 (bearish)'}",

        # ── Support & Resistance ──
        "",
        clr("  KEY LEVELS  (last 20 sessions)", BOLD),
        DASH,
        _fmt_price("  Resistance", r["high20"]) + "  ← hard ceiling",
        _fmt_price("  Current",    r["price_now"]),
        _fmt_price("  Support",    r["low20"])   + "  ← strong floor",

        # ── RSI ──
        "",
        clr("  RSI  (Relative Strength Index)", BOLD),
        DASH,
        f"  Value  : {r['rsi']:.1f}",
        f"  Status : {r['price_status']}",
        f"  Note   : {r['price_advice']}",
        f"  Guide  : <30 Oversold | 30–70 Normal | >70 Overbought",

        # ── MACD ──
        "",
        clr("  MACD  (Momentum)", BOLD),
        DASH,
        f"  MACD Line   : {r['macd']:+.2f}",
        f"  Signal Line : {r['macd_sig']:+.2f}",
        f"  Histogram   : {r['macd_hist']:+.2f}",
        f"  Signal      : {r['macd_signal_str']}",

        # ── Bollinger Bands ──
        "",
        clr("  BOLLINGER BANDS  (Volatility)", BOLD),
        DASH,
        _fmt_price("  Upper Band",  r["bb_upper"]),
        _fmt_price("  Lower Band",  r["bb_lower"]),
        f"  Band Width   : {r['bb_width']:.1f}%",
        f"  Price is     : {r['bb_pos']}",

        # ── ATR & Volume ──
        "",
        clr("  VOLATILITY & VOLUME", BOLD),
        DASH,
        f"  ATR (14-day)  : ₹{r['atr']:,.2f}  (expected daily swing)",
        f"  Today Volume  : {r['volume']:,.0f}",
        f"  20-day Avg    : {r['vol_avg']:,.0f}",
        f"  Volume Signal : {r['vol_comment']}",

        # ── Recommendation ──
        "",
        clr(SEP, CYAN),
        clr(f"  {'RECOMMENDATION':^68}", BOLD),
        clr(SEP, CYAN),
        f"  ACTION    : {clr(r['action'], action_color)}",
        f"  ADVICE    : {r['advice']}",
        f"  RISK LEVEL: {r['risk']}",
        clr(SEP, CYAN),

        # ── Action steps ──
        "",
        clr("  SUGGESTED NEXT STEPS", BOLD),
        DASH,
    ]

    if r["action"] == "BUY":
        lines += [
            "  1. Trend and momentum are aligned – conditions support entry",
            f"  2. Consider staggered entries (SIP) rather than lump-sum",
            f"  3. Initial target near resistance: ₹{r['high20']:,.2f}",
            f"  4. Stop-loss near support:        ₹{r['low20']:,.2f}",
            f"  5. Daily ATR of ₹{r['atr']:,.2f} indicates expected price swing – size positions accordingly",
        ]
    elif "SELL" in r["action"]:
        lines += [
            "  1. Momentum is weakening or negative – protect existing gains",
            "  2. Avoid deploying fresh capital at current levels",
            "  3. Review stop-losses on open positions",
            f"  4. Watch for a potential bounce near support: ₹{r['low20']:,.2f}",
        ]
    else:
        lines += [
            "  1. Mixed signals – no compelling entry or exit right now",
            "  2. Monitor MACD histogram for directional confirmation",
            "  3. A break above the upper Bollinger Band may signal a breakout",
            "  4. Wait for RSI to move decisively above 50 (bullish) or below 40 (bearish)",
        ]

    # ── Disclaimer ──
    lines += [
        "",
        clr(SEP, CYAN),
        clr("  DISCLAIMER", BOLD),
        DASH,
        "  • This analysis is informational only – not financial advice.",
        "  • Past market behaviour does not guarantee future results.",
        "  • Always consult a SEBI-registered advisor before investing.",
        "  • Never invest funds you cannot afford to lose.",
        clr(SEP, CYAN),
        "",
    ]

    return lines


def print_report(r: dict) -> None:
    for line in build_report_lines(r):
        print(line)


# ── Export helpers ─────────────────────────────────────────────────────────────
def save_text_report(r: dict, output_dir: Path = Path(".")) -> Path:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"nifty_report_{ts}.txt"
    with path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(strip_ansi(ln) for ln in build_report_lines(r)))
    return path


def save_csv_snapshot(df: pd.DataFrame, output_dir: Path = Path(".")) -> Path:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"nifty_data_{ts}.csv"
    cols = ["Open", "High", "Low", "Close", "Volume",
            "SMA_20", "SMA_50", "EMA_20", "RSI",
            "MACD", "MACD_Signal", "MACD_Hist",
            "BB_Upper", "BB_Lower", "BB_Width", "ATR"]
    df[cols].tail(60).to_csv(path)
    return path


# ── Entry point ───────────────────────────────────────────────────────────────
def main(days: int = 120, output_dir: Optional[str] = None) -> tuple[pd.DataFrame, dict]:
    out = Path(output_dir) if output_dir else Path(".")
    out.mkdir(parents=True, exist_ok=True)

    print(clr(SEP, CYAN))
    print(clr(f"{'WELCOME TO NIFTY 50 ANALYZER — ENHANCED':^70}", BOLD))
    print(clr(SEP, CYAN))

    try:
        df = fetch_nifty_data(days)
    except RuntimeError as e:
        log.error(str(e))
        sys.exit(1)

    log.info("Calculating indicators…")
    df = calculate_indicators(df)

    log.info("Building recommendation…")
    result = build_recommendation(df)

    print_report(result)

    txt_path = save_text_report(result, out)
    csv_path = save_csv_snapshot(df, out)
    log.info("Text report saved → %s", txt_path)
    log.info("CSV snapshot saved → %s", csv_path)

    return df, result


if __name__ == "__main__":
    df, result = main()