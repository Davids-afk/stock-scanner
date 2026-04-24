import yfinance as yf
import numpy as np
import requests
import os
import pandas as pd

# ======================
# SAFE SYMBOL LOADING
# ======================

def load_sp500():

    try:
        table = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]

        symbols = table["Symbol"].tolist()

        symbols = [s.replace(".", "-") for s in symbols]

        print(f"S&P500 loaded: {len(symbols)}")

        return symbols

    except Exception as e:

        print("SP500 load failed — using fallback")

        return [
            "AAPL","MSFT","NVDA","AMZN","GOOGL",
            "META","TSLA","AVGO","BRK-B","LLY"
        ]


def load_nasdaq100():

    try:

        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100"
        )

        for t in tables:

            if "Ticker" in t.columns:

                symbols = t["Ticker"].tolist()

                symbols = [s.replace(".", "-") for s in symbols]

                print(f"NASDAQ100 loaded: {len(symbols)}")

                return symbols

    except Exception as e:

        print("NASDAQ100 load failed — using fallback")

        return [
            "AMD","ADBE","NFLX","INTC",
            "CSCO","QCOM","TXN","AMGN"
        ]


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


def volume_avg(df, period=20):

    return df["Volume"].rolling(period).mean()


# ======================
# WEEKLY MA50
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
# ANALYSIS
# ======================

def analyze(df):

    df = df.copy()

    df["MA20"] = df["Close"].rolling(20).mean()

    df["MA50"] = df["Close"].rolling(50).mean()

    df["RSI"] = rsi(df["Close"])

    df["VOL_AVG"] = volume_avg(df)

    last = df.iloc[-1]

    if np.isnan(last["MA20"]) or np.isnan(last["MA50"]):

        return None

    weekly = weekly_trend(df)

    if weekly is None:

        return None

    above_ma50w, dist_ma50w = weekly

    trend_up = last["MA50"] > df["MA50"].iloc[-5]

    price_above_ma50 = last["Close"] > last["MA50"]

    high_20 = df["High"].rolling(20).max().iloc[-2]

    breakout = last["Close"] > high_20

    bounce = (
        last["Low"] <= last["MA20"] * 1.02
        and last["Close"] > last["MA20"]
    )

    vol_ok = last["Volume"] > last["VOL_AVG"] * 1.2

    rsi_ok = 45 <= last["RSI"] <= 75

    score = 0

    score += 25 if trend_up and price_above_ma50 else 0
    score += 25 if breakout else 0
    score += 20 if bounce else 0
    score += 15 if vol_ok else 0
    score += 10 if rsi_ok else 0
    score += 25 if above_ma50w else 0
    score += 10 if dist_ma50w < 5 else 0

    buy = (
        breakout
        and vol_ok
        and trend_up
        and rsi_ok
        and above_ma50w
        and dist_ma50w < 5
    )

    return score, buy


# ======================
# BATCH SCAN
# ======================

def chunks(lst, n):

    for i in range(0, len(lst), n):

        yield lst[i:i + n]


results = []

BATCH_SIZE = 25

for batch in chunks(WATCHLIST, BATCH_SIZE):

    print("Scanning batch:", len(batch))

    for t in batch:

        try:

            df = yf.download(
                t,
                period="2y",
                interval="1d",
                progress=False
            )

            if df is None or df.empty:

                continue

            res = analyze(df)

            if res is None:

                continue

            score, buy = res

            print(t, score, buy)

            results.append((t, score, buy))

        except Exception as e:

            print(t, "error:", e)

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

msg = "📊 FULL MARKET SCANNER\n\n"

msg += "🔥 BUY SETUPS:\n"

if len(buys) == 0:

    msg += "No BUY signals today\n"

else:

    for t, s, _ in buys:

        msg += f"{t} — {s}\n"

msg += "\n📈 TOP SCORES:\n"

for t, s, _ in top:

    msg += f"{t} — {s}\n"

requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    data={"chat_id": CHAT_ID, "text": msg}
)

print(msg)
