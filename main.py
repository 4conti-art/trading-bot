import requests
from fastapi import FastAPI
import numpy as np

app = FastAPI()

API_KEY = "0LNLJIQPXN2DOGE9"

TICKERS = ["AAPL","MSFT"]  # ✅ keep 2 for now


def fetch_series(ticker):
    url = "https://www.alphavantage.co/query"

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "outputsize": "compact",
        "apikey": API_KEY
    }

    r = requests.get(url, params=params).json()

    if "Time Series (Daily)" not in r:
        return None

    ts = r["Time Series (Daily)"]
    closes = [float(ts[date]["4. close"]) for date in sorted(ts.keys())]

    return closes


def compute_score(prices):
    if not prices or len(prices) < 21:
        return None

    close = np.array(prices)

    short = (close[-1] / close[-6]) - 1
    long = (close[-1] / close[-21]) - 1
    momentum = 0.6 * short + 0.4 * long

    log_returns = np.diff(np.log(close))
    volatility = np.std(log_returns) * np.sqrt(252)

    if volatility == 0:
        return None

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

        if score is not None:
            results.append({
                "ticker": t,
                "score": score
            })

    return sorted(results, key=lambda x: x["score"], reverse=True)