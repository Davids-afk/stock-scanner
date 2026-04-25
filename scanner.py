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

    symbols = table["Symbol"].tolist()
    symbols = [s.replace(".", "-") for s in symbols]

    return symbols


def load_nasdaq100():

    tables = pd.read_html(
        "https://en.wikipedia.org/wiki/Nasdaq-100"
    )

    for t in tables:

        if "Ticker" in t.columns:

            symbols = t["Ticker"].tolist()
            symbols = [s.replace(".", "-") for s in symbols]

            return symbols


SP500 = load_sp500()
NASDAQ100 = load_nasdaq100()

WATCHLIST = list(set(SP500 + NASDAQ100))

print("TOTAL SYMBOLS:", len(WATCHLIST))

# ======================
# INDICATORS
# ======================

def rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()

    rs = gain / loss

    return 100 - (100 / (1 + rs))


# ======================
# STRATEGIES
# ======================

def strategy_pullback(df):

    monthly = df.resample("M").last()
    weekly = df.resample("W").last()

    monthly["MA10"] = monthly["Close"].rolling(10).mean()
    weekly["MA50"] = weekly["Close"].rolling(50).mean()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    df["RSI"] = rsi(df["Close"])

    if len(monthly) < 12:
        return None

    last_m = monthly.iloc[-1]
    last_w = weekly.iloc[-1]
    last = df.iloc[-1]

    cond = (
        last_m["Close"] > last_m["MA10"]
        and last_w["Close"] > last_w["MA50"]
        and abs(last["Close"] - last["MA20"]) / last["MA20"] < 0.03
        and 40 <= last["RSI"] <= 55
    )

    if cond:

        entry = last["Close"]
        stop = last["MA50"]
        target = entry * 1.10

        return entry, stop, target

    return None


def strategy_breakout(df):

    df["VOL_AVG"] = df["Volume"].rolling(20).mean()

    high20 = df["High"].rolling(20).max().iloc[-2]

    last = df.iloc[-1]

    cond = (
        last["Close"] > high20
        and last["Volume"] > last["VOL_AVG"]
    )

    if cond:

        entry = high20 * 1.002
        stop = high20 * 0.98
        target = entry * 1.12

        return entry, stop, target

    return None


def strategy_momentum(df):

    df["EMA8"] = df["Close"].ewm(span=8).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()

    df["RSI"] = rsi(df["Close"])

    last = df.iloc[-1]

    cond = (
        last["EMA8"] > last["EMA21"]
        and 50 <= last["RSI"] <= 70
    )

    if cond:

        entry = last["Close"]
        stop = last["EMA21"]
        target = entry * 1.10

        return entry, stop, target

    return None


# ======================
# CHART
# ======================

def create_chart(df, ticker, entry, stop, target):

    df = df.tail(120)

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    plt.figure(figsize=(9,4))

    plt.plot(df["Close"], label="Price")
    plt.plot(df["MA20"], label="MA20")
    plt.plot(df["MA50"], label="MA50")

    plt.axhline(entry, linestyle="--", label="Entry")
    plt.axhline(stop, linestyle="--", label="Stop")
    plt.axhline(target, linestyle="--", label="Target")

    plt.title(ticker)

    plt.legend()

    file_name = f"{ticker}.png"

    plt.savefig(file_name)

    plt.close()

    return file_name


# ======================
# MAIN SCAN
# ======================

pullback_list = []
breakout_list = []
momentum_list = []

charts = []

for ticker in WATCHLIST[:200]:

    try:

        df = yf.download(
            ticker,
            period="2y",
            interval="1d",
            progress=False
        )

        if df.empty:
            continue

        res1 = strategy_pullback(df)
        res2 = strategy_breakout(df)
        res3 = strategy_momentum(df)

        if res1:

            entry, stop, target = res1

            pullback_list.append(
                (ticker, entry, stop, target)
            )

            charts.append(
                create_chart(
                    df,
                    ticker,
                    entry,
                    stop,
                    target
                )
            )

        elif res2:

            entry, stop, target = res2

            breakout_list.append(
                (ticker, entry, stop, target)
            )

            charts.append(
                create_chart(
                    df,
                    ticker,
                    entry,
                    stop,
                    target
                )
            )

        elif res3:

            entry, stop, target = res3

            momentum_list.append(
                (ticker, entry, stop, target)
            )

            charts.append(
                create_chart(
                    df,
                    ticker,
                    entry,
                    stop,
                    target
                )
            )

    except:

        continue


# ======================
# TELEGRAM TEXT
# ======================

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

msg = "📊 MULTI STRATEGY SCANNER\n\n"

def format_block(title, lst):

    text = title + "\n"

    for t, e, s, tp in lst[:5]:

        text += (
            f"{t}\n"
            f"Entry: {e:.2f}\n"
            f"Stop: {s:.2f}\n"
            f"Target: {tp:.2f}\n\n"
        )

    return text


msg += format_block(
    "🥇 Pullback",
    pullback_list
)

msg += format_block(
    "🥈 Breakout",
    breakout_list
)

msg += format_block(
    "🥉 Momentum",
    momentum_list
)

requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    data={
        "chat_id": CHAT_ID,
        "text": msg
    }
)

# ======================
# SEND CHARTS
# ======================

for chart in charts[:10]:

    with open(chart, "rb") as f:

        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={"chat_id": CHAT_ID},
            files={"photo": f}
        )

print(msg)
