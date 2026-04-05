import numpy as np
import yfinance as yf
import pandas as pd
import time
from fastapi import FastAPI

app = FastAPI()

# Cache for S&P 500 tickers
TICKER_CACHE = {
    "tickers": [],
    "timestamp": 0
}

CACHE_TTL = 86400  # 24 hours


def get_sp500_tickers():
    now = time.time()

    if TICKER_CACHE["tickers"] and (now - TICKER_CACHE["timestamp"] < CACHE_TTL):
        return TICKER_CACHE["tickers"]

    df = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
    tickers = df["Symbol"].tolist()

    # Fix tickers like BRK.B -> BRK-B
    tickers = [t.replace(".", "-") for t in tickers]

    TICKER_CACHE["tickers"] = tickers
    TICKER_CACHE["timestamp"] = now

    return tickers


def compute_momentum(df):
    if df is None or df.empty or len(df) < 6:
        return None

    close = df["Close"].squeeze()

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
        df = yf.download(ticker, period="10d", interval="1d", progress=False)

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
    return {"message": "Trading bot is running"}


@app.get("/top")
def get_top_stocks():
    tickers = get_sp500_tickers()
    print(f"TOTAL TICKERS: {len(tickers)}")

    results = []

    for ticker in tickers:
        data = analyze_ticker(ticker)
        if data:
            results.append(data)

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    return ranked[:5]
