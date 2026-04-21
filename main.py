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
        return df if df is not None and not df.empty else None
    except:
        return None


# =========================
# DEBUG ANALYSIS (no filters)
# =========================
def analyze(symbol, df):
    try:
        return {
            "symbol": symbol,
            "rows": len(df),
            "last_price": float(df["Close"].iloc[-1]) if len(df) > 0 else None
        }
    except:
        return {
            "symbol": symbol,
            "error": "analysis_failed"
        }


# =========================
# PIPELINE
# =========================
def run():
    end = datetime.utcnow()
    start = end - timedelta(days=365 * HISTORICAL_DATA_YEARS)

    out = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(fetch, s, start, end) for s in TICKERS]

        for i, f in enumerate(concurrent.futures.as_completed(futures)):
            df = f.result()
            symbol = TICKERS[i]

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
    return {"debug": run()}