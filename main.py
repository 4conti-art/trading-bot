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

# --- NEW: state ---
current_position = None

@app.get("/")
def root():
    return {"status": "ok", "mode": "stateful_engine_v1"}

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
    global daily_tickers, last_date, current_position

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

    # --- STATEFUL DECISION LOGIC ---
    if current_position is None:
        # no position → can BUY
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
        # already holding something
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
        "ranked": ranked
    }
