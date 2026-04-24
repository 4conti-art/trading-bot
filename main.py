import yfinance as yf
import random
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

POOL = [
    "AAPL","MSFT","NVDA","AMZN","META",
    "GOOGL","TSLA","JPM","V","UNH"
]

daily_tickers = None
last_date = None
current_position = None


@app.get("/")
def root():
    return {"status": "ok", "mode": "yfinance_skeleton"}


def fetch_eod(symbol: str):
    try:
        data = yf.Ticker(symbol).history(period="2d")

        if data is None or len(data) == 0:
            return {"ticker": symbol, "error": "no_data"}

        closes = data["Close"].tolist()

        if len(closes) < 2:
            return {
                "ticker": symbol,
                "close": closes[-1],
                "prev_close": None,
                "change": None
            }

        c = closes[-1]
        pc = closes[-2]

        if pc == 0:
            return {"ticker": symbol, "error": "bad_price"}

        change = (c - pc) / pc

        return {
            "ticker": symbol,
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

    # --- decision logic ---
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
                "ticker": current_position
            }
        elif top["ticker"] == current_position:
            decision = {
                "action": "HOLD",
                "ticker": current_position
            }
        else:
            decision = {
                "action": "ROTATE",
                "sell": current_position,
                "buy": top["ticker"]
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