import yfinance as yf
import pandas as pd
import requests
import os

print("START DEBUG MA50W")

# ======================
# LOAD SYMBOLS
# ======================

def load_sp500():

    try:

        table = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]

        symbols = table["Symbol"].tolist()

        symbols = [s.replace(".", "-") for s in symbols]

        return symbols

    except:

        return ["AAPL","MSFT","NVDA"]


def load_nasdaq100():

    try:

        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100"
        )

        for t in tables:

            if "Ticker" in t.columns:

                symbols = t["Ticker"].tolist()

                symbols = [s.replace(".", "-") for s in symbols]

                return symbols

    except:

        return ["AMD","AVGO"]

SP500 = load_sp500()
NASDAQ100 = load_nasdaq100()

WATCHLIST = list(set(SP500 + NASDAQ100))

print("TOTAL SYMBOLS:", len(WATCHLIST))

results = []

# ======================
# DEBUG LOOP
# ======================

for ticker in WATCHLIST[:50]:

    try:

        print("Downloading:", ticker)

        df = yf.download(
            ticker,
            period="3y",
            interval="1d",
            progress=False
        )

        if df.empty:
            continue

        # 🔴 קריטי מאוד
        df.index = pd.to_datetime(df.index)

        # Weekly resample
        weekly = df.resample("W").last()

        weekly["MA50W"] = (
            weekly["Close"]
            .rolling(50)
            .mean()
        )

        weekly = weekly.dropna()

        if weekly.empty:
            continue

        last = weekly.iloc[-1]

        price = float(last["Close"])
        ma50w = float(last["MA50W"])

        distance = (
            (price - ma50w) / ma50w * 100
        )

        print(
            ticker,
            "Price:", round(price,2),
            "MA50W:", round(ma50w,2),
            "Dist:", round(distance,2)
        )

        results.append(
            (ticker, price, ma50w, distance)
        )

    except Exception as e:

        print("ERROR:", ticker, e)

        continue

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

msg = "📊 DEBUG MA50W VALUES\n\n"

if results:

    for t, p, m, d in results[:20]:

        msg += (
            f"{t} | "
            f"P {p:.2f} | "
            f"MA50W {m:.2f} | "
            f"{d:.1f}%\n"
        )

else:

    msg += "❌ NO DATA"

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
