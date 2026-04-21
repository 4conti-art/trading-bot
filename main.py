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

        # 🔧 FIX: flatten multi-index columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return symbol, df

    except Exception:
        return symbol, None


# =========================
# ANALYSIS (SAFE)
# =========================
def analyze(symbol, df):
    try:
        if "Close" not in df.columns:
            return {"symbol": symbol, "error": "no_close_column"}

        return {
            "symbol": symbol,
            "rows": int(len(df)),
            "last_price": float(df["Close"].iloc[-1])
        }

    except Exception:
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
    return {"debug": run()}