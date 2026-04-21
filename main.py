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
# ANALYSIS (TREND ONLY)
# =========================
def analyze(symbol, df):
    try:
        if len(df) < 200:
            return {"symbol": symbol, "error": "not_enough_data"}

        df = df.copy()

        df["SMA_50"] = df["Close"].rolling(50).mean()
        df["SMA_200"] = df["Close"].rolling(200).mean()

        sma50 = df["SMA_50"].iloc[-1]
        sma200 = df["SMA_200"].iloc[-1]

        if pd.isna(sma50) or pd.isna(sma200):
            return {"symbol": symbol, "error": "nan_sma"}

        trend = 1 if sma50 > sma200 else -1 if sma50 < sma200 else 0

        return {
            "symbol": symbol,
            "trend": trend,
            "price": float(df["Close"].iloc[-1])
        }

    except:
        return {"symbol": symbol, "error": "analysis_failed"}


# =========================
# PIPELINE
# =========================
def run():
    end = datetime.utcnow()
    start = end - timedelta(days=365 * HISTORICAL_DATA_YEARS)

    out = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(fetch, s, start, end) for s in TICKERS]

        for f in concurrent.futures.as_completed(futures):
            symbol, df = f.result()

            if df is None:
                out.append({"symbol": symbol, "error": "no_data"})
            else:
                out.append(analyze(symbol, df))

    return out


# =========================
# API
# =========================
@app.get("/")
def home():
    return {"status": "alive"}


@app.get("/recommendations")
def recommendations():
    return {"trend_debug": run()}