import pandas as pd
import requests

print("📊 SAFE RUN SCANNER")

# ======================
# UNIVERSE
# ======================

try:
    sp500 = pd.read_html(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    )[0]["Symbol"].tolist()
except:
    sp500 = ["AAPL","MSFT","NVDA","AMZN","GOOGL"]

def to_stooq(t):
    return t.lower() + ".us"

results = []

# ======================
# SCAN (SAFE LOOP)
# ======================

for ticker in sp500[:100]:  # קטן ליציבות

    try:

        symbol = to_stooq(ticker)

        url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"

        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            continue

        from io import StringIO

        df = pd.read_csv(StringIO(r.text))

        if df.empty or len(df) < 200:
            continue

        df = df.sort_values("Date")

        price = df["Close"].iloc[-1]

        weekly = df.set_index("Date")["Close"].rolling(5).mean()

        ma50w = weekly.rolling(50).mean().iloc[-1]

        if pd.isna(ma50w):
            continue

        if price > ma50w:

            results.append((ticker, price, ma50w))

    except Exception as e:
        print("skip:", ticker)
        continue

# ======================
# OUTPUT
# ======================

print("RESULTS:", len(results))

for r in results[:20]:
    print(r)
