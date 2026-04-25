import yfinance as yf
import pandas as pd
import requests
import os

print("START TEST")

# בדיקה עם מניות קבועות
TEST_SYMBOLS = ["AAPL", "MSFT", "NVDA"]

results = []

for ticker in TEST_SYMBOLS:

    print("Downloading:", ticker)

    try:

        df = yf.download(
            ticker,
            period="3mo",
            interval="1d",
            progress=False
        )

        print(ticker, "rows:", len(df))

        if df.empty:
            print("EMPTY DATA:", ticker)
            continue

        last_price = df["Close"].iloc[-1]

        results.append(
            (ticker, float(last_price))
        )

    except Exception as e:

        print("ERROR:", ticker, e)


# ======================
# TELEGRAM
# ======================

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

msg = "📊 DATA TEST\n\n"

if results:

    for t, p in results:
        msg += f"{t} price: {p:.2f}\n"

else:

    msg += "❌ NO DATA DOWNLOADED"

print(msg)

if TOKEN and CHAT_ID:

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": msg
        }
    )
