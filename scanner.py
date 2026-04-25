import pandas as pd
import requests

print("📊 STABLE SCANNER (STOOQ DATA)")

# ======================
# UNIVERSE (simple for stability)
# ======================

sp500 = pd.read_html(
    "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
)[0]["Symbol"].str.lower().tolist()

# stooq uses lowercase tickers with .us suffix
def to_stooq(ticker):
    return ticker.lower() + ".us"

results = []

# ======================
# SCAN
# ======================

for ticker in sp500[:200]:  # start stable small

    try:

        symbol = to_stooq(ticker)

        url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"

        df = pd.read_csv(url)

        if df.empty or len(df) < 200:
            continue

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")

        price = df["Close"].iloc[-1]

        weekly = df.set_index("Date")["Close"].resample("W").last()
        ma50w = weekly.rolling(50).mean().iloc[-1]

        if pd.isna(ma50w):
            continue

        if price > ma50w:

            results.append((ticker.upper(), price, ma50w))

    except:
        continue

# ======================
# OUTPUT
# ======================

msg = "📊 STABLE STOOQ MA50W SCANNER\n\n"

if results:
    for t, p, m in results[:50]:
        msg += f"{t} | {p:.2f} > {m:.2f}\n"
else:
    msg += "❌ NO DATA OR TOO STRICT"

print(msg)
