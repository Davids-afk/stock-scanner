import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

print("START SCANNER")

# ======================
# TEST SYMBOLS (יציבים)
# ======================

SYMBOLS = [
"AAPL","MSFT","NVDA","AMZN","GOOGL",
"META","TSLA","AMD","AVGO","NFLX"
]

print("TOTAL SYMBOLS:", len(SYMBOLS))

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
# SCORE FUNCTION
# ======================

def score_stock(df):

    df = df.copy()

    df["EMA8"] = df["Close"].ewm(span=8).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    df["RSI"] = rsi(df["Close"])

    # חשוב מאוד — ניקוי NaN
    df = df.dropna()

    if len(df) < 60:
        return None

    last = df.iloc[-1]

    score = 0

    # תנאי מגמה
    if last["Close"] > last["EMA21"]:
        score += 30

    if last["EMA8"] > last["EMA21"]:
        score += 30

    # RSI רחב
    if 30 <= last["RSI"] <= 75:
        score += 20

    # מעל MA50
    if last["Close"] > last["MA50"]:
        score += 20

    return score

# ======================
# CLASSIFY
# ======================

def classify(score):

    if score is None:
        return None

    if score >= 70:
        return "A"

    elif score >= 50:
        return "B"

    elif score >= 40:
        return "WATCH"

    return None

# ======================
# MAIN
# ======================

A = []
B = []
WATCH = []

for ticker in SYMBOLS:

    try:

        print("Scanning:", ticker)

        df = yf.download(
            ticker,
            period="1y",
            interval="1d",
            progress=False
        )

        if df.empty:
            continue

        score = score_stock(df)

        level = classify(score)

        if level is None:
            continue

        price = float(
            df["Close"].iloc[-1]
        )

        print(ticker, "score:", score)

        if level == "A":
            A.append((ticker, score, price))

        elif level == "B":
            B.append((ticker, score, price))

        elif level == "WATCH":
            WATCH.append((ticker, score, price))

    except Exception as e:

        print("ERROR:", ticker, e)

        continue

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

msg = "📊 VERIFIED SCANNER\n\n"

msg += "🟣 A SETUPS\n"
msg += "\n".join(
    [f"{t} | {s} | {p:.2f}" for t,s,p in A]
) or "None"

msg += "\n\n🟡 B SETUPS\n"
msg += "\n".join(
    [f"{t} | {s} | {p:.2f}" for t,s,p in B]
) or "None"

msg += "\n\n🟢 WATCH\n"
msg += "\n".join(
    [f"{t} | {s} | {p:.2f}" for t,s,p in WATCH]
) or "None"

print(msg)

if TOKEN and CHAT_ID:

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": msg
        }
    )

print("DONE")
