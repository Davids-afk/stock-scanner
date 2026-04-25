import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import matplotlib.pyplot as plt

# ======================
# LOAD SYMBOLS
# ======================

def load_sp500():
    table = pd.read_html(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    )[0]

    return [s.replace(".", "-") for s in table["Symbol"].tolist()]


def load_nasdaq100():
    tables = pd.read_html(
        "https://en.wikipedia.org/wiki/Nasdaq-100"
    )

    for t in tables:
        if "Ticker" in t.columns:
            return [s.replace(".", "-") for s in t["Ticker"].tolist()]

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
# WEEKLY TREND
# ======================

def weekly_trend(df):
    weekly = df.resample("W").last()
    weekly["MA50"] = weekly["Close"].rolling(50).mean()

    last = weekly.iloc[-1]

    if np.isnan(last["MA50"]):
        return False

    return last["Close"] > last["MA50"]

# ======================
# SCORING ENGINE
# ======================

def score_stock(df):

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["EMA8"] = df["Close"].ewm(span=8).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    df["RSI"] = rsi(df["Close"])
    df["VOL_AVG"] = df["Volume"].rolling(20).mean()

    last = df.iloc[-1]

    score = 0

    # Trend
    if weekly_trend(df):
        score += 25

    if last["Close"] > last["MA20"]:
        score += 10

    # Momentum
    if last["EMA8"] > last["EMA21"]:
        score += 20

    # RSI healthy
    if 40 <= last["RSI"] <= 70:
        score += 15

    # Volume
    if last["Volume"] > last["VOL_AVG"]:
        score += 10

    # Pullback proximity
    dist = abs(last["Close"] - last["MA20"]) / last["MA20"]
    if dist < 0.05:
        score += 20

    return score

# ======================
# STRATEGY LEVEL
# ======================

def classify(score):
    if score >= 80:
        return "A"
    elif score >= 60:
        return "B"
    return None

# ======================
# CHART
# ======================

def create_chart(df, ticker, entry):

    df = df.tail(120)

    df["MA20"] = df["Close"].rolling(20).mean()

    plt.figure(figsize=(9,4))

    plt.plot(df["Close"])
    plt.plot(df["MA20"])

    plt.axhline(entry)

    plt.title(ticker)

    file = f"{ticker}.png"

    plt.savefig(file)

    plt.close()

    return file

# ======================
# SCAN
# ======================

A_setups = []
B_setups = []
charts = []

for ticker in WATCHLIST[:250]:

    try:

        df = yf.download(
            ticker,
            period="2y",
            interval="1d",
            progress=False
        )

        if df.empty:
            continue

        s = score_stock(df)
        level = classify(s)

        if level is None:
            continue

        entry = df["Close"].iloc[-1]
        stop = df["MA20"].iloc[-1]
        target = entry * 1.10

        if level == "A":
            A_setups.append((ticker, s, entry, stop, target))
        else:
            B_setups.append((ticker, s, entry, stop, target))

        chart = create_chart(df, ticker, entry)
        charts.append(chart)

    except:
        continue

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

msg = "📊 SWING SCANNER (A / B SYSTEM)\n\n"

msg += "🟣 A SETUPS\n"
if not A_setups:
    msg += "None\n\n"
else:
    for t, s, e, st, tp in A_setups[:10]:
        msg += f"{t} — {s}\nEntry {e:.2f}\n\n"

msg += "🟡 B SETUPS\n"
if not B_setups:
    msg += "None\n\n"
else:
    for t, s, e, st, tp in B_setups[:10]:
        msg += f"{t} — {s}\nEntry {e:.2f}\n\n"

requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    data={"chat_id": CHAT_ID, "text": msg}
)

for c in charts[:10]:
    try:
        with open(c, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": CHAT_ID},
                files={"photo": f}
            )
    except:
        continue

print(msg)
