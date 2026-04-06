import os
import requests
from fastapi import FastAPI

app = FastAPI()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA",
    "JPM","V","UNH","HD","PG","MA","XOM","CVX",
    "KO","PEP","AVGO","COST","MRK"
]

current_position = None


@app.get("/")
def root():
    return {"status": "ok"}


def get_quote(ticker: str):
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        c = data.get("c")
        pc = data.get("pc")

        if c is None or pc in (None, 0):
            return None

        change = (c - pc) / pc
        return {"ticker": ticker, "change": change}
    except Exception:
        return None


@app.get("/top")
def top():
    global current_position

    results = []

    for t in TICKERS:
        q = get_quote(t)
        if q:
            results.append(q)

    results = [r for r in results if r["change"] > 0]
    results = sorted(results, key=lambda x: x["change"], reverse=True)

    top = results[0] if results else None

    if current_position is None:
        if top:
            current_position = top["ticker"]
            return {"action": "BUY", "ticker": current_position, "change": top["change"]}
        else:
            return {"action": "HOLD", "ticker": None}

    else:
        if not top:
            action = {"action": "SELL", "ticker": current_position}
            current_position = None
            return action

        if top["ticker"] == current_position:
            return {"action": "HOLD", "ticker": current_position, "change": top["change"]}

        else:
            action = {
                "action": "SELL_AND_BUY",
                "sell": current_position,
                "buy": top["ticker"],
                "change": top["change"]
            }
            current_position = top["ticker"]
            return action
