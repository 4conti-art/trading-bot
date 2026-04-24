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
current_position = None

@app.get("/")
def root():
    return {"status": "ok", "mode": "stateful_engine_v2_robust"}

def fetch_eod(symbol: str):
    url = f"https://eodhd.com/api/eod/{symbol}?api_token={API_KEY}&fmt=json&limit=2"

    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        if not isinstance(data, list) or len(data) == 0:
            return {"ticker": symbol, "error": "no data"}

        latest = data[0]
        c = latest.get("close")

        if len(data) == 1:
            return {
                "ticker": symbol,
                "date": latest.get("date"),
                "close": c,
                "prev_close": None,
                "change": None
            }

        prev = data[1]
        pc = prev.get("close")

        if c is None or pc in (None, 0):
            return {
                "ticker": symbol,
                "error": "invalid price data"
            }

        change = (c - pc) / pc

        return {
            "ticker": symbol,
            "date": latest.get("date"),
            "close": c,
            "prev_close": pc,
            "change": change
        }

    except Exception as e:
        return {"ticker": symbol, "error": str(e)}

@app.get("/eod")
def get_eod():
    global daily_tickers, last_date, current_position

    today = datetime.utcnow().date()

    if daily_tickers is None or last_date != today:
        daily_tickers = random.sample(POOL, 3)
        last_date = today

    results = []
    errors = []

    for ticker in daily_tickers:
        data = fetch_eod(ticker)

        if data.get("error"):
            errors.append(data)
        else:
            results.append(data)

    ranked = sorted(
        [r for r in results if r.get("change") is not None],
        key=lambda x: x["change"],
        reverse=True
    )

    top = ranked[0] if ranked else None

    if current_position is None:
        if top and top["change"] > 0:
            current_position = top["ticker"]
            decision = {
                "action": "BUY",
                "ticker": current_position,
                "change": top["change"]
            }
        else:
            decision = {
                "action": "HOLD",
                "reason": "no positive momentum"
            }
    else:
        if not top or top["change"] <= 0:
            decision = {
                "action": "HOLD",
                "ticker": current_position,
                "reason": "holding, no better signal"
            }
        elif top["ticker"] == current_position:
            decision = {
                "action": "HOLD",
                "ticker": current_position,
                "reason": "still top performer"
            }
        else:
            decision = {
                "action": "ROTATE",
                "sell": current_position,
                "buy": top["ticker"],
                "change": top["change"]
            }
            current_position = top["ticker"]

    return {
        "date": str(today),
        "tickers_selected": daily_tickers,
        "current_position": current_position,
        "decision": decision,
        "ranked": ranked,
        "raw_results": results,
        "errors": errors
    }
