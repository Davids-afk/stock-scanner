import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

print("START SCANNER")

# ======================
# SYMBOLS
# ======================

SYMBOLS = [
"AAPL","MSFT","NVDA","AMZN","GOOGL",
"META","TSLA","AMD","AVGO","NFLX",
"ADBE","INTC","QCOM","CRM","ORCL",
"MU","SMCI","PANW","NOW","LRCX",
"KLAC","ASML","CDNS","SNPS",
"COST","HD","LOW","WMT","TGT",
"BA","CAT","GE","RTX",
"JPM","GS","MS"
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
# SCORE
# ======================

def score_stock(df):

    df["EMA8"] = df["Close"].ewm(span=8).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    df["RSI"] = rsi(df["Close"])
    df["VOL_AVG"] = df["Volume"].rolling(20).mean()

    last = df.iloc[-1]

    score = 0

    # Trend
    if last["Close"] > last["EMA21"]:
        score += 25

    if last["EMA8"] > last["EMA21"]:
        score += 25

    # RSI wider
    if 35 <= last["RSI"] <= 75:
        score += 15

    # Distance
    dist = abs(
        last["Close"] - last["EMA21"]
    ) / last["EMA21"]

    if dist < 0.12:
        score += 20

    # Volume softer
    if last["Volume"] > last["VOL_AVG"] * 0.8:
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

        if len(df) < 60:
            continue

        score = score_stock(df)

        level = classify(score)

        price = float(
            df["Close"].iloc[-1]
        )

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

msg = "📊 WORKING SWING SCANNER\n\n"

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
