import numpy as np
import pandas as pd
import requests
import time
from fastapi import FastAPI
from threading import Thread

app = FastAPI()

API_KEY = "O81J337DJX2XO5YH"

TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "META"]

CACHE = {
    "data": [],
    "last_update": 0
}

CACHE_TTL = 300  # 5 minutes


def fetch_alpha_vantage(ticker):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": ticker,
        "apikey": API_KEY,
        "outputsize": "compact"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "Time Series (Daily)" not in data:
            return None

        df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df["Close"] = df["4. close"].astype(float)

        return df

    except Exception:
        return None


def compute_momentum(df):
    if df is None or df.empty or len(df) < 6:
        return None

    close = df["Close"]

    log_returns = np.log(close / close.shift(1))
    momentum = (close.iloc[-1] / close.iloc[-6]) - 1
    volatility = log_returns.std() * np.sqrt(252)

    if volatility == 0 or np.isnan(volatility):
        return None

    score = momentum / volatility

    return {
        "score": float(score),
        "momentum": float(momentum),
        "volatility": float(volatility),
    }


def refresh_cache():
    results = []

    for ticker in TICKERS:
        df = fetch_alpha_vantage(ticker)
        result = compute_momentum(df)

        if result:
            results.append({
                "ticker": ticker,
                **result
            })

        time.sleep(12)  # respect rate limit

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    CACHE["data"] = results[:5]
    CACHE["last_update"] = time.time()


def background_update():
    while True:
        now = time.time()
        if now - CACHE["last_update"] > CACHE_TTL:
            refresh_cache()
        time.sleep(5)


@app.on_event("startup")
def start_background_thread():
    thread = Thread(target=background_update, daemon=True)
    thread.start()


@app.get("/")
def root():
    return {"message": "Trading bot running"}


@app.get("/top")
def get_top_stocks():
    return CACHE["data"]
