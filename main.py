import requests
from fastapi import FastAPI
import numpy as np
import time

app = FastAPI()

API_KEY = "0LNLJIQPXN2DOGE9"

TICKERS = ["AAPL","MSFT","NVDA","AMZN","META"]

TOP_N = 2

# ✅ simple cache (1 day)
CACHE = {}
CACHE_TIME = 0


def fetch_series(ticker):
    url = "https://www.alphavantage.co/query"

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "outputsize": "full",
        "apikey": API_KEY
    }

    r = requests.get(url, params=params).json()

    if "Time Series (Daily)" not in r:
        return None

    ts = r["Time Series (Daily)"]
    closes = [float(ts[date]["4. close"]) for date in sorted(ts.keys())]

    if len(closes) < 1000:
        return None

    return closes


def compute_score(prices):
    if not prices or len(prices) < 252 * 4:
        return None

    close = np.array(prices)
    close = close[-(252 * 4):]

    short = (close[-1] / close[-21]) - 1
    medium = (close[-1] / close[-63]) - 1
    long = (close[-1] / close[-252]) - 1

    momentum = 0.5 * short + 0.3 * medium + 0.2 * long

    log_returns = np.diff(np.log(close))
    volatility = np.std(log_returns) * np.sqrt(252)

    if volatility == 0 or np.isnan(volatility):
        return None

    return momentum / volatility


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/top")
def top():
    global CACHE, CACHE_TIME

    now = time.time()

    # ✅ return cached result if < 24h old
    if CACHE and (now - CACHE_TIME) < 86400:
        return CACHE

    results = []

    for t in TICKERS:
        prices = fetch_series(t)
        score = compute_score(prices)

        if score is not None:
            results.append({
                "ticker": t,
                "score": score
            })

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    for idx, r in enumerate(results):
        if idx < TOP_N and r["score"] > 0:
            r["signal"] = "BUY"
        elif idx == len(results) - 1:
            r["signal"] = "SELL"
        else:
            r["signal"] = "HOLD"

    # ✅ save cache
    CACHE = results
    CACHE_TIME = now

    return results