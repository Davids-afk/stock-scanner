import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

print("📊 REALISTIC MA50 WEEKLY ZONE SCANNER")

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

A_zone = []
B_zone = []
C_zone = []

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

        weekly = df.resample("W").last()
        weekly["MA50W"] = weekly["Close"].rolling(50).mean()
        weekly = weekly.dropna()

        if weekly.empty:
            continue

        price = df["Close"].iloc[-1]
        ma50w = weekly["MA50W"].iloc[-1]

        ratio = price / ma50w

        # ======================
        # ZONES
        # ======================

        if ratio >= 1.0:
            A_zone.append((ticker, price, ma50w, ratio))

        elif 0.85 <= ratio < 1.0:
            B_zone.append((ticker, price, ma50w, ratio))

        elif 0.75 <= ratio < 0.85:
            C_zone.append((ticker, price, ma50w, ratio))

    except:
        continue

# ======================
# SORT
# ======================

A_zone = sorted(A_zone, key=lambda x: x[3], reverse=True)
B_zone = sorted(B_zone, key=lambda x: x[3])
C_zone = sorted(C_zone, key=lambda x: x[3])

# ======================
# OUTPUT
# ======================

msg = "📊 MA50 WEEKLY ZONE SCANNER\n\n"

msg += "🟢 A ZONE (trend strong)\n"
msg += "\n".join([f"{t} | {p:.2f}" for t,p,_,_ in A_zone[:20]]) or "None"

msg += "\n\n🟡 B ZONE (pullback)\n"
msg += "\n".join([f"{t} | {p:.2f}" for t,p,_,_ in B_zone[:20]]) or "None"

msg += "\n\n🔵 C ZONE (early setup)\n"
msg += "\n".join([f"{t} | {p:.2f}" for t,p,_,_ in C_zone[:20]]) or "None"

print(msg)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if TOKEN and CHAT_ID:

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg}
    )

print("DONE")
