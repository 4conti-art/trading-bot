from fastapi import FastAPI
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import logging

app = FastAPI()

# =========================
# CONFIG
# =========================
PRICE_LOWER_BOUND = 10
PRICE_UPPER_BOUND = 200
NUM_RECOMMENDATIONS = 5
HISTORICAL_DATA_YEARS = 2
MAX_WORKERS = 5

TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD", "META"]

logging.basicConfig(level=logging.INFO)


# =========================
# DATA FETCH
# =========================
def fetch_historical_data(symbol, start_date, end_date):
    try:
        data = yf.download(
            symbol,
            start=start_date,
            end=end_date,
            progress=False,
            threads=False
        )

        if data is None or data.empty:
            return None

        return data

    except Exception as e:
        logging.error(f"{symbol} fetch error: {e}")
        return None


# =========================
# ANALYSIS
# =========================
def analyze_stock(symbol, df):
    try:
        if len(df) < 200:
            return None

        df = df.copy()

        df["SMA_50"] = df["Close"].rolling(50).mean()
        df["SMA_200"] = df["Close"].rolling(200).mean()
        df["Return"] = df["Close"].pct_change()

        current_price = df["Close"].iloc[-1]
        sma50 = df["SMA_50"].iloc[-1]
        sma200 = df["SMA_200"].iloc[-1]

        if pd.isna(sma50) or pd.isna(sma200):
            return None

        trend = 1 if sma50 > sma200 else -1 if sma50 < sma200 else 0

        vol = df["Return"].tail(30).std()

        if len(df) < 5:
            return None

        momentum = (
            df["Close"].iloc[-1] - df["Close"].iloc[-5]
        ) / df["Close"].iloc[-5]

        if pd.isna(vol) or pd.isna(momentum):
            return None

        return {
            "symbol": symbol,
            "price": float(current_price),
            "trend": int(trend),
            "volatility": float(vol),
            "momentum": float(momentum),
        }

    except Exception as e:
        logging.error(f"{symbol} analysis error: {e}")
        return None


# =========================
# SCORING
# =========================
def score_stock(stock):
    return (
        stock["trend"] * 1.0
        + stock["momentum"] * 2.0
        - stock["volatility"] * 1.0
    )


def filter_and_rank(stocks):
    filtered = [
        s for s in stocks
        if PRICE_LOWER_BOUND <= s["price"] <= PRICE_UPPER_BOUND
    ]

    ranked = sorted(filtered, key=score_stock, reverse=True)
    return ranked[:NUM_RECOMMENDATIONS]


# =========================
# PIPELINE
# =========================
def process_symbol(symbol, start, end):
    df = fetch_historical_data(symbol, start, end)
    if df is not None:
        return analyze_stock(symbol, df)
    return None


def generate_recommendations():
    end = datetime.utcnow()
    start = end - timedelta(days=365 * HISTORICAL_DATA_YEARS)

    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(process_symbol, s, start, end)
            for s in TICKERS
        ]

        for f in concurrent.futures.as_completed(futures):
            try:
                r = f.result(timeout=15)
                if r:
                    results.append(r)
            except Exception as e:
                logging.error(f"Thread error: {e}")

    return filter_and_rank(results)


# =========================
# API
# =========================
@app.get("/")
def home():
    return {"message": "Trading bot V2 is alive"}


@app.get("/recommendations")
def recommendations():
    try:
        picks = generate_recommendations()

        return {
            "picks": picks,
            "note": "Trend + Momentum + Volatility model"
        }

    except Exception as e:
        logging.error(f"Endpoint error: {e}")
        return {
            "picks": [],
            "error": "Failed to generate recommendations"
        }