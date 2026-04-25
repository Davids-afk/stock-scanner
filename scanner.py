import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

# ======================
# SYMBOLS
# ======================

def load_sp500():
    table = pd.read_html(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    )[0]

    return table["Symbol"].str.replace(".", "-").tolist()


def load_nasdaq100():
    tables = pd.read_html(
        "https://en.wikipedia.org/wiki/Nasdaq-100"
    )

    for t in tables:
        if "Ticker" in t.columns:
            return t["Ticker"].str.replace(".", "-").tolist()

    return []

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
# SCORE ENGINE
# ======================

def score_stock(df):

    df = df.copy()

    df["EMA8"] = df["Close"].ewm(span=8).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    df["RSI"] = rsi(df["Close"])
    df["VOL_AVG"] = df["Volume"].rolling(20).mean()

    last = df.iloc[-1]

    score = 0

    # מעל EMA21
    if last["Close"] > last["EMA21"]:
        score += 20

    # EMA trend
    if last["EMA8"] > last["EMA21"]:
        score += 20

    # RSI
    if 40 <= last["RSI"] <= 70:
        score += 15

    # קרוב ל EMA21
    dist = abs(last["Close"] - last["EMA21"]) / last["EMA21"]
    if dist < 0.08:
        score += 20

    # Volume
    if last["Volume"] > last["VOL_AVG"]:
        score += 10

    # מעל MA50
    if last["Close"] > last["MA50"]:
        score += 15

    return score

# ======================
# CLASSIFY
# ======================

def classify(score):

    if score >= 75:
        return "A"

    elif score >= 60:
        return "B"

    elif score >= 50:
        return "WATCH"

    return None

# ======================
# MAIN
# ======================

A = []
B = []
WATCH = []

for ticker in WATCHLIST[:300]:

    try:

        df = yf.download(
            ticker,
            period="1y",
            interval="1d",
            progress=False
        )

        if df.empty:
            continue

        df = df.dropna()

        if len(df) < 60:
            continue

        score = score_stock(df)

        level = classify(score)

        price = float(df["Close"].iloc[-1])

        if level == "A":
            A.append((ticker, score, price))

        elif level == "B":
            B.append((ticker, score, price))

        elif level == "WATCH":
            WATCH.append((ticker, score, price))

    except:
        continue

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

msg = "📊 REAL SWING SCANNER\n\n"

msg += "🟣 A SETUPS\n"
msg += "\n".join(
    [f"{t} | {s} | {p:.2f}" for t,s,p in A[:10]]
) or "None"

msg += "\n\n🟡 B SETUPS\n"
msg += "\n".join(
    [f"{t} | {s} | {p:.2f}" for t,s,p in B[:10]]
) or "None"

msg += "\n\n🟢 WATCH\n"
msg += "\n".join(
    [f"{t} | {s} | {p:.2f}" for t,s,p in WATCH[:10]]
) or "None"

if TOKEN and CHAT_ID:

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": msg
        }
    )

print(msg)
