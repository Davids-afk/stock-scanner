import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

print("📊 ROBUST TWO LAYER SWING SCANNER")

# ======================
# UNIVERSE
# ======================

def load_universe():

    try:

        sp = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]["Symbol"].str.replace(".", "-").tolist()

        nq = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100"
        )

        nq_list = []

        for t in nq:
            if "Ticker" in t.columns:
                nq_list = t["Ticker"].str.replace(".", "-").tolist()

        return list(set(sp + nq_list))

    except:

        return ["AAPL","MSFT","NVDA","AMZN","GOOGL","AMD","AVGO"]

WATCHLIST = load_universe()

print("TOTAL:", len(WATCHLIST))

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
# SCANNER
# ======================

BASE = []
HEDGE = []

for ticker in WATCHLIST:

    try:

        df = yf.download(
            ticker,
            period="2y",
            interval="1d",
            progress=False
        )

        if df.empty or len(df) < 100:
            continue

        df = df.dropna()

        # indicators
        df["EMA8"] = df["Close"].ewm(span=8).mean()
        df["EMA21"] = df["Close"].ewm(span=21).mean()
        df["MA50"] = df["Close"].rolling(50).mean()
        df["RSI"] = rsi(df["Close"])
        df["VOL_AVG"] = df["Volume"].rolling(20).mean()

        df = df.dropna()

        if len(df) < 60:
            continue

        recent = df.tail(5)

        ma50 = df["MA50"].iloc[-1]

        if pd.isna(ma50):
            continue

        # ======================
        # 🟢 BASE (5-day logic)
        # ======================

        base_hits = 0

        for i in range(len(recent)):

            price = recent["Close"].iloc[i]

            dist = (price - ma50) / ma50 * 100

            if price > ma50 and dist <= 20:
                base_hits += 1

        if base_hits >= 2:
            BASE.append((ticker, df["Close"].iloc[-1], base_hits))

        # ======================
        # 🔵 HEDGE (trend consistency)
        # ======================

        ema_hits = 0

        for i in range(len(recent)):

            if recent["EMA8"].iloc[i] > recent["EMA21"].iloc[i]:
                ema_hits += 1

        rsi_ok = 45 <= df["RSI"].iloc[-1] <= 70

        if ema_hits >= 3 and rsi_ok:
            HEDGE.append((ticker, df["Close"].iloc[-1], ema_hits))

    except:
        continue

# ======================
# SORT
# ======================

BASE = sorted(BASE, key=lambda x: x[2], reverse=True)
HEDGE = sorted(HEDGE, key=lambda x: x[2], reverse=True)

# ======================
# OUTPUT
# ======================

msg = "📊 ROBUST TWO LAYER SCANNER\n\n"

msg += "🟢 BASE SETUPS\n"
msg += "\n".join(
    [f"{t} | {p:.2f}" for t,p,_ in BASE[:20]]
) or "None"

msg += "\n\n🔵 HEDGE SETUPS\n"
msg += "\n".join(
    [f"{t} | {p:.2f}" for t,p,_ in HEDGE[:20]]
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
