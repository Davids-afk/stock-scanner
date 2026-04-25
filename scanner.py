import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import matplotlib.pyplot as plt

# ======================
# SYMBOLS
# ======================

def load_sp500():
    return pd.read_html(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    )[0]["Symbol"].str.replace(".", "-").tolist()

def load_nasdaq100():
    tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
    for t in tables:
        if "Ticker" in t.columns:
            return t["Ticker"].str.replace(".", "-").tolist()
    return []

WATCHLIST = list(set(load_sp500() + load_nasdaq100()))

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
# WEEKLY TREND (soft)
# ======================

def weekly_trend(df):
    try:
        w = df.resample("W").last()
        ma = w["Close"].rolling(50).mean()
        if len(ma.dropna()) < 10:
            return False
        return w["Close"].iloc[-1] > ma.iloc[-1]
    except:
        return False

# ======================
# SCORE (SOFTENED)
# ======================

def score(df):

    df = df.copy()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["EMA8"] = df["Close"].ewm(span=8).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    df["RSI"] = rsi(df["Close"])
    df["VOL_AVG"] = df["Volume"].rolling(20).mean()

    last = df.iloc[-1]

    s = 0

    if weekly_trend(df):
        s += 20

    if last["Close"] > last["MA20"]:
        s += 15

    if last["EMA8"] > last["EMA21"]:
        s += 20

    if 35 <= last["RSI"] <= 75:
        s += 15

    if last["Volume"] > last["VOL_AVG"]:
        s += 10

    dist = abs(last["Close"] - last["MA20"]) / last["MA20"]
    if dist < 0.08:
        s += 20

    return s

# ======================
# CLASSIFICATION (FIXED)
# ======================

def classify(s):
    if s >= 75:
        return "A"
    elif s >= 55:
        return "B"
    elif s >= 45:
        return "WATCH"
    return None

# ======================
# MAIN
# ======================

A, B, W = [], [], []

for t in WATCHLIST[:300]:

    try:
        df = yf.download(t, period="2y", interval="1d", progress=False)
        if df.empty:
            continue

        sc = score(df)
        lvl = classify(sc)

        price = df["Close"].iloc[-1]

        if lvl == "A":
            A.append((t, sc, price))
        elif lvl == "B":
            B.append((t, sc, price))
        elif lvl == "WATCH":
            W.append((t, sc, price))

    except:
        continue

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

msg = "📊 SWING SCANNER (FIXED)\n\n"

msg += "🟣 A SETUPS\n"
msg += "\n".join([f"{t} | {s}" for t,s,p in A[:10]]) or "None"

msg += "\n\n🟡 B SETUPS\n"
msg += "\n".join([f"{t} | {s}" for t,s,p in B[:10]]) or "None"

msg += "\n\n🟢 WATCH\n"
msg += "\n".join([f"{t} | {s}" for t,s,p in W[:10]]) or "None"

requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    data={"chat_id": CHAT_ID, "text": msg}
)

print(msg)
