
# MAIN TRADING BOT (TwelveData + FastAPI)

import numpy as np
import pandas as pd
import requests
import time
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from threading import Thread

app = FastAPI()

API_KEY = "de9c51d682374906a8de2c7f9e8dcb7b"

TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AMD","NFLX","ADBE",
    "JPM","GS","BAC","WMT","COST","HD","MCD","NKE",
    "XOM","CVX","XLE",
    "GLD","SLV","USO","UNG",
    "SPY","QQQ","DIA",
    "TLT","IEF",
    "XLK","XLF","XLV","XLI","XLY","XLP","XLB","XLU",
    "ARKK","SOXX"
]

CACHE = {"data": [], "last_update": 0}
CACHE_TTL = 300


def fetch_data(ticker):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": ticker,
        "interval": "1day",
        "outputsize": 30,
        "apikey": API_KEY
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if "values" not in data:
            return None

        df = pd.DataFrame(data["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime")
        df["Close"] = df["close"].astype(float)

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


def analyze_ticker(ticker):
    df = fetch_data(ticker)
    result = compute_momentum(df)

    if result is None:
        return None

    return {
        "ticker": ticker,
        **result
    }


def update_cache():
    while True:
        results = []

        for ticker in TICKERS:
            data = analyze_ticker(ticker)
            if data:
                results.append(data)

        results = sorted(results, key=lambda x: x["score"], reverse=True)[:5]

        CACHE["data"] = results
        CACHE["last_update"] = time.time()

        time.sleep(CACHE_TTL)


@app.on_event("startup")
def start_background():
    thread = Thread(target=update_cache, daemon=True)
    thread.start()


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/top")
def top():
    if not CACHE["data"]:
        return JSONResponse(content={"error": "No data yet"})

    return JSONResponse(content=CACHE["data"])
