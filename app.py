# -*- coding: utf-8 -*-
"""股票技術分析工具 - 網頁版 (Streamlit)"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="股票技術分析工具", page_icon="📈", layout="wide")

PRESETS = [
    "AAPL", "MSFT", "GOOG", "NVDA", "0883.HK", "0005.HK", "0981.HK", "0941.HK",
    "0857.HK", "1398.HK", "6823.HK", "2388.HK", "2638.HK", "VT", "QQQ", "KO",
    "VOO", "JNJ", "NET", "0008.HK",
]
PERIODS = {"近 3 個月": "3mo", "近 6 個月": "6mo", "近 1 年": "1y", "近 2 年": "2y", "近 5 年": "5y"}


# ---------------------------------------------------------------- 資料與指標
def normalize_ticker(symbol: str) -> str:
    symbol = (symbol or "AAPL").strip().upper()
    if symbol.endswith(".US"):
        return symbol[:-3]
    if symbol.endswith(".HK"):
        code = symbol[:-3]
        if code.isdigit():
            return code.zfill(4) + ".HK"
    return symbol


@st.cache_data(ttl=900, show_spinner="正在下載資料…")
def download_data(symbol: str, period: str) -> pd.DataFrame:
    ticker = normalize_ticker(symbol)
    df = yf.download(ticker, period=period, auto_adjust=False, progress=False, group_by="column")
    if df is None or df.empty:
        raise ValueError(f"找不到股票資料：{ticker}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna().copy()
    if len(df) < 30:
        raise ValueError(f"資料筆數太少，無法計算技術指標：{ticker}")
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

    # 保力加通道 (20, 2)
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
        return "買入觀察"
    if row["Close"] < row["MA20"] < row["MA50"] and row["RSI14"] < 50 and row["MACD"] < row["MACD_signal"]:
        return "賣出觀察"
    return "持有 / 觀望"


def get_bb_status(row) -> str:
    if pd.isna(row.get("BB_UPPER")) or pd.isna(row.get("BB_LOWER")):
        return "N/A"
    if row["Close"] > row["BB_UPPER"]:
        return "突破上軌"
    if row["Close"] < row["BB_LOWER"]:
        return "跌破下軌"
    return "位於中軌上方" if row["Close"] > row["BB_MID"] else "位於中軌下方"


def get_volatility_status(df: pd.DataFrame) -> str:
    recent = df["BB_WIDTH"].dropna().tail(20)
    if len(recent) < 10:
        return "N/A"
    cur, avg = recent.iloc[-1], recent.mean()
    if cur > avg * 1.15:
        return "波動擴張"
    if cur < avg * 0.85:
        return "波動收斂"
    return "波動正常"


# ---------------------------------------------------------------- 圖表
def _layout(fig, title, ylabel, height=420):
    fig.update_layout(
        title=title, xaxis_title="日期", yaxis_title=ylabel, height=height,
        hovermode="x unified", margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def plot_price(df, t):
    f = go.Figure()
    f.add_trace(go.Scatter(x=df.index, y=df.BB_UPPER, name="保力加上軌", line=dict(color="red", dash="dash", width=1)))
    f.add_trace(go.Scatter(x=df.index, y=df.BB_LOWER, name="保力加下軌", line=dict(color="green", dash="dash", width=1),
                           fill="tonexty", fillcolor="rgba(128,128,128,0.12)"))
    f.add_trace(go.Scatter(x=df.index, y=df.BB_MID, name="保力加中軌", line=dict(color="purple", dash="dash", width=1)))
    f.add_trace(go.Scatter(x=df.index, y=df.MA20, name="MA20", line=dict(color="#1f77b4", width=1.5)))
    f.add_trace(go.Scatter(x=df.index, y=df.MA50, name="MA50", line=dict(color="#ff7f0e", width=1.5)))
    f.add_trace(go.Scatter(x=df.index, y=df.MA200, name="MA200", line=dict(color="#2ca02c", width=1.5)))
    f.add_trace(go.Scatter(x=df.index, y=df.Close, name="收盤價", line=dict(color="black", width=2)))
    return _layout(f, f"{t} 股價 + 移動平均線 + 保力加通道", "價格", 520)


def plot_rsi(df, t):
    f = go.Figure(go.Scatter(x=df.index, y=df.RSI14, name="RSI 14", line=dict(color="purple", width=2)))
    f.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="超買 70")
    f.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="超賣 30")
    f.update_yaxes(range=[0, 100])
    return _layout(f, f"{t} RSI 14 相對強弱指標", "RSI", 320)


def plot_macd(df, t):
    f = go.Figure()
    f.add_trace(go.Bar(x=df.index, y=df.MACD_hist, name="柱狀圖", opacity=0.4))
    f.add_trace(go.Scatter(x=df.index, y=df.MACD, name="MACD", line=dict(color="blue", width=2)))
    f.add_trace(go.Scatter(x=df.index, y=df.MACD_signal, name="訊號線", line=dict(color="orange", width=2)))
    return _layout(f, f"{t} MACD 指標", "數值", 340)


def plot_volume(df, t):
    f = go.Figure()
    f.add_trace(go.Bar(x=df.index, y=df.Volume / 1e6, name="成交量 (百萬股)", opacity=0.7))
    f.add_trace(go.Scatter(x=df.index, y=df.Vol20 / 1e6, name="20 日平均成交量", line=dict(color="black", width=1.5)))
    return _layout(f, f"{t} 成交量", "百萬股", 320)


def plot_bb_width(df, t):
    f = go.Figure(go.Scatter(x=df.index, y=df.BB_WIDTH, name="保力加通道寬度", line=dict(color="brown", width=2)))
    return _layout(f, f"{t} 保力加通道寬度", "寬度", 300)


# ---------------------------------------------------------------- 摘要
def show_summary(df, symbol):
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    chg = latest.Close - prev.Close
    chg_pct = chg / prev.Close * 100 if prev.Close else 0
    avg_vol = df.Volume.tail(20).mean()

    trend = "偏多" if pd.notna(latest.MA50) and latest.Close > latest.MA50 else "偏弱"
    rsi_state = "過熱" if latest.RSI14 > 70 else "超賣" if latest.RSI14 < 30 else "中性"
    macd_state = "偏強區" if latest.MACD > latest.MACD_signal else "偏弱區"
    vol_state = "高於 20 日平均成交量" if latest.Volume > avg_vol else "正常或低於平均成交量"
    f = lambda v, d=2: f"{v:.{d}f}" if pd.notna(v) else "-"

    st.subheader(f"股票分析摘要：{normalize_ticker(symbol)}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("收盤價", f(latest.Close), f"{chg:+.2f} ({chg_pct:+.2f}%)")
    c2.metric("RSI14", f(latest.RSI14), rsi_state, delta_color="off")
    c3.metric("系統訊號", get_signal(latest))
    c4.metric("趨勢判斷", trend)

    st.markdown(
        f"- 日期：**{df.index[-1].date()}**\n"
        f"- MA20 / MA50 / MA200：**{f(latest.MA20)} / {f(latest.MA50)} / {f(latest.MA200)}**\n"
        f"- MACD / 訊號線：**{f(latest.MACD, 3)} / {f(latest.MACD_signal, 3)}**（{macd_state}）\n"
        f"- 保力加通道 中軌 / 上軌 / 下軌：**{f(latest.BB_MID)} / {f(latest.BB_UPPER)} / {f(latest.BB_LOWER)}**\n"
        f"- 保力加狀態：**{get_bb_status(latest)}**；波動：**{get_volatility_status(df)}**\n"
        f"- 成交量狀態：**{vol_state}**；20 日平均成交量約 **{avg_vol / 1e6:.1f}M**"
    )
    st.caption("免責聲明：以上內容只是一個簡單技術分析工具的結果，僅供參考，並不構成任何投資建議。")


# ---------------------------------------------------------------- 介面
ENGLISH_URL = "https://hkstock-e.streamlit.app/"

title_col, link_col = st.columns([5, 1], vertical_alignment="center")
title_col.title("📈 股票技術分析工具")
link_col.link_button("English Version", ENGLISH_URL, use_container_width=True)
st.caption("輸入例子：AAPL、AAPL.US、MSFT、0700.HK、700.HK、0005.HK（資料來源：Yahoo Finance）")

if "ticker" not in st.session_state:
    st.session_state.ticker = "AAPL"


def set_ticker(sym):
    st.session_state.ticker = sym


col1, col2, col3 = st.columns([2, 1.5, 1.5])
col1.text_input("Ticker", key="ticker", placeholder="例如：AAPL, 0700.HK, 700.HK")
period_label = col2.selectbox("區間", list(PERIODS), index=2)
tail_n = col3.slider("表格筆數", 3, 20, 5)

st.write("快捷股票：")
for row_start in range(0, len(PRESETS), 10):
    cols = st.columns(10)
    for col, sym in zip(cols, PRESETS[row_start:row_start + 10]):
        col.button(sym, key=f"p_{sym}", on_click=set_ticker, args=(sym,), use_container_width=True)

symbol = st.session_state.ticker
st.markdown(f"### 正在分析：`{symbol}`　（yfinance ticker：`{normalize_ticker(symbol)}`）")

try:
    data = add_indicators(download_data(symbol, PERIODS[period_label]))
    yf_sym = normalize_ticker(symbol)

    show_summary(data, symbol)
    for fn in (plot_price, plot_rsi, plot_macd, plot_volume, plot_bb_width):
        st.plotly_chart(fn(data, yf_sym))

    st.subheader(f"最近 {tail_n} 筆資料")
    cols = ["Open", "High", "Low", "Close", "Volume", "MA20", "MA50", "MA200", "BB_MID", "BB_UPPER",
            "BB_LOWER", "BB_WIDTH", "BB_PERCENT", "RSI14", "MACD", "MACD_signal", "MACD_hist"]
    st.dataframe(data[cols].tail(tail_n).style.format(
        {c: "{:.3f}" if c.startswith("MACD") else "{:,.0f}" if c == "Volume" else "{:.2f}" for c in cols}),
        width="stretch")
except Exception as e:
    st.error(f"執行失敗：{type(e).__name__}: {e}")
    st.markdown(
        "**排查建議：**\n"
        "1. 港股請用 Yahoo 格式，例如 `0005.HK`、`0700.HK`（輸入 `700.HK` 會自動補零）。\n"
        "2. `AAPL.US` 會自動轉成 `AAPL`。\n"
        "3. 若 Yahoo Finance 沒有該代號資料，請改用其他 Yahoo 格式的代號。"
    )
