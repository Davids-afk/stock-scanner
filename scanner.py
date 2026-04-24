import yfinance as yf
import numpy as np
import requests
import os
import pandas as pd
import matplotlib.pyplot as plt

# ======================
# LOAD UNIVERSE
# ======================

def load_sp500():
    try:
        table = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]
        return [s.replace(".", "-") for s in table["Symbol"].tolist()]
    except:
        return ["AAPL","MSFT","NVDA","AMZN","GOOGL"]

def load_nasdaq100():
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
        for t in tables:
            if "Ticker" in t.columns:
                return [s.replace(".", "-") for s in t["Ticker"].tolist()]
    except:
        return ["AMD","ADBE","NFLX"]

WATCHLIST = list(set(load_sp500() + load_nasdaq100()))
print("TOTAL:", len(WATCHLIST))

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
# WEEKLY MA50 (5%)
# ======================

def weekly_ma50(df):
    weekly = df.resample("W").last()
    weekly["MA50W"] = weekly["Close"].rolling(50).mean()

    last = weekly.iloc[-1]

    if np.isnan(last["MA50W"]):
        return False, 999

    price = last["Close"]
    ma50w = last["MA50W"]

    dist = abs(price - ma50w) / ma50w * 100

    return price > ma50w, dist

# ======================
# ANALYSIS
# ======================

def analyze(df):

    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA20"] = df["Close"].rolling(20).mean()

    df["EMA3"] = df["Close"].ewm(span=3).mean()
    df["EMA8"] = df["Close"].ewm(span=8).mean()

    df["RSI"] = rsi(df["Close"])
    df["VOL_AVG"] = df["Volume"].rolling(20).mean()

    last = df.iloc[-1]

    if np.isnan(last["MA50"]) or np.isnan(last["MA20"]):
        return None

    # ======================
    # CORE CONDITIONS
    # ======================

    trend_up = last["Close"] > last["MA50"]

    # breakout early
    high20 = df["High"].rolling(20).max().iloc[-2]
    breakout = last["Close"] > high20 * 0.97

    # volume
    vol_ok = last["Volume"] > last["VOL_AVG"]

    # RSI
    rsi_ok = 40 <= last["RSI"] <= 75

    # weekly support (5%)
    _, dist = weekly_ma50(df)
    near_weekly = dist < 5

    # EMA trend
    ema_trend = last["EMA3"] > last["EMA8"]

    ema_slope = (
        df["EMA3"].iloc[-1] > df["EMA3"].iloc[-2]
        and df["EMA8"].iloc[-1] > df["EMA8"].iloc[-2]
    )

    ema_ok = ema_trend and ema_slope

    # ======================
    # SCORE
    # ======================

    score = 0
    score += 25 if trend_up else 0
    score += 20 if breakout else 0
    score += 15 if vol_ok else 0
    score += 15 if rsi_ok else 0
    score += 15 if near_weekly else 0
    score += 10 if ema_ok else 0

    # ======================
    # SIGNALS
    # ======================

    BUY = (
        trend_up
        and breakout
        and vol_ok
        and near_weekly
        and ema_ok
    )

    WATCH = (
        trend_up
        and ema_ok
        and score >= 50
    )

    return score, BUY, WATCH, high20

# ======================
# CHART (CANDLE + MA + EMA)
# ======================

def create_chart(df, ticker, high20):

    df = df.tail(120)

    df["MA50"] = df["Close"].rolling(50).mean()
    df["EMA3"] = df["Close"].ewm(span=3).mean()
    df["EMA8"] = df["Close"].ewm(span=8).mean()

    plt.figure(figsize=(10,5))

    plt.plot(df["Close"], label="Price")
    plt.plot(df["MA50"], label="MA50")
    plt.plot(df["EMA3"], label="EMA3")
    plt.plot(df["EMA8"], label="EMA8")

    plt.axhline(high20, linestyle="--", color="green", label="Breakout")

    plt.title(ticker)
    plt.legend()

    file = f"{ticker}.png"
    plt.savefig(file)
    plt.close()

    return file

# ======================
# SCAN
# ======================

results = []
charts = []

for t in WATCHLIST[:150]:

    try:
        df = yf.download(t, period="1y", interval="1d", progress=False)

        if df.empty:
            continue

        res = analyze(df)

        if res is None:
            continue

        score, buy, watch, high20 = res

        results.append((t, score, buy, watch))

        if buy or watch:
            charts.append((t, create_chart(df, t, high20)))

        print(t, "score:", score, "buy:", buy, "watch:", watch)

    except:
        continue

# ======================
# SORT
# ======================

results.sort(key=lambda x: x[1], reverse=True)

top = results[:15]
buys = [r for r in results if r[2]]
watch = [r for r in results if r[3]]

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

msg = "📊 STABLE MOMENTUM SCANNER\n\n"

msg += "🔥 BUY:\n"
msg += "None today\n" if not buys else ""
for t, s, _, _ in buys[:10]:
    msg += f"{t} — {s}\n"

msg += "\n👀 WATCH:\n"
for t, s, _, _ in watch[:10]:
    msg += f"{t} — {s}\n"

msg += "\n📈 TOP:\n"
for t, s, _, _ in top:
    msg += f"{t} — {s}\n"

requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    data={"chat_id": CHAT_ID, "text": msg}
)

# ======================
# SEND CHARTS
# ======================

for t, img in charts[:10]:
    try:
        with open(img, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": CHAT_ID},
                files={"photo": f}
            )
    except:
        pass

print(msg)
