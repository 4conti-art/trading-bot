from fastapi import FastAPI
import numpy as np
import threading
import time
import yfinance as yf

app = FastAPI()

TICKERS = ["AAPL","MSFT","NVDA","AMZN","META"]
TOP_N = 2
MAX_WEIGHT = 0.5

DATA = []


def fetch_data():
    data = {}

    for t in TICKERS:
        df = yf.download(t, period="6mo", interval="1d", progress=False)

        if df.empty:
            continue

        closes = df["Close"]

        # ✅ FIX: handle DataFrame vs Series
        closes = closes.squeeze()
        closes = closes.dropna().tolist()

        if len(closes) >= 60:
            data[t] = closes[-60:]

    return data


def compute_score(prices):
    close = np.array(prices)

    short = (close[-1] / close[-3]) - 1
    medium = (close[-1] / close[-7]) - 1

    momentum = 0.7 * short + 0.3 * medium

    log_returns = np.diff(np.log(close))
    vol = np.std(log_returns)

    if vol == 0 or np.isnan(vol):
        return 0

    return max(min(momentum / (vol * 5), 20), -20)


def build_portfolio(data):
    results = []

    for t in data:
        score = compute_score(data[t])
        results.append({"ticker": t, "score": float(score)})

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
        r["weight"] = (r["score"] / total) if r["signal"] == "BUY" and total > 0 else 0.0

    # cap
    excess = 0
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
    market = fetch_data()
    if market:
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