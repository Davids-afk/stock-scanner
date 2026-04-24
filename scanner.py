import yfinance as yf
import numpy as np
import requests
import os
import pandas as pd
import mplfinance as mpf
from datetime import datetime
import csv
import os.path

# ======================
# MEMORY (LEARNING)
# ======================

FILE = "ml_memory.csv"

if not os.path.exists(FILE):
    with open(FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date","ticker","prob","buy","future_return"])

# ======================
# UNIVERSE
# ======================

def load_sp500():
    try:
        t = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        return [x.replace(".", "-") for x in t["Symbol"].tolist()]
    except:
        return ["AAPL","MSFT","NVDA","AMZN","GOOGL"]

def load_nasdaq100():
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
        for t in tables:
            if "Ticker" in t.columns:
                return [x.replace(".", "-") for x in t["Ticker"].tolist()]
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
# LEARNING BOOST
# ======================

def ml_edge(ticker):

    try:
        df = pd.read_csv(FILE)

        tdf = df[df["ticker"] == ticker].tail(30)

        if len(tdf) < 5:
            return 0

        win_rate = (tdf["future_return"] > 0).mean()

        return (win_rate - 0.5) * 20

    except:
        return 0

# ======================
# ANALYSIS ENGINE
# ======================

def analyze(df, ticker):

    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["RSI"] = rsi(df["Close"])

    last = df.iloc[-1]

    if np.isnan(last["MA50"]) or np.isnan(last["MA20"]):
        return None

    # ======================
    # FEATURES
    # ======================

    trend = last["Close"] > last["MA50"]

    high20 = df["High"].rolling(20).max().iloc[-2]
    breakout = last["Close"] > high20

    vol_avg = df["Volume"].rolling(20).mean().iloc[-1]
    vol_spike = last["Volume"] > vol_avg * 1.3   # פחות קשיח

    rsi_ok = 35 <= last["RSI"] <= 75

    range20 = df["High"].rolling(20).max().iloc[-1] - df["Low"].rolling(20).min().iloc[-1]
    compression = (range20 / last["Close"]) < 0.15  # פחות קשיח

    weekly = df.resample("W").last()
    ma50w = weekly["Close"].rolling(50).mean().iloc[-1]
    above_ma50w = last["Close"] > ma50w if not np.isnan(ma50w) else True

    # ======================
    # PROBABILITY MODEL
    # ======================

    prob = 0
    prob += 25 if breakout else 10
    prob += 25 if trend else 0
    prob += 15 if vol_spike else 5
    prob += 15 if compression else 5
    prob += 10 if rsi_ok else 0
    prob += 10 if above_ma50w else 0

    prob += ml_edge(ticker)

    prob = min(100, max(0, prob))

    # ======================
    # SIGNALS (FIXED BALANCED)
    # ======================

    BUY = (
        prob >= 70
        and trend
        and (breakout or vol_spike)
    )

    WATCH = (
        prob >= 50
        and trend
    )

    return prob, BUY, WATCH, high20

# ======================
# LEARNING LOG
# ======================

def log_ml(ticker, prob, buy, df):

    try:
        close_now = df["Close"].iloc[-1]
        close_future = df["Close"].iloc[-6] if len(df) > 6 else close_now

        future_return = (close_future / close_now) - 1

        with open(FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.utcnow().date(),
                ticker,
                prob,
                int(buy),
                future_return
            ])

    except:
        pass

# ======================
# CHART
# ======================

def create_chart(df, ticker, high20):

    try:
        df = df.tail(120)
        df["MA50"] = df["Close"].rolling(50).mean()

        file = f"{ticker}.png"

        mpf.plot(
            df,
            type="candle",
            style="yahoo",
            volume=True,
            title=ticker,
            addplot=[mpf.make_addplot(df["MA50"])],
            hlines=dict(
                hlines=[high20],
                colors=["green"],
                linestyle="--"
            ),
            savefig=file
        )

        return file

    except:
        return None

# ======================
# SCAN
# ======================

results = []
charts = []

for t in WATCHLIST[:120]:

    try:
        df = yf.download(t, period="2y", interval="1d", progress=False)

        if df.empty:
            continue

        res = analyze(df, t)

        if res is None:
            continue

        prob, buy, watch, high20 = res

        results.append((t, prob, buy, watch))

        log_ml(t, prob, buy, df)

        if buy or watch:
            img = create_chart(df, t, high20)
            if img:
                charts.append((t, img))

        # DEBUG חשוב
        print(t, "prob:", prob, "buy:", buy, "watch:", watch)

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

msg = "📊 FIXED ML SCANNER\n\n"

msg += "🔥 BUY:\n"
msg += "None today\n" if not buys else ""
for t, p, _, _ in buys[:10]:
    msg += f"{t} — {p}%\n"

msg += "\n👀 WATCH:\n"
for t, p, _, _ in watch[:10]:
    msg += f"{t} — {p}%\n"

msg += "\n📈 TOP:\n"
for t, p, _, _ in top:
    msg += f"{t} — {p}%\n"

requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    data={"chat_id": CHAT_ID, "text": msg}
)

# ======================
# SEND CHARTS
# ======================

for t, img in charts[:8]:
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
