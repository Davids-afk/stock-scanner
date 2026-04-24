import yfinance as yf
import numpy as np
import requests
import os
import pandas as pd

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
# WEEKLY MA50
# ======================

def weekly_ma50(df):

    weekly = df.resample("W").last()

    weekly["MA50W"] = weekly["Close"].rolling(50).mean()

    last = weekly.iloc[-1]

    if np.isnan(last["MA50W"]):
        return False, 999   # במקום None

    price = last["Close"]
    ma50w = last["MA50W"]

    distance = abs(price - ma50w) / ma50w * 100

    return price > ma50w, distance

# ======================
# ANALYSIS
# ======================

def analyze(df):

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    df["RSI"] = rsi(df["Close"])

    df["VOL_AVG"] = df["Volume"].rolling(20).mean()

    last = df.iloc[-1]

    if np.isnan(last["MA20"]) or np.isnan(last["MA50"]):
        return None

    above_ma50w, dist_ma50w = weekly_ma50(df)

    # TREND
    trend_up = last["Close"] > last["MA50"]

    # EARLY BREAKOUT (יותר רך)
    high_20 = df["High"].rolling(20).max().iloc[-2]

    early_breakout = last["Close"] > high_20 * 0.97

    # VOLUME
    vol_ok = last["Volume"] > last["VOL_AVG"] * 0.9

    # RSI
    rsi_ok = 40 <= last["RSI"] <= 75

    # קרוב ל-MA50W
    near_ma50w = dist_ma50w < 10

    score = 0

    score += 25 if trend_up else 0
    score += 25 if early_breakout else 0
    score += 15 if vol_ok else 0
    score += 15 if rsi_ok else 0
    score += 20 if near_ma50w else 0
    score += 10 if above_ma50w else 0

    BUY = (
        early_breakout
        and trend_up
        and near_ma50w
    )

    WATCH = (
        early_breakout
        and trend_up
    )

    return score, BUY, WATCH

# ======================
# SCAN
# ======================

results = []

LIMIT = 200   # כדי לא להעמיס על GitHub

for t in WATCHLIST[:LIMIT]:

    try:

        df = yf.download(
            t,
            period="2y",
            interval="1d",
            progress=False
        )

        if df.empty:
            continue

        res = analyze(df)

        if res is None:
            continue

        score, buy, watch = res

        results.append((t, score, buy, watch))

    except Exception as e:
        print(t, e)

# ======================
# SORT
# ======================

results = sorted(results, key=lambda x: x[1], reverse=True)

top = results[:15]

buys = [r for r in results if r[2]]

watch = [r for r in results if r[3]]

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

msg = "📊 MARKET SCANNER\n\n"

msg += "🔥 BUY:\n"

if len(buys) == 0:
    msg += "None today\n"
else:
    for t, s, _, _ in buys[:10]:
        msg += f"{t} — {s}\n"

msg += "\n👀 WATCH:\n"

for t, s, _, _ in watch[:10]:
    msg += f"{t} — {s}\n"

msg += "\n📈 TOP SCORES:\n"

for t, s, _, _ in top:
    msg += f"{t} — {s}\n"

requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    data={"chat_id": CHAT_ID, "text": msg}
)

print(msg)
