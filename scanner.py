import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

print("📊 TWO LAYER SWING SCANNER START")

# ======================
# SYMBOLS (S&P + NASDAQ)
# ======================

def load_sp500():
    try:
        table = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]
        return table["Symbol"].str.replace(".", "-").tolist()
    except:
        return ["AAPL","MSFT","NVDA","AMZN","GOOGL"]

def load_nasdaq100():
    try:
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100"
        )
        for t in tables:
            if "Ticker" in t.columns:
                return t["Ticker"].str.replace(".", "-").tolist()
    except:
        return ["AMD","AVGO","NFLX"]

WATCHLIST = list(set(load_sp500() + load_nasdaq100()))

print("TOTAL STOCKS:", len(WATCHLIST))

# ======================
# RSI
# ======================

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ======================
# DATA PROCESS
# ======================

def process(df):

    df = df.copy()

    df["EMA8"] = df["Close"].ewm(span=8).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["RSI"] = rsi(df["Close"])
    df["VOL_AVG"] = df["Volume"].rolling(20).mean()

    df = df.dropna()

    if len(df) < 60:
        return None

    last = df.iloc[-1]

    # weekly MA50
    weekly = df.resample("W").last()
    weekly["MA50W"] = weekly["Close"].rolling(50).mean()
    weekly = weekly.dropna()

    if weekly.empty:
        return None

    w = weekly.iloc[-1]

    price = last["Close"]
    ma50w = w["MA50W"]

    dist = (price - ma50w) / ma50w * 100

    return last, price, ma50w, dist, df

# ======================
# LAYERS
# ======================

BASE = []
HEDGE = []

for ticker in WATCHLIST:

    try:

        df = yf.download(
            ticker,
            period="3y",
            interval="1d",
            progress=False
        )

        if df.empty:
            continue

        out = process(df)

        if out is None:
            continue

        last, price, ma50w, dist, df = out

        volume_ok = last["Volume"] > last["VOL_AVG"]

        # ======================
        # 🟢 BASE LAYER
        # ======================

        if (
            price >= ma50w
            and dist <= 10
            and volume_ok
        ):
            BASE.append((ticker, price, dist))

        # ======================
        # 🔵 HEDGE FUND LAYER
        # ======================

        trend_up = last["EMA8"] > last["EMA21"]

        rsi_ok = 45 <= last["RSI"] <= 70

        pullback_ok = (price / df["Close"].max()) > 0.88

        if (
            trend_up
            and price >= ma50w
            and rsi_ok
            and pullback_ok
        ):
            HEDGE.append((ticker, price, dist))

    except:
        continue

# ======================
# SORT
# ======================

BASE = sorted(BASE, key=lambda x: x[2])
HEDGE = sorted(HEDGE, key=lambda x: x[2])

# ======================
# OUTPUT
# ======================

msg = "📊 TWO LAYER SWING SCANNER\n\n"

msg += "🟢 BASE (MA50 support)\n"
msg += "\n".join(
    [f"{t} | {p:.2f} | {d:.1f}%" for t,p,d in BASE[:20]]
) or "None"

msg += "\n\n🔵 HEDGE FUND SETUPS\n"
msg += "\n".join(
    [f"{t} | {p:.2f} | {d:.1f}%" for t,p,d in HEDGE[:20]]
) or "None"

print(msg)

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if TOKEN and CHAT_ID:

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": msg
        }
    )

print("DONE")
