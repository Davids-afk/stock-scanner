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
    try:
        table = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]

        symbols = table["Symbol"].tolist()
        symbols = [s.replace(".", "-") for s in symbols]

        return symbols

    except:
        return ["AAPL","MSFT","NVDA","AMZN","GOOGL"]


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
        return ["AMD","ADBE","NFLX"]


SP500 = load_sp500()
NASDAQ100 = load_nasdaq100()

WATCHLIST = list(set(SP500 + NASDAQ100))

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
# WEEKLY MA50 FIXED
# ======================

def weekly_ma50(df):

    try:

        weekly = yf.download(
            df.name,
            period="5y",
            interval="1wk",
            progress=False
        )

        weekly["MA50W"] = (
            weekly["Close"]
            .rolling(50)
            .mean()
        )

        last = weekly.iloc[-1]

        if np.isnan(last["MA50W"]):
            return False

        return last["Close"] > last["MA50W"]

    except:

        return False


# ======================
# ANALYZE
# ======================

def analyze(df, ticker):

    try:

        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA50"] = df["Close"].rolling(50).mean()

        df["EMA8"] = df["Close"].ewm(span=8).mean()
        df["EMA21"] = df["Close"].ewm(span=21).mean()

        df["RSI"] = rsi(df["Close"])

        df["VOL_AVG"] = (
            df["Volume"]
            .rolling(20)
            .mean()
        )

        last = df.iloc[-1]

        # WEEKLY TREND

        weekly_ok = weekly_ma50(df)

        # PULLBACK

        near_ma20 = (
            abs(last["Close"] - last["MA20"])
            / last["MA20"]
            < 0.05
        )

        rsi_pullback = (
            35 <= last["RSI"] <= 60
        )

        pullback = (
            weekly_ok
            and near_ma20
            and rsi_pullback
        )

        # BREAKOUT

        high20 = (
            df["High"]
            .rolling(20)
            .max()
            .iloc[-2]
        )

        breakout = (
            last["Close"] > high20
            and last["Volume"]
            > last["VOL_AVG"]
        )

        # MOMENTUM

        momentum = (
            last["EMA8"] > last["EMA21"]
            and last["RSI"] > 50
        )

        if pullback or breakout or momentum:

            entry = last["Close"]

            stop = last["MA50"]

            target = entry * 1.10

            return entry, stop, target

        return None

    except:

        return None


# ======================
# CHART
# ======================

def create_chart(df, ticker, entry, stop, target):

    try:

        df = df.tail(120)

        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA50"] = df["Close"].rolling(50).mean()

        plt.figure(figsize=(9,4))

        plt.plot(df["Close"])
        plt.plot(df["MA20"])
        plt.plot(df["MA50"])

        plt.axhline(entry)
        plt.axhline(stop)
        plt.axhline(target)

        plt.title(ticker)

        file_name = f"{ticker}.png"

        plt.savefig(file_name)

        plt.close()

        return file_name

    except:

        return None


# ======================
# MAIN
# ======================

results = []
charts = []

for ticker in WATCHLIST[:300]:

    print("Scanning:", ticker)

    try:

        df = yf.download(
            ticker,
            period="2y",
            interval="1d",
            progress=False
        )

        if df.empty:
            continue

        df.name = ticker

        res = analyze(df, ticker)

        if res:

            entry, stop, target = res

            results.append(
                (ticker, entry, stop, target)
            )

            chart = create_chart(
                df,
                ticker,
                entry,
                stop,
                target
            )

            if chart:
                charts.append(chart)

    except:

        continue


# ======================
# TELEGRAM
# ======================

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

msg = "📊 STABLE SWING SCANNER\n\n"

if len(results) == 0:

    msg += "No signals today"

else:

    for t, e, s, tp in results[:10]:

        msg += (
            f"{t}\n"
            f"Entry: {e:.2f}\n"
            f"Stop: {s:.2f}\n"
            f"Target: {tp:.2f}\n\n"
        )


requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    data={
        "chat_id": CHAT_ID,
        "text": msg
    }
)

for chart in charts[:10]:

    try:

        with open(chart, "rb") as f:

            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": CHAT_ID},
                files={"photo": f}
            )

    except:

        continue


print(msg)
