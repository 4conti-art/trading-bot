import numpy as np
import yfinance as yf
from fastapi import FastAPI

app = FastAPI()


def compute_momentum(df):
    if df is None or df.empty or len(df) < 6:
        return None

    df = df.copy()

    # Ensure Close is a proper Series
    close = df["Close"].squeeze()

    # Log returns
    log_returns = np.log(close / close.shift(1))

    # 1-week momentum
    momentum = (close.iloc[-1] / close.iloc[-6]) - 1

    # Annualized volatility
    volatility = log_returns.std() * np.sqrt(252)

    if volatility == 0 or np.isnan(volatility):
        return None

    score = momentum / volatility

    return {
        "score": float(score),
        "momentum": float(momentum),
        "volatility": float(volatility),
    }


TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "AMD", "TSLA"]


def analyze_ticker(ticker):
    try:
        print(f"Processing {ticker}")

        df = yf.download(ticker, period="10d", interval="1d", progress=False)

        result = compute_momentum(df)

        if result is None:
            print(f"{ticker} returned None")
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
