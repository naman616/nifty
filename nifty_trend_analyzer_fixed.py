"""
Nifty 50 Trend Analyzer — Optimized Edition
Improvements over original:
  - Single-pass indicator calculation (no redundant rolling/ewm calls)
  - ATR + Stochastic RSI + Volume trend added
  - Weighted signal scoring (trend counts more than single indicators)
  - ANSI-coloured terminal output
  - Timestamped CSV & TXT exports (no silent overwrites)
  - Type hints, logging, and clean error handling throughout
"""

import re
import sys
import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ── ANSI colours ──────────────────────────────────────────────────────────────
G, R, Y, C, B, X = "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[1m", "\033[0m"

def clr(text: str, code: str) -> str:   return f"{code}{text}{X}"
def strip_ansi(s: str) -> str:          return re.sub(r"\033\[[0-9;]*m", "", s)

SEP  = "=" * 70
DASH = "-" * 70

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)


# ── 1. Data fetch ─────────────────────────────────────────────────────────────
def fetch_data(days: int = 120) -> pd.DataFrame:
    log.info("Downloading Nifty 50 data (%d days)…", days)
    df: pd.DataFrame = yf.download("^NSEI", period=f"{days}d", progress=False)
    if df.empty:
        raise RuntimeError("No data returned. Check your internet connection.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.sort_index(inplace=True)
    log.info("Loaded %d rows  (latest close: %s)", len(df), df.index[-1].date())
    return df


# ── 2. Indicators (single pass) ───────────────────────────────────────────────
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all indicators in one function — avoids repeated passes over data."""
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]

    # Moving averages
    df["SMA_20"] = c.rolling(20).mean()
    df["SMA_50"] = c.rolling(50).mean()
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["EMA_12"] = ema12
    df["EMA_26"] = ema26

    # RSI-14
    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

    # MACD
    df["MACD"]      = ema12 - ema26
    df["MACD_Sig"]  = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Sig"]

    # Bollinger Bands
    std20           = c.rolling(20).std()
    df["BB_Mid"]    = df["SMA_20"]
    df["BB_Upper"]  = df["BB_Mid"] + 2 * std20
    df["BB_Lower"]  = df["BB_Mid"] - 2 * std20
    df["BB_Pct"]    = (c - df["BB_Lower"]) / (df["BB_Upper"] - df["BB_Lower"]) * 100

    # ATR-14 (volatility proxy)
    tr             = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    df["ATR"]      = tr.rolling(14).mean()

    # Stochastic RSI (3-period smoothed)
    rsi_min        = df["RSI"].rolling(14).min()
    rsi_max        = df["RSI"].rolling(14).max()
    stoch_raw      = (df["RSI"] - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan) * 100
    df["StochRSI"] = stoch_raw.rolling(3).mean()

    # Volume trend
    df["Vol_SMA20"] = v.rolling(20).mean()
    df["Vol_Ratio"] = v / df["Vol_SMA20"]

    return df


# ── 3. Signal engine ──────────────────────────────────────────────────────────
def _score(df: pd.DataFrame) -> dict:
    """Return a dict of individual indicator readings and a composite score."""
    row  = df.iloc[-1]
    prev = df.iloc[-2]

    price  = float(row["Close"])
    sma20  = float(row["SMA_20"])
    sma50  = float(row["SMA_50"])
    rsi    = float(row["RSI"])
    macd   = float(row["MACD"])
    msig   = float(row["MACD_Sig"])
    mhist  = float(row["MACD_Hist"])
    mhist_prev = float(prev["MACD_Hist"])
    bb_pct = float(row["BB_Pct"])
    stoch  = float(row["StochRSI"])
    atr    = float(row["ATR"])
    vr     = float(row["Vol_Ratio"])

    recent   = df.tail(20)
    support  = float(recent["Low"].min())
    resist   = float(recent["High"].max())

    # ── Trend (weight ×2)
    if price > sma20 > sma50:
        trend, t_str, t_score = "Strong Uptrend",       "Strong",   +2
    elif price > sma20 and price > sma50:
        trend, t_str, t_score = "Uptrend",              "Moderate", +1
    elif price < sma20 < sma50:
        trend, t_str, t_score = "Strong Downtrend",     "Strong",   -2
    elif price < sma20 and price < sma50:
        trend, t_str, t_score = "Downtrend",            "Moderate", -1
    else:
        trend, t_str, t_score = "Sideways",             "Weak",      0

    # ── RSI (weight ×1)
    if rsi > 70:    rsi_lbl, rsi_score = "Overbought",  -1
    elif rsi < 30:  rsi_lbl, rsi_score = "Oversold",    +1
    else:           rsi_lbl, rsi_score = "Neutral",      0

    # ── MACD (weight ×1 + histogram flip bonus)
    if macd > msig and macd > 0:    macd_lbl, macd_score = "Bullish Crossover", +1
    elif macd < msig and macd < 0:  macd_lbl, macd_score = "Bearish Crossover", -1
    else:                           macd_lbl, macd_score = "Neutral",             0
    if mhist > 0 and mhist_prev < 0:   macd_score += 0.5   # fresh bullish flip
    elif mhist < 0 and mhist_prev > 0: macd_score -= 0.5   # fresh bearish flip

    # ── Stochastic RSI (weight ×0.5)
    if stoch > 80:    stoch_lbl, stoch_score = "Overbought", -0.5
    elif stoch < 20:  stoch_lbl, stoch_score = "Oversold",   +0.5
    else:             stoch_lbl, stoch_score = "Neutral",      0

    # ── Bollinger Band position (weight ×0.5)
    if bb_pct > 90:     bb_lbl, bb_score = "Near Upper Band", -0.5
    elif bb_pct < 10:   bb_lbl, bb_score = "Near Lower Band", +0.5
    else:               bb_lbl, bb_score = "Inside Bands",     0

    # ── Volume confirmation (weight ×0.5)
    vol_score = 0.3 if vr > 1.3 and t_score > 0 else (-0.3 if vr > 1.3 and t_score < 0 else 0)

    total = t_score + rsi_score + macd_score + stoch_score + bb_score + vol_score

    return dict(
        price=price, sma20=sma20, sma50=sma50,
        rsi=rsi,   rsi_lbl=rsi_lbl,
        macd=macd, msig=msig, mhist=mhist, macd_lbl=macd_lbl,
        stoch=stoch, stoch_lbl=stoch_lbl,
        bb_pct=bb_pct, bb_lbl=bb_lbl,
        bb_upper=float(row["BB_Upper"]), bb_lower=float(row["BB_Lower"]),
        atr=atr, vr=vr,
        support=support, resist=resist,
        trend=trend, t_str=t_str,
        score=total,
    )


def build_analysis(df: pd.DataFrame) -> dict:
    s    = _score(df)
    prev = float(df.iloc[-2]["Close"])
    chg  = s["price"] - prev
    chg_pct = chg / prev * 100

    if s["score"] >= 2:
        action, risk = "BUY",        "Low–Medium"
    elif s["score"] <= -1.5:
        action, risk = "SELL",       "High"
    else:
        action, risk = "HOLD/WATCH", "Medium"

    # Build suggestion list
    tips = []
    if action == "BUY":
        tips += [
            f"  [+] Composite score {s['score']:+.1f} — bullish bias",
            f"  [>] Consider entries near support ₹{s['support']:,.2f}",
            f"  [T] Initial target: ₹{s['resist']:,.2f}",
            f"  [S] Stop-loss guide: 1–2× ATR (≈ ₹{s['atr']:,.2f}) below entry",
        ]
    elif action == "SELL":
        tips += [
            f"  [!] Composite score {s['score']:+.1f} — bearish bias",
            f"  [>] Book profits / avoid fresh longs",
            f"  [W] Watch support at ₹{s['support']:,.2f} for potential reversal",
        ]
    else:
        tips += [
            f"  [~] Composite score {s['score']:+.1f} — mixed signals",
            f"  [W] Range ₹{s['support']:,.2f} – ₹{s['resist']:,.2f}",
            f"  [>] Wait for MACD histogram or RSI to confirm direction",
        ]

    if s["rsi_lbl"] == "Oversold":
        tips.append("  [i] RSI oversold — watch for bounce")
    elif s["rsi_lbl"] == "Overbought":
        tips.append("  [i] RSI overbought — profit-booking zone")

    if s["bb_pct"] < 10:
        tips.append("  [v] Price hugging lower Bollinger Band — potential mean-reversion")
    elif s["bb_pct"] > 90:
        tips.append("  [^] Price hugging upper Bollinger Band — resistance likely")

    if s["vr"] > 1.5:
        tips.append(f"  [V] Volume {s['vr']:.1f}× average — strong conviction today")
    elif s["vr"] < 0.6:
        tips.append(f"  [v] Volume {s['vr']:.1f}× average — low conviction, treat move cautiously")

    s.update(prev=prev, chg=chg, chg_pct=chg_pct, action=action, risk=risk, tips=tips)
    return s


# ── 4. Report ─────────────────────────────────────────────────────────────────
def _fmt(label: str, val: float, w: int = 18) -> str:
    return f"  {label:<{w}} ₹{val:>12,.2f}"


def report_lines(a: dict) -> list[str]:
    now   = datetime.now().strftime("%d %B %Y, %I:%M %p")
    arrow = clr("▲ UP",   G) if a["chg"] >= 0 else clr("▼ DOWN", R)
    tc    = G if "Up" in a["trend"] else (R if "Down" in a["trend"] else Y)
    ac    = G if a["action"] == "BUY" else (R if a["action"] == "SELL" else Y)

    return [
        "",
        clr(SEP, C),
        clr(f"{'NIFTY 50 — TREND ANALYSIS REPORT':^70}", B),
        clr(SEP, C),
        f"  Date  : {now}",
        f"  Score : {a['score']:+.1f}  (≥2 Bullish | ≤-1.5 Bearish | else Neutral)",
        clr(SEP, C),

        "",
        clr("  PRICE SUMMARY", B),
        DASH,
        _fmt("Current",       a["price"]),
        _fmt("Previous Close",a["prev"]),
        f"  {'Change':<18} ₹{a['chg']:>+12,.2f}  ({a['chg_pct']:+.2f}%)  {arrow}",

        "",
        clr("  TREND & MOVING AVERAGES", B),
        DASH,
        f"  Trend   : {clr(a['trend'], tc)}  [{a['t_str']}]",
        _fmt("SMA 20-day",  a["sma20"]),
        _fmt("SMA 50-day",  a["sma50"]),

        "",
        clr("  MOMENTUM INDICATORS", B),
        DASH,
        f"  RSI (14)      : {a['rsi']:.2f}  → {a['rsi_lbl']}",
        f"  MACD          : {a['macd']:+.2f}  |  Signal: {a['msig']:+.2f}  |  Hist: {a['mhist']:+.2f}",
        f"  MACD Status   : {a['macd_lbl']}",
        f"  Stoch RSI     : {a['stoch']:.1f}  → {a['stoch_lbl']}",

        "",
        clr("  VOLATILITY (BOLLINGER BANDS)", B),
        DASH,
        _fmt("Upper Band",  a["bb_upper"]),
        _fmt("Current",     a["price"]),
        _fmt("Lower Band",  a["bb_lower"]),
        f"  BB Position   : {a['bb_pct']:.1f}%  → {a['bb_lbl']}",
        f"  ATR (14-day)  : ₹{a['atr']:,.2f}  (expected daily range)",

        "",
        clr("  SUPPORT & RESISTANCE  (last 20 sessions)", B),
        DASH,
        _fmt("Resistance",  a["resist"]) + "  ← ceiling",
        _fmt("Current",     a["price"]),
        _fmt("Support",     a["support"]) + "  ← floor",

        "",
        clr("  VOLUME", B),
        DASH,
        f"  Ratio vs 20-day avg : {a['vr']:.2f}×",

        "",
        clr(SEP, C),
        clr(f"  {'RECOMMENDATION':^68}", B),
        clr(SEP, C),
        f"  ACTION     : {clr(a['action'], ac)}",
        f"  RISK LEVEL : {a['risk']}",
        clr(SEP, C),

        "",
        clr("  SUGGESTIONS", B),
        DASH,
        *a["tips"],

        "",
        clr(SEP, C),
        clr("  DISCLAIMER", B),
        DASH,
        "  • For educational purposes only — not financial advice.",
        "  • Consult a SEBI-registered advisor before investing.",
        "  • Never invest funds you cannot afford to lose.",
        clr(SEP, C),
        "",
    ]


def print_report(a: dict) -> None:
    for ln in report_lines(a):
        print(ln)


# ── 5. Export ─────────────────────────────────────────────────────────────────
def save_txt(a: dict, out: Path) -> Path:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out / f"nifty_report_{ts}.txt"
    path.write_text("\n".join(strip_ansi(ln) for ln in report_lines(a)), encoding="utf-8")
    return path


def save_csv(df: pd.DataFrame, out: Path) -> Path:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out / f"nifty_data_{ts}.csv"
    cols = ["Open", "High", "Low", "Close", "Volume",
            "SMA_20", "SMA_50", "EMA_12", "EMA_26",
            "RSI", "MACD", "MACD_Sig", "MACD_Hist",
            "BB_Upper", "BB_Mid", "BB_Lower", "BB_Pct",
            "ATR", "StochRSI", "Vol_Ratio"]
    df[cols].tail(60).to_csv(path)
    return path


# ── 6. Entry point ────────────────────────────────────────────────────────────
def main(days: int = 120, output_dir: Optional[str] = None) -> tuple[pd.DataFrame, dict]:
    out = Path(output_dir or ".")
    out.mkdir(parents=True, exist_ok=True)

    print(clr(SEP, C))
    print(clr(f"{'NIFTY 50 TREND ANALYZER':^70}", B))
    print(clr(SEP, C))

    try:
        df = fetch_data(days)
    except RuntimeError as e:
        log.error(str(e)); sys.exit(1)

    log.info("Computing indicators…")
    df = add_indicators(df)

    log.info("Scoring signals…")
    analysis = build_analysis(df)

    print_report(analysis)

    txt = save_txt(analysis, out)
    csv = save_csv(df, out)
    log.info("Report saved  → %s", txt)
    log.info("CSV saved     → %s", csv)

    # Last-5-days summary
    print(clr("\n  LAST 5 SESSIONS", B))
    print(DASH)
    summary_cols = ["Open", "High", "Low", "Close", "RSI", "MACD", "Vol_Ratio"]
    print(df[summary_cols].tail().to_string())
    print()

    return df, analysis


if __name__ == "__main__":
    df, analysis = main()