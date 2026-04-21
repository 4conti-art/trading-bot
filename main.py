from fastapi import FastAPI
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures

app = FastAPI()

# =========================
# CONFIG
# =========================
TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD", "META"]
HISTORICAL_DATA_YEARS = 2


# =========================
# DATA FETCH
# =========================
def fetch(symbol, start, end):
    try:
        df = yf.download(symbol, start=start, end=end, progress=False, threads=False)

        if df is None or df.empty:
            return symbol, None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return symbol, df

    except:
        return symbol, None


# =========================
# ANALYSIS
# =========================
def analyze(symbol, df):
    try:
        if len(df) < 200:
            return None

        df = df.copy()

        # Trend
        df["SMA_50"] = df["Close"].rolling(50).mean()
        df["SMA_200"] = df["Close"].rolling(200).mean()

        sma50 = df["SMA_50"].iloc[-1]
        sma200 = df["SMA_200"].iloc[-1]

        if pd.isna(sma50) or pd.isna(sma200):
            return None

        trend = 1 if sma50 > sma200 else -1 if sma50 < sma200 else 0

        # Momentum
        if len(df) < 5:
            return None

        momentum = (
            df["Close"].iloc[-1] - df["Close"].iloc[-5]
        ) / df["Close"].iloc[-5]

        if pd.isna(momentum):
            return None

        # Score
        score = trend + (momentum * 2)

        return {
            "symbol": symbol,
            "trend": trend,
            "momentum": float(momentum),
            "score": float(score),
            "price": float(df["Close"].iloc[-1])
        }

    except:
        return None


# =========================
# PIPELINE
# =========================
def run():
    end = datetime.utcnow()
    start = end - timedelta(days=365 * HISTORICAL_DATA_YEARS)

    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(fetch, s, start, end) for s in TICKERS]

        for f in concurrent.futures.as_completed(futures):
            symbol, df = f.result()

            if df is not None:
                r = analyze(symbol, df)
                if r:
                    results.append(r)

    # 🔥 NEW: ranking
    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    return ranked


# =========================
# API
# =========================
@app.get("/")
def home():
    return {"status": "alive"}


@app.get("/recommendations")
def recommendations():
    return {"ranked": run()}