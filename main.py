import numpy as np
import requests
from fastapi import FastAPI

app = FastAPI()

API_KEY = "O81J337DJX2XO5YH"

def fetch_data(symbol):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=compact&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "Time Series (Daily)" not in data:
        print("Error fetching data:", data)
        return None

    ts = data["Time Series (Daily)"]
    closes = [float(v["4. close"]) for v in ts.values()]
    closes.reverse()  # oldest → newest

    return closes

def compute_momentum(closes):
    if closes is None or len(closes) < 6:
        return None

    closes = np.array(closes)

    log_returns = np.log(closes[1:] / closes[:-1])

    momentum = (closes[-1] / closes[-6]) - 1
    volatility = np.std(log_returns) * np.sqrt(252)

    if volatility == 0 or np.isnan(volatility):
        return None

    score = momentum / volatility

    return {
        "score": float(score),
        "momentum": float(momentum),
        "volatility": float(volatility),
    }

TICKERS = ["AAPL"]

def analyze_ticker(ticker):
    try:
        closes = fetch_data(ticker)
        print(ticker, "points:", len(closes) if closes else 0)

        result = compute_momentum(closes)
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
    return {"message": "Trading bot is running (Alpha Vantage)"}

@app.get("/top")
def get_top_stocks():
    results = []

    for ticker in TICKERS:
        data = analyze_ticker(ticker)
        if data:
            results.append(data)

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    return ranked[:5]
