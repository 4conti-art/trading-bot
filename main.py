import numpy as np
import yfinance as yf
from fastapi import FastAPI

app = FastAPI()

def compute_momentum(df):
    if df is None or df.empty or len(df) < 6:
        return None

    df = df.copy()

    df["log_returns"] = np.log(df["Close"] / df["Close"].shift(1))

    momentum = float((df["Close"].iloc[-1].item() / df["Close"].iloc[-6].item()) - 1)
    volatility = float(df["log_returns"].std().item() * np.sqrt(252))

    if volatility == 0 or np.isnan(volatility):
        return None

    score = float(momentum / volatility)

    return {
        "score": score,
        "momentum": momentum,
        "volatility": volatility,
    }

TICKERS = ["AAPL"]

def analyze_ticker(ticker):
    try:
        df = yf.download(ticker, period="10d", interval="1d", progress=False)
        print(ticker, "rows:", len(df))

        result = compute_momentum(df)
        if result is None:
            return None

        return {
            "ticker": ticker,
            **result
        }

    except Exception as e:
        print(f"Error with {ticker}: {e}")
        return None

@app.get("/")
def root():
    return {"message": "Trading bot is running"}

@app.get("/top")
def get_top_stocks():
    results = []

    for ticker in TICKERS:
        data = analyze_ticker(ticker)
        if data:
            results.append(data)

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    return ranked[:5]
