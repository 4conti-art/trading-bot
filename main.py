import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI
import time

app = FastAPI()

API_KEY = "O81J337DJX2XO5YH"

TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "META"]


def fetch_alpha_vantage(ticker):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": ticker,
        "apikey": API_KEY,
        "outputsize": "compact"
    }

    response = requests.get(url, params=params)
    data = response.json()

    print(f"{ticker} keys: {list(data.keys())}")

    if "Time Series (Daily)" not in data:
        print(f"{ticker} skipped (bad response)")
        return None

    df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df["Close"] = df["4. close"].astype(float)

    print(f"{ticker} rows: {len(df)}")

    return df


def compute_momentum(df, ticker=""):
    if df is None or df.empty or len(df) < 6:
        print(f"{ticker} failed (data issue)")
        return None

    close = df["Close"]

    log_returns = np.log(close / close.shift(1))
    momentum = (close.iloc[-1] / close.iloc[-6]) - 1
    volatility = log_returns.std() * np.sqrt(252)

    print(f"{ticker} volatility: {volatility}")

    if volatility == 0 or np.isnan(volatility):
        print(f"{ticker} failed (volatility)")
        return None

    score = momentum / volatility

    print(f"{ticker} OK")

    return {
        "score": float(score),
        "momentum": float(momentum),
        "volatility": float(volatility),
    }


def analyze_ticker(ticker):
    try:
        df = fetch_alpha_vantage(ticker)
        result = compute_momentum(df, ticker)

        if result is None:
            return None

        return {
            "ticker": ticker,
            **result
        }

    except Exception as e:
        print(f"ERROR {ticker}: {e}")
        return None


@app.get("/")
def root():
    return {"message": "Trading bot is running (Alpha debug)"}


@app.get("/top")
def get_top_stocks():
    results = []

    for ticker in TICKERS:
        print(f"Processing {ticker}")

        data = analyze_ticker(ticker)
        if data:
            results.append(data)

        time.sleep(12)

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    return ranked[:5]
