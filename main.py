import requests
import pandas as pd
import numpy as np
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import time

print("RUNNING VERSION: FINNHUB DAILY TOP 5")

app = FastAPI()

API_KEY = "d79t519r01qspme61vogd79t519r01qspme61vp0"

TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AMD","NFLX","ADBE",
    "JPM","GS","BAC","WMT","COST","HD","XOM","CVX","SPY","QQQ"
]

def fetch_quote(ticker):
    url = "https://finnhub.io/api/v1/quote"
    params = {"symbol": ticker, "token": API_KEY}
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if "c" not in data or "pc" not in data:
            return None
        change = (data["c"] - data["pc"]) / data["pc"]
        return {"ticker": ticker, "price": data["c"], "change": change}
    except:
        return None

def fetch_history(ticker):
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
            return None
        df = pd.DataFrame({"Close": data["c"]})
        return df
    except:
        return None

def compute_score(df):
    if df is None or len(df) < 6:
        return None
    close = df["Close"]
    log_returns = np.log(close / close.shift(1))
    momentum = (close.iloc[-1] / close.iloc[-6]) - 1
    volatility = log_returns.std() * np.sqrt(252)
    if volatility == 0 or np.isnan(volatility):
        return None
    return float(momentum / volatility)

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/top")
def top():
    quotes = []
    for t in TICKERS:
        q = fetch_quote(t)
        if q:
            quotes.append(q)

    quotes = sorted(quotes, key=lambda x: abs(x["change"]), reverse=True)[:5]

    results = []
    for q in quotes:
        df = fetch_history(q["ticker"])
        score = compute_score(df)
        if score:
            results.append({
                "ticker": q["ticker"],
                "change": q["change"],
                "score": score
            })

    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return JSONResponse(content=results)
