import requests
from fastapi import FastAPI
import numpy as np

app = FastAPI()

API_KEY = "0LNLJIQPXN2DOGE9"

TICKERS = ["AAPL","MSFT","NVDA","AMZN","META"]

TOP_N = 2

STATIC_DATA = {
    "AAPL": np.linspace(150, 180, 60),
    "MSFT": np.linspace(300, 290, 60),
    "NVDA": np.linspace(400, 450, 60),
    "AMZN": np.linspace(120, 160, 60),
    "META": np.linspace(250, 280, 60),
}


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
        if len(closes) >= 30:
            return closes

    return STATIC_DATA[ticker]


def compute_score(prices):
    close = np.array(prices)

    short = (close[-1] / close[-5]) - 1
    medium = (close[-1] / close[-15]) - 1

    momentum = 0.7 * short + 0.3 * medium

    log_returns = np.diff(np.log(close))
    volatility = np.std(log_returns)

    if volatility == 0 or np.isnan(volatility):
        return 0

    return momentum / (volatility * 10)


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/top")
def top():
    results = []

    for t in TICKERS:
        prices = fetch_series(t)
        score = compute_score(prices)

        results.append({
            "ticker": t,
            "score": float(score)
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    for i, r in enumerate(results):
        if i < TOP_N:
            r["signal"] = "BUY"
        elif i == len(results) - 1:
            r["signal"] = "SELL"
        else:
            r["signal"] = "HOLD"

    return results