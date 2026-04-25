import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

print("START FULL MARKET TEST")

# ======================
# LOAD S&P500
# ======================

def load_sp500():

    try:

        table = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]

        symbols = table["Symbol"].tolist()

        symbols = [s.replace(".", "-") for s in symbols]

        print("SP500 loaded:", len(symbols))

        return symbols

    except:

        print("SP500 load failed")

        return []


# ======================
# LOAD NASDAQ100
# ======================

def load_nasdaq100():

    try:

        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100"
        )

        for t in tables:

            if "Ticker" in t.columns:

                symbols = t["Ticker"].tolist()

                symbols = [s.replace(".", "-") for s in symbols]

                print("NASDAQ100 loaded:", len(symbols))

                return symbols

    except:

        print("NASDAQ load failed")

        return []


SP500 = load_sp500()
NASDAQ100 = load_nasdaq100()

WATCHLIST = list(set(SP500 + NASDAQ100))

print("TOTAL SYMBOLS:", len(WATCHLIST))

# ======================
# PARAMETERS
# ======================

MIN_VOLUME = 1_000_000

results = []

# ======================
# SCAN
# ======================

for ticker in WATCHLIST[:300]:

    try:

        print("Scanning:", ticker)

        df = yf.download(
            ticker,
            period="3y",
            interval="1d",
            progress=False
        )

        if df.empty:
            continue

        # Volume filter
        df["VOL_AVG"] = df["Volume"].rolling(20).mean()

        df = df.dropna()

        if df.empty:
            continue

        last_vol = df["VOL_AVG"].iloc[-1]

        if last_vol < MIN_VOLUME:
            continue

        # Weekly conversion
        weekly = df.resample("W").last()

        weekly["MA50W"] = weekly["Close"].rolling(50).mean()

        weekly = weekly.dropna()

        if weekly.empty:
            continue

        last = weekly.iloc[-1]

        price = last["Close"]
        ma50w = last["MA50W"]

        distance = (price - ma50w) / ma50w * 100

        # Distance condition
        if 0 <= distance <= 15:

            results.append(
                (ticker, price, ma50w, distance)
            )

    except Exception as e:

        print("ERROR:", ticker)

        continue

# ======================
# SORT
# ======================

results = sorted(
    results,
    key=lambda x: x[3]
)

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

msg = "📊 MA50 WEEKLY + VOLUME SCANNER\n\n"

if results:

    for t, p, m, d in results[:30]:

        msg += (
            f"{t}\n"
            f"Price {p:.2f}\n"
            f"MA50W {m:.2f}\n"
            f"Dist {d:.1f}%\n\n"
        )

else:

    msg += "❌ NO STOCKS FOUND"

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
