import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

print("📊 FIXED MA50 WEEKLY BAND SCANNER")

# ======================
# UNIVERSE
# ======================

def load_universe():

    try:

        sp = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]["Symbol"].str.replace(".", "-").tolist()

        nq_tables = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100"
        )

        nq = []

        for t in nq_tables:
            if "Ticker" in t.columns:
                nq = t["Ticker"].str.replace(".", "-").tolist()

        return list(set(sp + nq))

    except:

        return ["AAPL","MSFT","NVDA","AMZN","GOOGL","AMD","AVGO"]

WATCHLIST = load_universe()

results = []

# ======================
# SCAN
# ======================

for ticker in WATCHLIST:

    try:

        df = yf.download(
            ticker,
            period="3y",
            interval="1d",
            progress=False
        )

        if df.empty or len(df) < 200:
            continue

        df.index = pd.to_datetime(df.index)

        # 🟢 DAILY PRICE (IMPORTANT FIX)
        price = df["Close"].iloc[-1]

        # 🟢 WEEKLY MA50
        weekly = df.resample("W").last()
        weekly["MA50W"] = weekly["Close"].rolling(50).mean()
        weekly = weekly.dropna()

        if weekly.empty:
            continue

        ma50w = weekly["MA50W"].iloc[-1]

        # ======================
        # BAND CONDITION
        # ======================

        lower = ma50w * 0.90
        upper = ma50w * 1.10

        if lower <= price <= upper:

            distance = (price - ma50w) / ma50w * 100

            results.append((ticker, price, ma50w, distance))

    except:
        continue

# ======================
# SORT
# ======================

results = sorted(results, key=lambda x: abs(x[3]))

# ======================
# OUTPUT
# ======================

msg = "📊 FIXED MA50 WEEKLY BAND SCANNER\n\n"

if results:

    for t, p, m, d in results[:50]:

        msg += f"{t} | P {p:.2f} | MA50W {m:.2f} | {d:.1f}%\n"

else:

    msg += "❌ NO STOCKS FOUND"

print(msg)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if TOKEN and CHAT_ID:

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg}
    )

print("DONE")
