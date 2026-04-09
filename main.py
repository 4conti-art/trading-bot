import requests
from fastapi import FastAPI
import numpy as np
import time

app = FastAPI()

API_KEY = "d79t519r01qspme61vogd79t519r01qspme61vp0"

TICKERS = ["AAPL","MSFT","NVDA","AMZN","META"]


def fetch_series(ticker):
    url = "https://finnhub.io/api/v1/stock/candle"

    now = int(time.time())
    past = now - 60 * 60 * 24 * 90  # ✅ 90 days for proper momentum

    params = {
        "symbol": ticker,
        "resolution": "D",
        "from": past,
        "to": now,
        "token": API_KEY
    }

    r = requests.get(url, params=params).json()

    # ✅ ONLY accept real candle data
    if "c" in r and r.get("s") == "ok" and len(r["c"]) > 25:
        return r["c"]

    return None


def compute_score(prices):
    if not prices or len(prices) < 21:
        return None

    close = np.array(prices)

    # ✅ momentum
    short = (close[-1] / close[-6]) - 1
    long = (close[-1] / close[-21]) - 1
    momentum = 0.6 * short + 0.4 * long

    # ✅ volatility
    log_returns = np.diff(np.log(close))
    volatility = np.std(log_returns)

    if volatility == 0 or np.isnan(volatility):
        return None

    # ✅ final score (Sharpe-like)
    return momentum / volatility


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/top")
def top():
    results = []

    for t in TICKERS:
        prices = fetch_series(t)
        score = compute_score(prices)

        if score is None:
            continue

        results.append({
            "ticker": t,
            "score": score
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)