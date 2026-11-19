# Stock Technical Analysis Tool | 股票技術分析工具

[English](#english) | [繁體中文](#繁體中文)

---

## English

Enter a stock ticker to instantly view technical indicator charts and a simple signal. Supports US and Hong Kong stocks.

🔗 **Live apps**
- 繁體中文版: https://hkstock.streamlit.app/
- English version: https://hkstock-e.streamlit.app/

### Features
- Price with MA20 / MA50 / MA200 and Bollinger Bands
- RSI14, MACD, volume and Bollinger Band width charts
- Simple signal: Buy watch / Sell watch / Hold
- 20 quick-pick tickers; periods from 3 months to 5 years

### How to use
1. Open the website.
2. Enter a ticker such as `AAPL`, `0700.HK` or `700.HK`, or click a quick-pick button.
3. Choose a period and review the charts and summary.

Ticker formats: `AAPL.US` is converted to `AAPL`; `700.HK` is converted to `0700.HK`.

### Files
| File | Description |
|---|---|
| `app.py` | Traditional Chinese version |
| `app_en.py` | English version |
| `requirements.txt` | Python dependencies |

### Built with
Python, Streamlit, yfinance, Plotly. Data source: Yahoo Finance.

### Disclaimer
This is a simple technical analysis tool, for reference only. It is not investment advice.

---

## 繁體中文

輸入股票代號，自動顯示技術指標圖表和簡單訊號，支援美股及港股。

🔗 **網站**
- 繁體中文版：https://hkstock.streamlit.app/
- English 版：https://astock.streamlit.app/

### 功能
- 股價 + MA20 / MA50 / MA200 + 保力加通道
- RSI14、MACD、成交量、保力加通道寬度
- 系統訊號：買入觀察 / 賣出觀察 / 持有觀望
- 20 個快捷股票按鈕，區間可選 3 個月至 5 年

### 使用方法
1. 開啟網站。
2. 輸入股票代號，例如 `AAPL`、`0700.HK`、`700.HK`，或按快捷按鈕。
3. 揀選區間，查看圖表和摘要。

代號格式：輸入 `AAPL.US` 會自動轉成 `AAPL`；輸入 `700.HK` 會自動轉成 `0700.HK`。

### 檔案
| 檔案 | 說明 |
|---|---|
| `app.py` | 繁體中文版 |
| `app_en.py` | 英文版 |
| `requirements.txt` | Python 套件清單 |

### 技術
Python、Streamlit、yfinance、Plotly。資料來源：Yahoo Finance。

### 免責聲明
本工具只是簡單技術分析，僅供參考，不構成任何投資建議。
