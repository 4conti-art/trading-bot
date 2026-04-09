import requests
from fastapi import FastAPI
import numpy as np
import time

app = FastAPI()

API_KEY = "0LNLJIQPXN2DOGE9"

TICKERS = ["AAPL","MSFT","NVDA","AMZN","META"]

TOP_N = 2


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

    closes = [float(ts[d]["4. close"]) for d in sorted(ts.keys())]

    if len(closes) < 200:
        return None

    return closes


def compute_score(prices):
    if not prices or len(prices) < 200:
        return None

    close = np.array(prices)

    # ✅ use last ~1 year instead of 4 (fix empty issue)
    close = close[-252:]

    short = (close[-1] / close[-21]) - 1
    medium = (close[-1] / close[-63]) - 1

    momentum = 0.7 * short + 0.3 * medium

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
    results = []

    for i, t in enumerate(TICKERS):
        prices = fetch_series(t)
        score = compute_score(prices)

        if score is not None:
            results.append({
                "ticker": t,
                "score": score
            })

        if i < len(TICKERS) - 1:
            time.sleep(12)

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    for idx, r in enumerate(results):
        if idx < TOP_N and r["score"] > 0:
            r["signal"] = "BUY"
        elif idx == len(results) - 1:
            r["signal"] = "SELL"
        else:
            r["signal"] = "HOLD"

    return results