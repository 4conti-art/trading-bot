import numpy as np
import pandas as pd
import requests
import time
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from threading import Thread

print("RUNNING VERSION: FINNHUB KEEPALIVE")

app = FastAPI()

API_KEY = "d79t519r01qspme61vogd79t519r01qspme61vp0"

TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AMD","NFLX","ADBE",
    "JPM","GS","BAC","WMT","COST","HD","MCD","NKE",
    "XOM","CVX","SPY","QQQ","DIA"
]

BATCH_SIZE = 10
current_index = 0

CACHE = {"data": [], "last_update": 0}
CACHE_TTL = 60


def fetch_data(ticker):
    url = "https://finnhub.io/api/v1/stock/candle"
    now = int(time.time())
    past = now - 60*60*24*30

    params = {
        "symbol": ticker,
        "resolution": "D",
        "from": past,
        "to": now,
        "token": API_KEY
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if data.get("s") != "ok":
            print(f"{ticker}: bad response -> {data}")
            return None

        df = pd.DataFrame({"Close": data["c"]})
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

    print("Refreshing Finnhub batch...")
    results = CACHE["data"].copy()

    batch = TICKERS[current_index:current_index + BATCH_SIZE]

    for ticker in batch:
        df = fetch_data(ticker)
        result = compute_momentum(df)

        print(f"{ticker}: {result}")

        if result:
            results = [r for r in results if r["ticker"] != ticker]
            results.append({"ticker": ticker, **result})

        time.sleep(1)

    current_index = (current_index + BATCH_SIZE) % len(TICKERS)

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    CACHE["data"] = results[:10]
    CACHE["last_update"] = time.time()

    print("Updated:", CACHE["data"])


def background():
    time.sleep(10)
    refresh_cache()
    while True:
        if time.time() - CACHE["last_update"] > CACHE_TTL:
            refresh_cache()
        time.sleep(5)


def keep_alive():
    while True:
        try:
            requests.get("http://127.0.0.1:10000/")
        except:
            pass
        time.sleep(30)


@app.on_event("startup")
def start():
    Thread(target=background, daemon=True).start()
    Thread(target=keep_alive, daemon=True).start()


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/top")
def top():
    return JSONResponse(content=CACHE["data"], media_type="application/json")
