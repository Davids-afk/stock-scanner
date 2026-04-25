import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

# ======================
# SYMBOLS
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
        return ["AMD","ADBE","NFLX"]


WATCHLIST = list(set(load_sp500() + load_nasdaq100()))

print("TOTAL SYMBOLS:", len(WATCHLIST))

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
# MAIN SCAN (SIMPLE)
# ======================

A = []
B = []
WATCH = []

for ticker in WATCHLIST[:200]:

    try:

        df = yf.download(
            ticker,
            period="1y",
            interval="1d",
            progress=False
        )

        if df.empty:
            continue

        df["EMA8"] = df["Close"].ewm(span=8).mean()
        df["EMA21"] = df["Close"].ewm(span=21).mean()
        df["RSI"] = rsi(df["Close"])

        last = df.iloc[-1]

        score = 0

        # EMA trend
        if last["EMA8"] > last["EMA21"]:
            score += 40

        # RSI healthy
        if 40 <= last["RSI"] <= 70:
            score += 30

        # Price above EMA21
        if last["Close"] > last["EMA21"]:
            score += 30

        # Classification

        if score >= 80:
            A.append((ticker, score))

        elif score >= 60:
            B.append((ticker, score))

        elif score >= 50:
            WATCH.append((ticker, score))

    except:
        continue

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

msg = "📊 BASIC MOMENTUM SCANNER\n\n"

msg += "🟣 A SETUPS\n"
msg += "\n".join([f"{t} | {s}" for t,s in A[:10]]) or "None"

msg += "\n\n🟡 B SETUPS\n"
msg += "\n".join([f"{t} | {s}" for t,s in B[:10]]) or "None"

msg += "\n\n🟢 WATCH\n"
msg += "\n".join([f"{t} | {s}" for t,s in WATCH[:10]]) or "None"

if TOKEN and CHAT_ID:

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": msg
        }
    )

print(msg)
