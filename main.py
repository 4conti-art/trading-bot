import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

print("RUNNING VERSION: FINNHUB FREE (QUOTE ONLY)")

app = FastAPI()

API_KEY = "d79t519r01qspme61vogd79t519r01qspme61vp0"

TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AMD","NFLX","ADBE",
    "JPM","GS","BAC","WMT","COST","HD","XOM","CVX","SPY","QQQ"
]

def fetch_quote(ticker):
    url = "https://finnhub.io/api/v1/quote"
    params = {"symbol": ticker, "token": API_KEY}
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()

        if "c" not in data or "pc" not in data or data["pc"] == 0:
            return None

        change = (data["c"] - data["pc"]) / data["pc"]

        return {
            "ticker": ticker,
            "price": data["c"],
            "change": change
        }
    except:
        return None


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/top")
def top():
    results = []

    # Get all quotes
    for t in TICKERS:
        q = fetch_quote(t)
        if q:
            results.append(q)

    # If nothing came back, return debug info
    if not results:
        return JSONResponse(content={"error": "No data returned from Finnhub"})

    # Pick top 5 movers
    results = sorted(results, key=lambda x: abs(x["change"]), reverse=True)[:5]

    # Add simple "score" (same as change for now)
    for r in results:
        r["score"] = r["change"]

    return JSONResponse(content=results)
