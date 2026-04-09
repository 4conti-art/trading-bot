import requests
from fastapi import FastAPI
import numpy as np
import time

app = FastAPI()

API_KEY = "0LNLJIQPXN2DOGE9"

TICKERS = ["AAPL","MSFT","NVDA","AMZN","META"]

# ✅ Strategy parameters
BUY_THRESHOLD = 0.5
SELL_THRESHOLD = -0.5


def fetch_series(ticker):
    url = "https://www.alphavantage.co/query"

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "apikey": API_KEY
    }

    r = requests.get(url, params=params).json()

    if "Time Series (Daily)" not in r:
        return None

    ts = r["Time Series (Daily)"]

    closes = [float(ts[date]["4. close"]) for date in sorted(ts.keys())]

    if len(closes) < 30:
        return None

    return closes


def compute_score(prices):
    if not prices or len(prices) < 21:
        return None

    close = np.array(prices)

    # ✅ momentum
    short = (close[-1] / close[-6]) - 1
    long = (close[-1] / close[-21]) - 1
    momentum = 0.6 * short + 0.4 * long

    # ✅ volatility (annualized)
    log_returns = np.diff(np.log(close))
    volatility = np.std(log_returns) * np.sqrt(252)

    if volatility == 0 or np.isnan(volatility):
        return None

    return momentum / volatility


def generate_signal(score):
    if score is None:
        return "NO_DATA"

    if score > BUY_THRESHOLD:
        return "BUY"

    if score < SELL_THRESHOLD:
        return "SELL"

    return "HOLD"


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/top")
def top():
    results = []

    for i, t in enumerate(TICKERS):
        prices = fetch_series(t)
        score = compute_score(prices)
        signal = generate_signal(score)

        if score is not None:
            results.append({
                "ticker": t,
                "score": score,
                "signal": signal
            })

        # ✅ respect API rate limit
        if i < len(TICKERS) - 1:
            time.sleep(12)

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return results