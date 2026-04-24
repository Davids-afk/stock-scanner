import yfinance as yf
import numpy as np
import requests
import os
import pandas as pd

# ======================
# GET UNIVERSE (AUTO)
# ======================

def get_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    table = pd.read_html(url)[0]
    return table["Symbol"].str.replace(".", "-", regex=False).tolist()

def get_nasdaq100():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    tables = pd.read_html(url)
    for t in tables:
        if "Ticker" in t.columns:
            return t["Ticker"].str.replace(".", "-", regex=False).tolist()
    return []

SP500 = get_sp500()
NASDAQ100 = get_nasdaq100()

WATCHLIST = list(set(SP500 + NASDAQ100))

# ======================
# INDICATORS
# ======================

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def volume_avg(df, period=20):
    return df["Volume"].rolling(period).mean()

# ======================
# WEEKLY TREND (MA50W)
# ======================

def weekly_trend(df):
    weekly = df.resample("W").last()
    weekly["MA50W"] = weekly["Close"].rolling(50).mean()

    last = weekly.iloc[-1]

    if np.isnan(last["MA50W"]):
        return None

    price = last["Close"]
    ma50w = last["MA50W"]

    above = price > ma50w
    dist = abs(price - ma50w) / ma50w * 100

    return above, dist

# ======================
# ANALYZE
# ======================

def analyze(df):
    df = df.copy()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["RSI"] = rsi(df["Close"])
    df["VOL_AVG"] = volume_avg(df)

    last = df.iloc[-1]

    if np.isnan(last["MA20"]) or np.isnan(last["MA50"]) or np.isnan(last["RSI"]):
        return None

    # WEEKLY FILTER
    weekly = weekly_trend(df)
    if weekly is None:
        return None

    above_ma50w, dist_ma50w = weekly

    # TREND
    trend_up = last["MA50"] > df["MA50"].iloc[-5]
    price_above_ma50 = last["Close"] > last["MA50"]

    # BREAKOUT
    high_20 = df["High"].rolling(20).max().iloc[-2]
    breakout = last["Close"] > high_20

    # BOUNCE
    bounce = (
        last["Low"] <= last["MA20"] * 1.02 and
        last["Close"] > last["MA20"]
    )

    # VOLUME
    vol_ok = last["Volume"] > last["VOL_AVG"] * 1.2

    # RSI
    rsi_ok = 45 <= last["RSI"] <= 75

    # SCORE
    score = 0
    score += 25 if trend_up and price_above_ma50 else 0
    score += 25 if breakout else 0
    score += 20 if bounce else 0
    score += 15 if vol_ok else 0
    score += 10 if rsi_ok else 0
    score += 25 if above_ma50w else 0
    score += 10 if dist_ma50w < 5 else 0

    # BUY SIGNAL
    buy = (
        breakout and
        vol_ok and
        trend_up and
        rsi_ok and
        above_ma50w and
        dist_ma50w < 5
    )

    return score, buy

# ======================
# BATCHING (IMPORTANT)
# ======================

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# ======================
# SCAN
# ======================

results = []

BATCH_SIZE = 30

for batch in chunks(WATCHLIST, BATCH_SIZE):
    print(f"Scanning batch of {len(batch)} stocks...")

    for t in batch:
        try:
            df = yf.download(t, period="2y", interval="1d", progress=False)

            if df is None or df.empty:
                continue

            res = analyze(df)
            if res is None:
                continue

            score, buy = res

            print(f"{t} score={score} buy={buy}")

            results.append((t, score, buy))

        except Exception as e:
            print(f"{t} error {e}")
            continue

# ======================
# SORT
# ======================

results = sorted(results, key=lambda x: x[1], reverse=True)

top = results[:20]
buys = [r for r in results if r[2]]

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

msg = "📊 FULL MARKET SCANNER (S&P + NASDAQ)\n\n"

msg += "🔥 BUY SETUPS:\n"
if len(buys) == 0:
    msg += "No BUY signals today\n"
else:
    for t, s, _ in buys:
        msg += f"{t} — {s}\n"

msg += "\n📈 TOP SCORERS:\n"
for t, s, b in top:
    msg += f"{t} — {s}\n"

requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    data={"chat_id": CHAT_ID, "text": msg}
)

print(msg)
