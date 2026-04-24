import yfinance as yf
import pandas as pd
import numpy as np
import requests

# ======================
# CONFIG
# ======================

SP500 = ["AAPL","MSFT","NVDA","META","AMZN","GOOGL","BRK-B","LLY","AVGO","TSLA"]
NASDAQ100 = ["AMD","ADBE","NFLX","INTC","CSCO","PEP","COST","QCOM","TXN","AMGN"]

WATCHLIST = list(set(SP500 + NASDAQ100))

TOKEN = "PUT_YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "PUT_YOUR_CHAT_ID"

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

    if np.isnan(last["MA50"]) or np.isnan(last["MA200"]):
        return 0

    trend = 40 if last["MA50"] > last["MA200"] else 0
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
        df = yf.download(t, period="1y", interval="1wk")
        s = score(df)
        results.append((t, s))
    except:
        continue

results = sorted(results, key=lambda x: x[1], reverse=True)[:10]

# ======================
# TELEGRAM OUTPUT
# ======================

msg = "📊 TOP 10 S&P + NASDAQ\n\n"

for t, s in results:
    msg += f"{t} — {s}\n"

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

print(msg)
