import yfinance as yf
import numpy as np
import requests
import os
import pandas as pd
import mplfinance as mpf

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
# ANALYSIS (BASIC RULES ONLY)
# ======================

def analyze(df):

    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["RSI"] = rsi(df["Close"])
    df["VOL_AVG"] = df["Volume"].rolling(20).mean()

    last = df.iloc[-1]

    if np.isnan(last["MA50"]) or np.isnan(last["MA20"]):
        return None

    # ======================
    # CORE CONDITIONS
    # ======================

    trend_up = last["Close"] > last["MA50"]

    # bounce on MA50
    bounce = (
        last["Low"] <= last["MA50"] * 1.02 and
        last["Close"] > last["MA50"]
    )

    # RSI normal zone
    rsi_ok = 40 <= last["RSI"] <= 70

    # volume confirmation
    vol_ok = last["Volume"] > last["VOL_AVG"]

    # near breakout
    high20 = df["High"].rolling(20).max().iloc[-2]
    breakout_ready = last["Close"] >= high20 * 0.98

    # weekly trend (MA50 weekly)
    weekly = df.resample("W").last()
    ma50w = weekly["Close"].rolling(50).mean().iloc[-1]
    above_weekly = last["Close"] > ma50w if not np.isnan(ma50w) else True

    # ======================
    # SCORE
    # ======================

    score = 0
    score += 30 if trend_up else 0
    score += 20 if bounce else 0
    score += 15 if rsi_ok else 0
    score += 15 if vol_ok else 0
    score += 10 if breakout_ready else 0
    score += 10 if above_weekly else 0

    # ======================
    # SIGNALS
    # ======================

    BUY = (
        trend_up and
        (bounce or breakout_ready) and
        vol_ok and
        rsi_ok
    )

    WATCH = (
        trend_up and
        score >= 50
    )

    return score, BUY, WATCH, high20

# ======================
# CHART
# ======================

def create_chart(df, ticker, high20):

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

# ======================
# SCAN
# ======================

results = []
charts = []

for t in WATCHLIST[:120]:

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

msg = "📊 BASIC MARKET SCANNER\n\n"

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
