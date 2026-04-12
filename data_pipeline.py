import requests
import json
import time

API_KEY = "MRYC1GBIBJ38BN0C"
OUTPUT_FILE = "signals.json"

UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META",
    "SPY", "QQQ", "GLD", "SLV", "DBC"
]

# ----------------------------
# ✅ FETCH DATA
# ----------------------------
def fetch(symbol):
    url = (
        "https://www.alphavantage.co/query"
        f"?function=TIME_SERIES_DAILY_ADJUSTED"
        f"&symbol={symbol}"
        f"&outputsize=compact"
        f"&apikey={API_KEY}"
    )

    try:
        res = requests.get(url, timeout=10)
        data = res.json()

        ts = data.get("Time Series (Daily)")
        if not ts:
            print(f"❌ No data {symbol}")
            return None

        closes = [float(v["4. close"]) for v in ts.values()]
        closes.reverse()  # oldest → newest

        return closes

    except Exception as e:
        print(f"❌ Failed {symbol}: {e}")
        return None


# ----------------------------
# ✅ SCORE
# ----------------------------
def compute_score(close):
    if len(close) < 30:
        return None

    mom = (close[-1] / close[-20]) - 1

    returns = [
        (close[i] / close[i-1] - 1)
        for i in range(1, len(close))
    ]

    vol = sum([(r ** 2) for r in returns]) / len(returns)
    vol = vol ** 0.5

    if vol == 0:
        return None

    return mom / vol


# ----------------------------
# ✅ RUN PIPELINE
# ----------------------------
def run_pipeline():
    results = []

    for symbol in UNIVERSE:
        close = fetch(symbol)

        if close is None:
            continue

        score = compute_score(close)

        if score is None:
            continue

        results.append({
            "ticker": symbol,
            "score": float(score)
        })

        print(f"✅ {symbol}")

        time.sleep(12)  # ✅ REQUIRED (API LIMIT)

    results = sorted(results, key=lambda x: x["score"], reverse=True)[:10]

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f)

    print("\n✅ signals.json updated")


# ----------------------------
# ✅ RUN
# ----------------------------
if __name__ == "__main__":
    run_pipeline()