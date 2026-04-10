from fastapi import FastAPI
import numpy as np
import threading
import time

# Optional import (safe)
try:
    import yfinance as yf
    YF_AVAILABLE = True
except:
    YF_AVAILABLE = False

app = FastAPI()

TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "META"]
TOP_N = 2
MAX_WEIGHT = 0.5

DATA = []

# ----------------------------
# ✅ CORE ENGINE (GENESIS 1)
# ----------------------------

def compute_score(prices):
    close = np.array(prices)

    short = (close[-1] / close[-3]) - 1
    medium = (close[-1] / close[-7]) - 1

    momentum = 0.7 * short + 0.3 * medium

    log_returns = np.diff(np.log(close))
    vol = np.std(log_returns)

    if vol == 0 or np.isnan(vol):
        return 0

    score = momentum / (vol * 5)

    # clamp for stability
    return float(max(min(score, 20), -20))


# ----------------------------
# ✅ FALLBACK DATA (GENESIS 2)
# ----------------------------

def generate_fallback():
    data = {}

    np.random.seed(42)

    for t in TICKERS:
        prices = [100]

        for _ in range(60):
            drift = 0.001
            noise = np.random.normal(0, 0.01)
            prices.append(prices[-1] * (1 + drift + noise))

        data[t] = prices[-60:]

    return data


# ----------------------------
# ✅ REAL DATA (OPTIONAL)
# ----------------------------

def fetch_real_data():
    if not YF_AVAILABLE:
        return {}

    data = {}

    for t in TICKERS:
        try:
            df = yf.download(t, period="6mo", interval="1d", progress=False)

            if df is None or df.empty:
                continue

            closes = df["Close"]
            closes = closes.squeeze()
            closes = closes.dropna().tolist()

            if len(closes) >= 60:
                data[t] = closes[-60:]

        except Exception as e:
            print(f"Fetch failed for {t}: {e}")

    return data


# ----------------------------
# ✅ DATA LAYER (GENESIS 3)
# ----------------------------

def get_data():
    real = fetch_real_data()

    if len(real) == len(TICKERS):
        print("✅ Using REAL data")
        return real

    print("⚠️ Using FALLBACK data")
    return generate_fallback()


# ----------------------------
# ✅ PORTFOLIO ENGINE (GENESIS 4)
# ----------------------------

def build_portfolio(market):
    results = []

    for t in market:
        score = compute_score(market[t])
        results.append({"ticker": t, "score": score})

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    # signals
    for i, r in enumerate(results):
        if i < TOP_N:
            r["signal"] = "BUY"
        elif i == len(results) - 1:
            r["signal"] = "SELL"
        else:
            r["signal"] = "HOLD"

    # weights
    buy = [r for r in results if r["signal"] == "BUY"]
    total = sum(r["score"] for r in buy)

    for r in results:
        if r["signal"] == "BUY" and total > 0:
            r["weight"] = r["score"] / total
        else:
            r["weight"] = 0.0

    # cap + redistribute
    excess = 0.0
    for r in buy:
        if r["weight"] > MAX_WEIGHT:
            excess += r["weight"] - MAX_WEIGHT
            r["weight"] = MAX_WEIGHT

    remaining = [r for r in buy if r["weight"] < MAX_WEIGHT]

    if remaining and excess > 0:
        rem_total = sum(r["weight"] for r in remaining)
        if rem_total > 0:
            for r in remaining:
                r["weight"] += excess * (r["weight"] / rem_total)

    # normalize
    norm = sum(r["weight"] for r in buy)
    if norm > 0:
        for r in buy:
            r["weight"] /= norm

    return results


# ----------------------------
# ✅ PIPELINE (GENESIS 5)
# ----------------------------

def build_data():
    global DATA
    market = get_data()
    DATA = build_portfolio(market)


def background_job():
    while True:
        build_data()
        time.sleep(3600)


@app.on_event("startup")
def startup_event():
    build_data()

    thread = threading.Thread(target=background_job)
    thread.daemon = True
    thread.start()


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/top")
def top():
    return DATA