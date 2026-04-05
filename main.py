import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI
import time

app = FastAPI()

API_KEY = "O81J337DJX2XO5YH"

# Keep small list due to rate limits
TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "META"]


def fetch_alpha_vantage(ticker):
    url = f"https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": ticker,
        "apikey": API_KEY,
        "outputsize": "compact"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "Time Series (Daily)" not in data:
        return None

    df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df["Close"] = df["4. close"].astype(float)

    return df


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
    try:
        df = fetch_alpha_vantage(ticker)
        result = compute_momentum(df)

        if result is None:
            return None

        return {
            "ticker": ticker,
            **result
        }

    except Exception:
        return None


@app.get("/")
def root():
    return {"message": "Trading bot is running (Alpha Vantage)"}


@app.get("/top")
def get_top_stocks():
    results = []

    for ticker in TICKERS:
        data = analyze_ticker(ticker)
        if data:
            results.append(data)

        time.sleep(12)  # avoid rate limits

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    return ranked[:5]
