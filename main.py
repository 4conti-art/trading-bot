import numpy as np
import pandas as pd
import requests
import time
from fastapi import FastAPI
from threading import Thread

print("RUNNING VERSION: ROTATING SAFE")

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

BATCH_SIZE = 8
current_index = 0

CACHE = {"data": [], "last_update": 0}
CACHE_TTL = 60


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
            print(f"{ticker}: bad response")
            return None

        df = pd.DataFrame(data["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime")
        df["Close"] = df["close"].astype(float)

        return df

    except Exception as e:
        print(f"{ticker}: error {e}")
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
    global current_index

    print("Refreshing rotating batch...")
    results = CACHE["data"].copy()

    batch = TICKERS[current_index:current_index + BATCH_SIZE]

    for ticker in batch:
        df = fetch_data(ticker)
        result = compute_momentum(df)

        print(f"{ticker}: {result}")

        if result:
            results = [r for r in results if r["ticker"] != ticker]
            results.append({
                "ticker": ticker,
                **result
            })

        time.sleep(1.2)

    current_index = (current_index + BATCH_SIZE) % len(TICKERS)

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    CACHE["data"] = results[:10]
    CACHE["last_update"] = time.time()

    print("Updated:", CACHE["data"])


def background():
    time.sleep(10)  # delay startup work
    while True:
        if time.time() - CACHE["last_update"] > CACHE_TTL:
            refresh_cache()
        time.sleep(5)


@app.on_event("startup")
def start():
    Thread(target=background, daemon=True).start()


@app.get("/")
def root():
    return {"message": "Rotating universe bot running (safe startup)"}


@app.get("/top")
def top():
    return CACHE["data"]
