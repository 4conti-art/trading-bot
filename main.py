from fastapi import FastAPI
import numpy as np
import threading
import time

app = FastAPI()

TICKERS = ["AAPL","MSFT","NVDA","AMZN","META"]
TOP_N = 2
MAX_WEIGHT = 0.5
N = 120

DATA = []
BACKTEST = []

np.random.seed(42)

# ✅ realistic price generation
def generate_series(start, drift):
    prices = [start]
    for _ in range(N - 1):
        noise = np.random.normal(0, 0.01)
        prices.append(prices[-1] * (1 + drift + noise))
    return np.array(prices)

STATIC_DATA = {
    "AAPL": generate_series(150, 0.001),
    "MSFT": generate_series(300, -0.0005),
    "NVDA": generate_series(400, 0.002),
    "AMZN": generate_series(120, 0.0015),
    "META": generate_series(250, -0.001),
}


def compute_score(prices):
    close = np.array(prices)

    short = (close[-1] / close[-3]) - 1
    medium = (close[-1] / close[-7]) - 1

    momentum = 0.7 * short + 0.3 * medium

    log_returns = np.diff(np.log(close))
    vol = np.std(log_returns)

    if vol == 0 or np.isnan(vol):
        return 0

    raw = momentum / (vol * 5)

    # ✅ clamp scores
    return max(min(raw, 20), -20)


def build_portfolio(t):
    results = []

    for k in TICKERS:
        window = STATIC_DATA[k][t-10:t]
        score = compute_score(window)
        results.append({"ticker": k, "score": float(score)})

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

    # ✅ risk cap
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


def build_data():
    global DATA
    DATA = build_portfolio(N - 1)


def run_backtest():
    global BACKTEST

    equity = [1.0]

    for t in range(10, N - 1):
        portfolio = build_portfolio(t)

        ret = 0.0
        for r in portfolio:
            if r["signal"] == "BUY":
                p0 = STATIC_DATA[r["ticker"]][t]
                p1 = STATIC_DATA[r["ticker"]][t + 1]
                ret += r["weight"] * ((p1 / p0) - 1)

        equity.append(equity[-1] * (1 + ret))

    BACKTEST = equity


def background_job():
    while True:
        build_data()
        run_backtest()
        time.sleep(86400)


@app.on_event("startup")
def startup_event():
    build_data()
    run_backtest()
    thread = threading.Thread(target=background_job)
    thread.daemon = True
    thread.start()


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/top")
def top():
    return DATA


@app.get("/backtest")
def backtest():
    return BACKTEST