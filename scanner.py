import yfinance as yf
import pandas as pd
import requests
import os

print("📊 SIMPLE MA50W ABOVE SCANNER")

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

print("TOTAL STOCKS:", len(WATCHLIST))

# ======================
# RESULT
# ======================

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

        # daily close (latest)
        price = df["Close"].iloc[-1]

        # weekly MA50
        weekly = df.resample("W").last()
        weekly["MA50W"] = weekly["Close"].rolling(50).mean()

        weekly = weekly.dropna()

        if weekly.empty:
            continue

        ma50w = weekly["MA50W"].iloc[-1]

        # ======================
        # ONLY CONDITION
        # ======================

        if price > ma50w:

            results.append((ticker, price, ma50w))

    except:
        continue

# ======================
# SORT (distance above MA50W)
# ======================

results = sorted(results, key=lambda x: (x[1] - x[2]), reverse=True)

# ======================
# OUTPUT
# ======================

msg = "📊 MA50 WEEKLY SIMPLE ABOVE SCANNER\n\n"

if results:

    for t, p, m in results[:50]:

        msg += f"{t} | Close {p:.2f} | MA50W {m:.2f}\n"

else:

    msg += "❌ NO STOCKS FOUND"

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
