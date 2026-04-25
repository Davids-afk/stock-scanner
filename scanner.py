import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

print("📊 FIXED TWO LAYER SCANNER")

# ======================
# UNIVERSE
# ======================

def load_universe():

    try:

        sp500 = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]["Symbol"].str.replace(".", "-").tolist()

        nasdaq = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100"
        )

        nasdaq_list = []

        for t in nasdaq:

            if "Ticker" in t.columns:

                nasdaq_list = t["Ticker"].str.replace(".", "-").tolist()

        return list(set(sp500 + nasdaq_list))

    except:

        return ["AAPL","MSFT","NVDA","AMZN","GOOGL","AMD","AVGO"]

WATCHLIST = load_universe()

print("TOTAL:", len(WATCHLIST))

# ======================
# SCORING HELP
# ======================

def rsi(series, period=14):

    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()

    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ======================
# LAYERS
# ======================

BASE = []
HEDGE = []

for ticker in WATCHLIST[:300]:

    try:

        df = yf.download(
            ticker,
            period="2y",
            interval="1d",
            progress=False
        )

        if df.empty:
            continue

        df = df.dropna()

        if len(df) < 60:
            continue

        # indicators
        df["EMA8"] = df["Close"].ewm(span=8).mean()
        df["EMA21"] = df["Close"].ewm(span=21).mean()
        df["MA50"] = df["Close"].rolling(50).mean()
        df["RSI"] = rsi(df["Close"])
        df["VOL_AVG"] = df["Volume"].rolling(20).mean()

        df = df.dropna()

        last = df.iloc[-1]

        price = last["Close"]
        ma50 = last["MA50"]

        if pd.isna(ma50):
            continue

        dist = (price - ma50) / ma50 * 100

        # ======================
        # 🟢 BASE (FIXED)
        # ======================

        volume_ok = last["Volume"] > 800_000

        if (
            price > ma50
            and dist <= 20
            and volume_ok
        ):
            BASE.append((ticker, price, dist))

        # ======================
        # 🔵 HEDGE
        # ======================

        trend = last["EMA8"] > last["EMA21"]

        rsi_ok = 45 <= last["RSI"] <= 70

        pullback = (price / df["Close"].max()) > 0.88

        if (
            trend
            and price > ma50
            and rsi_ok
            and volume_ok
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

msg = "📊 FIXED TWO LAYER SCANNER\n\n"

msg += "🟢 BASE SETUPS\n"
msg += "\n".join(
    [f"{t} | {p:.2f} | {d:.1f}%" for t,p,d in BASE[:20]]
) or "None"

msg += "\n\n🔵 HEDGE SETUPS\n"
msg += "\n".join(
    [f"{t} | {p:.2f} | {d:.1f}%" for t,p,d in HEDGE[:20]]
) or "None"

print(msg)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if TOKEN and CHAT_ID:

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg}
    )

print("DONE")
