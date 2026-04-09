import requests
from fastapi import FastAPI
import numpy as np

app = FastAPI()

API_KEY = "0LNLJIQPXN2DOGE9"

TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META",
    "SPY","QQQ","IWM","GLD","SLV",
    "USO","UNG","TLT","XLE","XLF"
]

TOP_N = 3


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

    if len(closes) < 252 * 4:
        return None

    return closes


def compute_score(prices):
    if prices is None:
        return None

    close = np.array(prices[-(252 * 4):])

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
    results = []

    for t in TICKERS:
        prices = fetch_series(t)

        if prices is None:
            continue

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