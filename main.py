from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import json
import os

app = FastAPI()

TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "META"]
FILE = "portfolio.json"

# ✅ LOAD / SAVE
def load_portfolio():
    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            return json.load(f)
    return {"cash": 10000, "positions": {}, "history": []}


def save_portfolio(p):
    with open(FILE, "w") as f:
        json.dump(p, f)


PORTFOLIO = load_portfolio()

# ✅ FIXED PRICE MODEL (NO RANDOMNESS)
PRICE = 100

def compute_value():
    value = PORTFOLIO["cash"]

    for t, shares in PORTFOLIO["positions"].items():
        value += shares * PRICE

    return value


def build_data():
    return {
        "portfolio_value": compute_value(),
        "cash": PORTFOLIO["cash"],
        "positions": PORTFOLIO["positions"],
        "signals": [
            {"ticker": "AAPL", "signal": "BUY"},
            {"ticker": "MSFT", "signal": "BUY"},
            {"ticker": "NVDA", "signal": "HOLD"},
            {"ticker": "AMZN", "signal": "HOLD"},
            {"ticker": "META", "signal": "HOLD"},
        ]
    }


# ✅ API
@app.get("/portfolio")
def portfolio():
    return build_data()


@app.post("/update_portfolio")
async def update_portfolio(request: Request):
    global PORTFOLIO

    data = await request.json()

    PORTFOLIO["cash"] = data.get("cash", PORTFOLIO["cash"])
    PORTFOLIO["positions"] = data.get("positions", PORTFOLIO["positions"])

    save_portfolio(PORTFOLIO)

    print("✅ SAVED:", PORTFOLIO)

    return {"status": "updated"}


@app.get("/dashboard")
def dashboard():
    return FileResponse("dashboard.html")