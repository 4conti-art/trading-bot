import numpy as np
import yfinance as yf
from fastapi import FastAPI
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

# Same stable ticker set
TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","BRK-B","LLY","AVGO",
    "TSLA","JPM","UNH","V","XOM","MA","HD","PG","COST","MRK",
    "ABBV","PEP","KO","ADBE","NFLX","CRM","WMT","ACN","AMD","MCD",
    "INTC","TMO","LIN","DHR","ORCL","NKE","QCOM","TXN","AMAT","LOW",
    "HON","UPS","RTX","BA","IBM","GE","CAT","GS","BLK","PLD"
]


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
    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        data = executor.map(analyze_ticker, TICKERS)

    for r in data:
        if r:
            results.append(r)

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    return ranked[:5]
