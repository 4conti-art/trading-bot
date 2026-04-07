import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import date, datetime
import time

print("RUNNING: LEAN TEST VERSION")

app = FastAPI()

API_KEY = "d79t519r01qspme61vogd79t519r01qspme61vp0"

# Curated list of 10 big tickers
TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "JPM", "SPY", "QQQ"]

# --- In-memory daily cache ---
_cache = {
    "date": None,
    "movers": None,
    "report": None,
    "recommend": None,
}


def fetch_quote(ticker):
    url = "https://finnhub.io/api/v1/quote"
    params = {"symbol": ticker, "token": API_KEY}
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if "c" not in data or "pc" not in data or data["pc"] == 0:
            return None
        change = (data["c"] - data["pc"]) / data["pc"]
        return {"ticker": ticker, "price": data["c"], "change": change}
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


def get_top_movers():
    results = []
    for t in TICKERS:
        q = fetch_quote(t)
        if q:
            results.append(q)
        time.sleep(0.25)  # be gentle with rate limits
    if not results:
        return None
    return sorted(results, key=lambda x: abs(x["change"]), reverse=True)[:5]


def generate_report(movers):
    if not movers:
        return "No data available today."
    lines = [f"Daily Report — {date.today().isoformat()}", ""]
    for m in movers:
        direction = "UP" if m["change"] > 0 else "DOWN"
        lines.append(f"  {m['ticker']}: ${m['price']:.2f}  {direction} {abs(m['change'])*100:.2f}%")
    return "\n".join(lines)


def generate_recommendation(movers):
    if not movers:
        return None
    top = movers[0]  # biggest mover of the day
    action = "BUY" if top["change"] > 0 else "SELL"
    return {
        "ticker": top["ticker"],
        "action": action,
        "price": top["price"],
        "change_pct": round(abs(top["change"]) * 100, 2),
        "reason": f"Top mover of the day: {action} {top['ticker']} at ${top['price']:.2f}",
    }


# --- Routes ---

@app.get("/")
def root():
    return {"status": "ok", "version": "lean-test"}


@app.get("/movers")
def movers():
    today = str(date.today())
    if _cache["date"] != today or _cache["movers"] is None:
        _cache["date"] = today
        _cache["movers"] = get_top_movers()
    return JSONResponse(content=_cache["movers"] or {"error": "No data"})


@app.get("/report")
def report():
    today = str(date.today())
    if _cache["date"] != today or _cache["report"] is None:
        if _cache["movers"] is None or _cache["date"] != today:
            _cache["movers"] = get_top_movers()
            _cache["date"] = today
        _cache["report"] = generate_report(_cache["movers"])
    return JSONResponse(content={"report": _cache["report"]})


@app.get("/recommend")
def recommend():
    today = str(date.today())
    if _cache["date"] != today or _cache["recommend"] is None:
        if _cache["movers"] is None or _cache["date"] != today:
            _cache["movers"] = get_top_movers()
            _cache["date"] = today
        _cache["recommend"] = generate_recommendation(_cache["movers"])
    return JSONResponse(content=_cache["recommend"] or {"error": "No data"})
