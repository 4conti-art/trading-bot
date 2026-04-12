from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import json
import os

# ✅ IMPORT PIPELINE
from data_pipeline import get_top_picks

app = FastAPI()

TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "META"]
FILE = "portfolio.json"

# ----------------------------
# ✅ LOAD / SAVE (SAFE EVEN IF RESETS)
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
# ✅ VALUE (SIMPLE)
# ----------------------------
PRICE = 100

def compute_value():
    value = PORTFOLIO["cash"]

    for t, shares in PORTFOLIO["positions"].items():
        value += shares * PRICE

    return value


# ----------------------------
# ✅ BUILD DATA (NOW WITH SIGNALS)
# ----------------------------
def build_data():
    # ✅ GET REAL RANKED PICKS
    picks = get_top_picks(10)

    signals = []

    for p in picks:
        signals.append({
            "ticker": p["symbol"],
            "score": round(p["score"], 3),
            "price": round(p["price"], 2)
        })

    return {
        "portfolio_value": compute_value(),
        "cash": PORTFOLIO["cash"],
        "positions": PORTFOLIO["positions"],
        "signals": signals
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