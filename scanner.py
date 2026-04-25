import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import traceback

# ======================
# DEBUG MODE (IMPORTANT)
# ======================

def log_error(ticker, e):
    print(f"\n❌ ERROR IN: {ticker}")
    print(traceback.format_exc())

# ======================
# SYMBOLS
# ======================

def load_sp500():
    try:
        return pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]["Symbol"].str.replace(".", "-").tolist()
    except:
        return ["AAPL","MSFT","NVDA","AMZN","GOOGL"]

def load_nasdaq100():
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
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
# SAFE WEEKLY CHECK
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
# SCORE
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

    try:
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

    except:
        return 0

    return s

# ======================
# CLASSIFY
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
# MAIN SAFE LOOP
# ======================

A, B, W = [], [], []

for ticker in WATCHLIST[:250]:

    try:

        df = yf.download(
            ticker,
            period="2y",
            interval="1d",
            progress=False
        )

        if df is None or df.empty:
            continue

        df = df.dropna()

        if len(df) < 100:
            continue

        s = score(df)
        lvl = classify(s)

        price = float(df["Close"].iloc[-1])

        if lvl == "A":
            A.append((ticker, s, price))
        elif lvl == "B":
            B.append((ticker, s, price))
        elif lvl == "WATCH":
            W.append((ticker, s, price))

    except Exception as e:
        log_error(ticker, e)
        continue

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

msg = "📊 DEBUG SWING SCANNER\n\n"

msg += "🟣 A\n" + ("\n".join([f"{t} | {s}" for t,s,p in A[:10]]) or "None")

msg += "\n\n🟡 B\n" + ("\n".join([f"{t} | {s}" for t,s,p in B[:10]]) or "None")

msg += "\n\n🟢 WATCH\n" + ("\n".join([f"{t} | {s}" for t,s,p in W[:10]]) or "None")

if TOKEN and CHAT_ID:
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg}
    )

print(msg)
