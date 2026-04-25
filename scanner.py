import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

print("📊 ROBUST MA50 WEEKLY ABOVE SCANNER (FIXED)")

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
            period="5y",   # חשוב! יותר דאטה
            interval="1d",
            progress=False
        )

        if df.empty or len(df) < 200:
            continue

        df = df.dropna()

        # ======================
        # DAILY CLOSE (REAL PRICE)
        # ======================
        price = df["Close"].iloc[-1]

        # ======================
        # WEEKLY SERIES (FIX)
        # ======================
        weekly = df["Close"].resample("W").last()

        # חשוב: בלי dropna לפני MA
        ma50w = weekly.rolling(50, min_periods=20).mean().iloc[-1]

        if pd.isna(ma50w):
            continue

        # ======================
        # CONDITION
        # ======================

        if price > ma50w:

            results.append((ticker, price, ma50w))

    except:
        continue

# ======================
# SORT
# ======================

results = sorted(results, key=lambda x: (x[1] - x[2]), reverse=True)

# ======================
# OUTPUT
# ======================

msg = "📊 FIXED MA50W ABOVE SCANNER\n\n"

if results:

    for t, p, m in results[:50]:

        msg += f"{t} | Close {p:.2f} | MA50W {m:.2f}\n"

else:

    msg += "❌ STILL EMPTY (DATA ISSUE OR MARKET STATE)"

print(msg)

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if TOKEN and CHAT_ID:

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg}
    )

print("DONE")
