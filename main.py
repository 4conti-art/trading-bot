import numpy as np
import pandas as pd
import requests
import time
from fastapi import FastAPI
from threading import Thread

print("RUNNING VERSION: EXPANDED UNIVERSE (S&P 500)")

app = FastAPI()

API_KEY = "de9c51d682374906a8de2c7f9e8dcb7b"

# -----------------------------
# GET S&P 500 TICKERS (cached once)
# -----------------------------
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    df = tables[0]
    tickers = df["Symbol"].tolist()
    return tickers

TICKERS = get_sp500_tickers()

CACHE = {"data": [], "last_update": 0}
CACHE_TTL = 60  # faster refresh for testing


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
    print("Refreshing S&P 500 universe...")
    results = []

    for i, ticker in enumerate(TICKERS):
        df = fetch_data(ticker)
        result = compute_momentum(df)

        if result:
            results.append({
                "ticker": ticker,
                **result
            })

        # small delay (S&P 500 is large)
        time.sleep(0.8)

        if i % 50 == 0:
            print(f"Progress: {i}/{len(TICKERS)}")

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    CACHE["data"] = results[:10]
    CACHE["last_update"] = time.time()

    print("Updated top 10:", CACHE["data"])


def background():
    time.sleep(5)
    while True:
        if time.time() - CACHE["last_update"] > CACHE_TTL:
            refresh_cache()
        time.sleep(5)


@app.on_event("startup")
def start():
    Thread(target=background, daemon=True).start()


@app.get("/")
def root():
    return {"message": "S&P 500 bot running"}


@app.get("/top")
def top():
    return CACHE["data"]
