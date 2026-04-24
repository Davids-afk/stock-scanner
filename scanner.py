import yfinance as yf
import numpy as np
import requests
import os

# ======================
# CONFIG
# ======================

SP500 = ["AAPL","MSFT","NVDA","META","AMZN","GOOGL","BRK-B","LLY","AVGO","TSLA"]
NASDAQ100 = ["AMD","ADBE","NFLX","INTC","CSCO","PEP","COST","QCOM","TXN","AMGN"]

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

# ======================
# SCORE FUNCTION
# ======================

def score(df):
    df = df.copy()

    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["RSI"] = rsi(df["Close"])

    last = df.iloc[-1]

    # חשוב: לא לזרוק הכל בגלל MA200
    if np.isnan(last["MA50"]) or np.isnan(last["RSI"]):
        return None

    trend = 40 if last["MA50"] > last["Close"] else 0
    rsi_score = 20 if last["RSI"] > 55 else 10

    bounce = 20 if last["Low"] <= last["MA50"] * 1.05 and last["Close"] >= last["MA50"] else 0

    dist = abs(last["Close"] - last["MA50"]) / last["MA50"] * 100
    dist_score = 10 if dist < 2 else 5

    return trend + rsi_score + bounce + dist_score

# ======================
# SCAN
# ======================

results = []

for t in WATCHLIST:
    try:
        # FIX חשוב מאוד: daily + 2 years
        df = yf.download(t, period="2y", interval="1d", progress=False)

        if df is None or df.empty:
            print(f"{t} no data")
            continue

        s = score(df)

        if s is None:
            continue

        print(f"{t} score: {s}")
        results.append((t, s))

    except Exception as e:
        print(f"{t} error: {e}")
        continue

# sort
results = sorted(results, key=lambda x: x[1], reverse=True)

top = results[:10]

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

msg = "📊 TOP 10 S&P + NASDAQ\n\n"

if len(top) == 0:
    msg += "No signals today 📉"
else:
    for t, s in top:
        msg += f"{t} — {s}\n"

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

print(msg)
