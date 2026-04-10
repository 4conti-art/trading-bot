import requests
from fastapi import FastAPI
import numpy as np
import threading
import time

app = FastAPI()

API_KEY = "0LNLJIQPXN2DOGE9"

TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META",
    "SPY","QQQ","GLD","SLV","USO"
]

TOP_N = 3

DATA = []

STATIC_DATA = {
    "AAPL": np.linspace(150, 180, 60),
    "MSFT": np.linspace(300, 280, 60),
    "NVDA": np.linspace(400, 460, 60),
    "AMZN": np.linspace(120, 170, 60),
    "META": np.linspace(250, 240, 60),
    "SPY": np.linspace(400, 430, 60),
    "QQQ": np.linspace(300, 350, 60),
    "GLD": np.linspace(170, 175, 60),
    "SLV": np.linspace(20, 23, 60),
    "USO": np.linspace(60, 75, 60),
}


def fetch_series(ticker):
    url = "https://www.alphavantage.co/query"

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "outputsize": "compact",
        "apikey": API_KEY
    }

    try:
        r = requests.get(url, params=params, timeout=10).json()

        if "Time Series (Daily)" in r:
            ts = r["Time Series (Daily)"]
            closes = [float(ts[d]["4. close"]) for d in sorted(ts.keys())]
            if len(closes) >= 10:
                return closes
    except:
        pass

    return STATIC_DATA[ticker]


def compute_score(prices):
    close = np.array(prices)

    short = (close[-1] / close[-3]) - 1
    medium = (close[-1] / close[-7]) - 1

    momentum = 0.7 * short + 0.3 * medium

    log_returns = np.diff(np.log(close))
    volatility = np.std(log_returns)

    if volatility == 0 or np.isnan(volatility):
        return 0

    score = momentum / (volatility * 5)

    return max(min(score, 20), -20)


def build_data():
    global DATA

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

    DATA = results


def background_job():
    while True:
        build_data()
        time.sleep(86400)


@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=background_job)
    thread.daemon = True
    thread.start()


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/top")
def top():
    return DATA