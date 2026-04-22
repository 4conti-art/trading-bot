import requests
import random
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

API_KEY = "69e8cdc7e8f9d9.44028983"

POOL = [
    "AAPL.US","MSFT.US","NVDA.US","AMZN.US","META.US",
    "GOOGL.US","TSLA.US","JPM.US","V.US","UNH.US"
]

daily_tickers = None
last_date = None

@app.get("/")
def root():
    return {"status": "ok", "mode": "daily_random_with_ranking"}

def fetch_eod(symbol: str):
    url = f"https://eodhd.com/api/eod/{symbol}?api_token={API_KEY}&fmt=json&limit=2"

    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        if isinstance(data, list) and len(data) >= 2:
            latest = data[0]
            prev = data[1]

            c = latest.get("close")
            pc = prev.get("close")

            if c is None or pc in (None, 0):
                return None

            change = (c - pc) / pc

            return {
                "ticker": symbol,
                "date": latest.get("date"),
                "close": c,
                "prev_close": pc,
                "change": change
            }
        return None
    except Exception:
        return None

@app.get("/eod")
def get_eod():
    global daily_tickers, last_date

    today = datetime.utcnow().date()

    if daily_tickers is None or last_date != today:
        daily_tickers = random.sample(POOL, 3)
        last_date = today

    results = []

    for ticker in daily_tickers:
        data = fetch_eod(ticker)
        if data:
            results.append(data)

    ranked = sorted(results, key=lambda x: x["change"], reverse=True)

    top = ranked[0] if ranked else None
    bottom = ranked[-1] if ranked else None

    return {
        "date": str(today),
        "tickers_selected": daily_tickers,
        "tickers_returned": len(results),
        "top": top,
        "bottom": bottom,
        "ranked": ranked
    }
