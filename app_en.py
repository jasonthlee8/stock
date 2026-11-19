# -*- coding: utf-8 -*-
"""Stock Technical Analysis Tool - Web version (Streamlit, English)"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Stock Technical Analysis Tool", page_icon="📈", layout="wide")

PRESETS = [
    "AAPL", "MSFT", "GOOG", "NVDA", "0883.HK", "0005.HK", "0981.HK", "0941.HK",
    "0857.HK", "1398.HK", "6823.HK", "2388.HK", "2638.HK", "VT", "QQQ", "KO",
    "VOO", "JNJ", "NET", "0008.HK",
]
PERIODS = {"Last 3 months": "3mo", "Last 6 months": "6mo", "Last 1 year": "1y",
           "Last 2 years": "2y", "Last 5 years": "5y"}


# ---------------------------------------------------------------- Data & indicators
def normalize_ticker(symbol: str) -> str:
    symbol = (symbol or "AAPL").strip().upper()
    if symbol.endswith(".US"):
        return symbol[:-3]
    if symbol.endswith(".HK"):
        code = symbol[:-3]
        if code.isdigit():
            return code.zfill(4) + ".HK"
    return symbol


@st.cache_data(ttl=900, show_spinner="Downloading data…")
def download_data(symbol: str, period: str) -> pd.DataFrame:
    ticker = normalize_ticker(symbol)
    df = yf.download(ticker, period=period, auto_adjust=False, progress=False, group_by="column")
    if df is None or df.empty:
        raise ValueError(f"No data found for ticker: {ticker}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna().copy()
    if len(df) < 30:
        raise ValueError(f"Not enough data to compute indicators: {ticker}")
    return df


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    c = out["Close"]

    for n in (20, 50, 200):
        out[f"MA{n}"] = c.rolling(n).mean()

    # RSI (Wilder)
    diff = c.diff()
    up = diff.clip(lower=0)
    down = -diff.clip(upper=0)
    avg_up = up.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_down = down.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = avg_up / avg_down.replace(0, np.nan)
    out["RSI14"] = (100 - 100 / (1 + rs)).fillna(100.0).where(avg_up.notna())

    # MACD (12, 26, 9)
    ema12 = c.ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = c.ewm(span=26, adjust=False, min_periods=26).mean()
    out["MACD"] = ema12 - ema26
    out["MACD_signal"] = out["MACD"].ewm(span=9, adjust=False, min_periods=9).mean()
    out["MACD_hist"] = out["MACD"] - out["MACD_signal"]

    out["Vol20"] = out["Volume"].rolling(20).mean()

    # Bollinger Bands (20, 2)
    std = c.rolling(20).std(ddof=0)
    out["BB_MID"] = out["MA20"]
    out["BB_UPPER"] = out["BB_MID"] + 2 * std
    out["BB_LOWER"] = out["BB_MID"] - 2 * std
    out["BB_WIDTH"] = out["BB_UPPER"] - out["BB_LOWER"]
    out["BB_PERCENT"] = (c - out["BB_LOWER"]) / out["BB_WIDTH"]
    return out


def get_signal(row) -> str:
    needed = ["Close", "MA20", "MA50", "RSI14", "MACD", "MACD_signal"]
    if any(pd.isna(row.get(k)) for k in needed):
        return "N/A"
    if row["Close"] > row["MA20"] > row["MA50"] and 50 < row["RSI14"] < 70 and row["MACD"] > row["MACD_signal"]:
        return "Buy watch"
    if row["Close"] < row["MA20"] < row["MA50"] and row["RSI14"] < 50 and row["MACD"] < row["MACD_signal"]:
        return "Sell watch"
    return "Hold / Neutral"


def get_bb_status(row) -> str:
    if pd.isna(row.get("BB_UPPER")) or pd.isna(row.get("BB_LOWER")):
        return "N/A"
    if row["Close"] > row["BB_UPPER"]:
        return "Above upper band"
    if row["Close"] < row["BB_LOWER"]:
        return "Below lower band"
    return "Above middle band" if row["Close"] > row["BB_MID"] else "Below middle band"


def get_volatility_status(df: pd.DataFrame) -> str:
    recent = df["BB_WIDTH"].dropna().tail(20)
    if len(recent) < 10:
        return "N/A"
    cur, avg = recent.iloc[-1], recent.mean()
    if cur > avg * 1.15:
        return "Expanding"
    if cur < avg * 0.85:
        return "Contracting"
    return "Normal"


# ---------------------------------------------------------------- Charts
def _layout(fig, title, ylabel, height=420):
    fig.update_layout(
        title=title, xaxis_title="Date", yaxis_title=ylabel, height=height,
        hovermode="x unified", margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def plot_price(df, t):
    f = go.Figure()
    f.add_trace(go.Scatter(x=df.index, y=df.BB_UPPER, name="Upper band", line=dict(color="red", dash="dash", width=1)))
    f.add_trace(go.Scatter(x=df.index, y=df.BB_LOWER, name="Lower band", line=dict(color="green", dash="dash", width=1),
                           fill="tonexty", fillcolor="rgba(128,128,128,0.12)"))
    f.add_trace(go.Scatter(x=df.index, y=df.BB_MID, name="Middle band", line=dict(color="purple", dash="dash", width=1)))
    f.add_trace(go.Scatter(x=df.index, y=df.MA20, name="MA20", line=dict(color="#1f77b4", width=1.5)))
    f.add_trace(go.Scatter(x=df.index, y=df.MA50, name="MA50", line=dict(color="#ff7f0e", width=1.5)))
    f.add_trace(go.Scatter(x=df.index, y=df.MA200, name="MA200", line=dict(color="#2ca02c", width=1.5)))
    f.add_trace(go.Scatter(x=df.index, y=df.Close, name="Close", line=dict(color="black", width=2)))
    return _layout(f, f"{t} Price + Moving Averages + Bollinger Bands", "Price", 520)


def plot_rsi(df, t):
    f = go.Figure(go.Scatter(x=df.index, y=df.RSI14, name="RSI 14", line=dict(color="purple", width=2)))
    f.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought 70")
    f.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold 30")
    f.update_yaxes(range=[0, 100])
    return _layout(f, f"{t} RSI 14 (Relative Strength Index)", "RSI", 320)


def plot_macd(df, t):
    f = go.Figure()
    f.add_trace(go.Bar(x=df.index, y=df.MACD_hist, name="Histogram", opacity=0.4))
    f.add_trace(go.Scatter(x=df.index, y=df.MACD, name="MACD", line=dict(color="blue", width=2)))
    f.add_trace(go.Scatter(x=df.index, y=df.MACD_signal, name="Signal line", line=dict(color="orange", width=2)))
    return _layout(f, f"{t} MACD", "Value", 340)


def plot_volume(df, t):
    f = go.Figure()
    f.add_trace(go.Bar(x=df.index, y=df.Volume / 1e6, name="Volume (millions)", opacity=0.7))
    f.add_trace(go.Scatter(x=df.index, y=df.Vol20 / 1e6, name="20-day avg volume", line=dict(color="black", width=1.5)))
    return _layout(f, f"{t} Volume", "Millions of shares", 320)


def plot_bb_width(df, t):
    f = go.Figure(go.Scatter(x=df.index, y=df.BB_WIDTH, name="Band width", line=dict(color="brown", width=2)))
    return _layout(f, f"{t} Bollinger Band Width", "Width", 300)


# ---------------------------------------------------------------- Summary
def show_summary(df, symbol):
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    chg = latest.Close - prev.Close
    chg_pct = chg / prev.Close * 100 if prev.Close else 0
    avg_vol = df.Volume.tail(20).mean()

    trend = "Bullish" if pd.notna(latest.MA50) and latest.Close > latest.MA50 else "Weak"
    rsi_state = "Overbought" if latest.RSI14 > 70 else "Oversold" if latest.RSI14 < 30 else "Neutral"
    macd_state = "Above signal" if latest.MACD > latest.MACD_signal else "Below signal"
    vol_state = "Above 20-day average" if latest.Volume > avg_vol else "Normal or below average"
    f = lambda v, d=2: f"{v:.{d}f}" if pd.notna(v) else "-"

    st.subheader(f"Summary: {normalize_ticker(symbol)}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Close", f(latest.Close), f"{chg:+.2f} ({chg_pct:+.2f}%)")
    c2.metric("RSI14", f(latest.RSI14), rsi_state, delta_color="off")
    c3.metric("Signal", get_signal(latest))
    c4.metric("Trend", trend)

    st.markdown(
        f"- Date: **{df.index[-1].date()}**\n"
        f"- MA20 / MA50 / MA200: **{f(latest.MA20)} / {f(latest.MA50)} / {f(latest.MA200)}**\n"
        f"- MACD / Signal line: **{f(latest.MACD, 3)} / {f(latest.MACD_signal, 3)}** ({macd_state})\n"
        f"- Bollinger Bands middle / upper / lower: **{f(latest.BB_MID)} / {f(latest.BB_UPPER)} / {f(latest.BB_LOWER)}**\n"
        f"- Band position: **{get_bb_status(latest)}**; volatility: **{get_volatility_status(df)}**\n"
        f"- Volume: **{vol_state}**; 20-day average about **{avg_vol / 1e6:.1f}M**"
    )
    st.caption("Disclaimer: This is the output of a simple technical analysis tool, for reference only. "
               "It is not investment advice.")


# ---------------------------------------------------------------- UI
st.title("📈 Stock Technical Analysis Tool")
st.caption("Examples: AAPL, AAPL.US, MSFT, 0700.HK, 700.HK, 0005.HK (data source: Yahoo Finance)")

if "ticker" not in st.session_state:
    st.session_state.ticker = "AAPL"


def set_ticker(sym):
    st.session_state.ticker = sym


col1, col2, col3 = st.columns([2, 1.5, 1.5])
col1.text_input("Ticker", key="ticker", placeholder="e.g. AAPL, 0700.HK, 700.HK")
period_label = col2.selectbox("Period", list(PERIODS), index=2)
tail_n = col3.slider("Table rows", 3, 20, 5)

st.write("Quick picks:")
for row_start in range(0, len(PRESETS), 10):
    cols = st.columns(10)
    for col, sym in zip(cols, PRESETS[row_start:row_start + 10]):
        col.button(sym, key=f"p_{sym}", on_click=set_ticker, args=(sym,), use_container_width=True)

symbol = st.session_state.ticker
st.markdown(f"### Analyzing: `{symbol}` (yfinance ticker: `{normalize_ticker(symbol)}`)")

try:
    data = add_indicators(download_data(symbol, PERIODS[period_label]))
    yf_sym = normalize_ticker(symbol)

    show_summary(data, symbol)
    for fn in (plot_price, plot_rsi, plot_macd, plot_volume, plot_bb_width):
        st.plotly_chart(fn(data, yf_sym))

    st.subheader(f"Latest {tail_n} rows")
    cols = ["Open", "High", "Low", "Close", "Volume", "MA20", "MA50", "MA200", "BB_MID", "BB_UPPER",
            "BB_LOWER", "BB_WIDTH", "BB_PERCENT", "RSI14", "MACD", "MACD_signal", "MACD_hist"]
    st.dataframe(data[cols].tail(tail_n).style.format(
        {c: "{:.3f}" if c.startswith("MACD") else "{:,.0f}" if c == "Volume" else "{:.2f}" for c in cols}),
        width="stretch")
except Exception as e:
    st.error(f"Failed: {type(e).__name__}: {e}")
    st.markdown(
        "**Troubleshooting:**\n"
        "1. Hong Kong stocks use Yahoo format, e.g. `0005.HK`, `0700.HK` (`700.HK` is zero-padded automatically).\n"
        "2. `AAPL.US` is converted to `AAPL` automatically.\n"
        "3. If Yahoo Finance has no data for the ticker, try another Yahoo-format ticker."
    )
