import requests
from fastapi import FastAPI
import numpy as np

app = FastAPI()

API_KEY = "0LNLJIQPXN2DOGE9"

TICKERS = ["AAPL","MSFT","NVDA","AMZN","META"]

TOP_N = 2


def fetch_series(ticker):
    url = "https://www.alphavantage.co/query"

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "outputsize": "compact",
        "apikey": API_KEY
    }

    r = requests.get(url, params=params).json()

    if "Time Series (Daily)" in r:
        ts = r["Time Series (Daily)"]
        closes = [float(ts[d]["4. close"]) for d in sorted(ts.keys())]
        return closes

    # ✅ fallback to quote
    q = requests.get(
        "https://www.alphavantage.co/query",
        params={
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
            "apikey": API_KEY
        }
    ).json()

    if "Global Quote" in q and "05. price" in q["Global Quote"]:
        price = float(q["Global Quote"]["05. price"])
        return [price * 0.99, price]  # minimal series

    return None


def compute_score(prices):
    if prices is None or len(prices) < 2:
        return None

    close = np.array(prices)

    if len(close) < 30:
        return (close[-1] / close[0]) - 1

    short = (close[-1] / close[-5]) - 1
    medium = (close[-1] / close[-15]) - 1
    long = (close[-1] / close[-30]) - 1

    momentum = 0.5 * short + 0.3 * medium + 0.2 * long

    log_returns = np.diff(np.log(close))
    volatility = np.std(log_returns)

    if volatility == 0 or np.isnan(volatility):
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

        if score is None:
            continue

        results.append({
            "ticker": t,
            "score": score
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    for i, r in enumerate(results):
        if i < TOP_N and r["score"] > 0:
            r["signal"] = "BUY"
        elif i == len(results) - 1:
            r["signal"] = "SELL"
        else:
            r["signal"] = "HOLD"

    return results