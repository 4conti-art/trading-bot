from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import json
import os

app = FastAPI()

FILE = "portfolio.json"

# ----------------------------
# ✅ LOAD / SAVE
# ----------------------------
def load_portfolio():
    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            return json.load(f)
    return {"cash": 10000, "positions": {}}


def save_portfolio(p):
    with open(FILE, "w") as f:
        json.dump(p, f)


PORTFOLIO = load_portfolio()

# ----------------------------
# ✅ VALUE
# ----------------------------
PRICE = 100

def compute_value():
    value = PORTFOLIO["cash"]
    for t, shares in PORTFOLIO["positions"].items():
        value += shares * PRICE
    return value

# ----------------------------
# ✅ STATIC SIGNALS (SAFE MODE)
# ----------------------------
def get_signals():
    return [
        {"ticker": "AAPL", "score": 1.0},
        {"ticker": "MSFT", "score": 0.9},
        {"ticker": "NVDA", "score": 0.85},
        {"ticker": "GLD", "score": 0.8},
        {"ticker": "DBC", "score": 0.75},
    ]

# ----------------------------
# ✅ BUILD DATA
# ----------------------------
def build_data():
    return {
        "portfolio_value": compute_value(),
        "cash": PORTFOLIO["cash"],
        "positions": PORTFOLIO["positions"],
        "signals": get_signals()
    }

# ----------------------------
# ✅ API
# ----------------------------
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

    return {"status": "updated"}


@app.get("/dashboard")
def dashboard():
    return FileResponse("dashboard.html")