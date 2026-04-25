import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import traceback

print("START SCANNER")

# ======================
# SAFE SYMBOL LOAD
# ======================

def load_sp500():

    try:

        table = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]

        symbols = table["Symbol"].tolist()

        symbols = [s.replace(".", "-") for s in symbols]

        print("Loaded SP500:", len(symbols))

        return symbols

    except Exception as e:

        print("SP500 LOAD FAILED")

        return [
            "AAPL","MSFT","NVDA","AMZN",
            "GOOGL","META","TSLA",
            "AMD","NFLX","ADBE"
        ]


def load_nasdaq100():

    try:

        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100"
        )

        for t in tables:

            if "Ticker" in t.columns:

                symbols = t["Ticker"].tolist()

                symbols = [s.replace(".", "-") for s in symbols]

                print("Loaded NASDAQ100:", len(symbols))

                return symbols

    except Exception as e:

        print("NASDAQ LOAD FAILED")

        return ["AMD","NVDA","AVGO"]


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
# SCORE FUNCTION
# ======================

def score_stock(df):

    try:

        df["EMA8"] = df["Close"].ewm(span=8).mean()

        df["EMA21"] = df["Close"].ewm(span=21).mean()

        df["MA50"] = df["Close"].rolling(50).mean()

        df["RSI"] = rsi(df["Close"])

        df["VOL_AVG"] = df["Volume"].rolling(20).mean()

        last = df.iloc[-1]

        score = 0

        if last["Close"] > last["EMA21"]:
            score += 20

        if last["EMA8"] > last["EMA21"]:
            score += 20

        if 40 <= last["RSI"] <= 70:
            score += 15

        dist = abs(
            last["Close"] - last["EMA21"]
        ) / last["EMA21"]

        if dist < 0.08:
            score += 20

        if last["Volume"] > last["VOL_AVG"]:
            score += 10

        if last["Close"] > last["MA50"]:
            score += 15

        return score

    except:

        return 0

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
# MAIN LOOP (SAFE)
# ======================

A = []
B = []
WATCH = []

for ticker in WATCHLIST[:200]:

    try:

        print("Scanning:", ticker)

        df = yf.download(
            ticker,
            period="1y",
            interval="1d",
            progress=False
        )

        if df is None or df.empty:
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

    except Exception as e:

        print("ERROR:", ticker)

        print(traceback.format_exc())

        continue

# ======================
# TELEGRAM SAFE
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

print(msg)

if TOKEN and CHAT_ID:

    try:

        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg
            }
        )

    except Exception as e:

        print("Telegram failed")

print("DONE")
