import numpy as np
import yfinance as yf
from fastapi import FastAPI

app = FastAPI()


def compute_momentum(df, ticker=""):
    if df is None or df.empty:
        print(f"{ticker} failed: empty df")
        return None

    print(f"{ticker} rows: {len(df)}")

    if len(df) < 6:
        print(f"{ticker} failed: not enough rows")
        return None

    df = df.copy()

    try:
        close = df["Close"].squeeze()
    except Exception as e:
        print(f"{ticker} failed: close extraction error {e}")
        return None

    log_returns = np.log(close / close.shift(1))

    momentum = (close.iloc[-1] / close.iloc[-6]) - 1

    volatility = log_returns.std() * np.sqrt(252)

    print(f"{ticker} volatility: {volatility}")

    if volatility == 0 or np.isnan(volatility):
        print(f"{ticker} failed: volatility invalid")
        return None

    score = momentum / volatility

    print(f"{ticker} OK")

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
