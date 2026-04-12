import requests
import pandas as pd
from io import StringIO

# ----------------------------
# ✅ UNIVERSE
# ----------------------------
UNIVERSE = [
    "AAPL.US", "MSFT.US", "NVDA.US", "AMZN.US", "META.US",
    "SPY.US", "QQQ.US", "IWM.US",
    "GLD.US", "SLV.US", "USO.US", "UNG.US",
    "DBC.US", "DBA.US",
    "XLE.US", "XLF.US", "XLB.US",
]

# ----------------------------
# ✅ FETCH (ROBUST)
# ----------------------------
def fetch_stooq(symbol):
    url = f"https://stooq.com/q/d/l/?s={symbol.lower()}&i=d"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            print(f"❌ HTTP {symbol}")
            return None

        text = res.text.strip()

        # ✅ Basic validation
        if "Date,Open,High,Low,Close,Volume" not in text:
            print(f"❌ Bad data {symbol}")
            return None

        df = pd.read_csv(StringIO(text))

        if df.empty:
            return None

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")

        return df

    except Exception as e:
        print(f"❌ Failed {symbol}: {e}")
        return None


# ----------------------------
# ✅ BUILD DATASET
# ----------------------------
def build_dataset():
    data = {}

    for symbol in UNIVERSE:
        df = fetch_stooq(symbol)

        if df is None or len(df) < 60:
            continue

        data[symbol] = df
        print(f"✅ {symbol} loaded")

    print(f"\n✅ FINAL DATASET: {len(data)} assets")
    return data


# ----------------------------
# ✅ METRICS
# ----------------------------
def compute_metrics(df):
    close = df["Close"]

    mom5 = close.iloc[-1] / close.iloc[-5] - 1
    mom20 = close.iloc[-1] / close.iloc[-20] - 1
    mom60 = close.iloc[-1] / close.iloc[-60] - 1

    returns = close.pct_change()
    vol = returns.std() * (252 ** 0.5)

    return mom5, mom20, mom60, vol, close.iloc[-1]


# ----------------------------
# ✅ SCORE
# ----------------------------
def score(mom5, mom20, mom60, vol):
    if vol == 0:
        return 0

    momentum = 0.5*mom5 + 0.3*mom20 + 0.2*mom60
    return momentum / vol


# ----------------------------
# ✅ TOP PICKS
# ----------------------------
def get_top_picks(n=10):
    data = build_dataset()
    results = []

    for symbol, df in data.items():
        mom5, mom20, mom60, vol, price = compute_metrics(df)
        s = score(mom5, mom20, mom60, vol)

        results.append({
            "symbol": symbol,
            "score": s,
            "price": price
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return results[:n]


# ----------------------------
# ✅ RUN
# ----------------------------
if __name__ == "__main__":
    picks = get_top_picks(10)

    print("\n🔥 TOP PICKS:\n")

    for p in picks:
        print(f"{p['symbol']} | score={p['score']:.4f} | price={p['price']:.2f}")