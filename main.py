from fastapi import FastAPI
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures

app = FastAPI()

# =========================
# CONFIG
# =========================
HISTORICAL_DATA_YEARS = 2
TOP_N = 5
MAX_WORKERS = 5
MAX_TICKERS = 150


# =========================
# LOAD TICKERS
# =========================
def load_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
        df = pd.read_csv(url)
        tickers = df["Symbol"].tolist()
        tickers = [t.replace(".", "-") for t in tickers]
        return tickers[:MAX_TICKERS]
    except:
        return ["AAPL", "MSFT", "NVDA", "TSLA"]


TICKERS = load_tickers()


# =========================
# FETCH
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

        price = float(df["Close"].iloc[-1])

        df["SMA_50"] = df["Close"].rolling(50).mean()
        df["SMA_200"] = df["Close"].rolling(200).mean()

        sma50 = df["SMA_50"].iloc[-1]
        sma200 = df["SMA_200"].iloc[-1]

        if pd.isna(sma50) or pd.isna(sma200):
            return None

        trend = 1 if sma50 > sma200 else -1 if sma50 < sma200 else 0

        momentum = (
            df["Close"].iloc[-1] - df["Close"].iloc[-5]
        ) / df["Close"].iloc[-5]

        if pd.isna(momentum):
            return None

        score = trend + (momentum * 2)

        return {
            "symbol": symbol,
            "trend": trend,
            "momentum": float(momentum),
            "score": float(score),
            "price": price
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

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(fetch, s, start, end) for s in TICKERS]

        for f in concurrent.futures.as_completed(futures):
            symbol, df = f.result()

            if df is not None:
                r = analyze(symbol, df)
                if r:
                    results.append(r)

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    return ranked[:TOP_N]


# =========================
# API
# =========================
@app.get("/")
def home():
    return {"status": "Trading bot live", "universe": len(TICKERS)}


@app.get("/recommendations")
def recommendations():
    return {
        "picks": run(),
        "note": "No price filter"
    }