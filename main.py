from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import numpy as np
import threading
import time

# Optional data source
try:
    import yfinance as yf
    YF_AVAILABLE = True
except:
    YF_AVAILABLE = False

app = FastAPI()

TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "META"]

DATA = {}

# ✅ USER PORTFOLIO
PORTFOLIO = {
    "cash": 10000,
    "positions": {},
    "history": []
}

# ----------------------------
# ✅ DATA
# ----------------------------
def generate_fallback():
    data = {}
    np.random.seed(42)

    for t in TICKERS + ["SPY"]:
        prices = [100]
        for _ in range(150):
            drift = 0.0005
            noise = np.random.normal(0, 0.01)
            prices.append(prices[-1] * (1 + drift + noise))
        data[t] = prices[-150:]

    return data


def fetch_real_data():
    if not YF_AVAILABLE:
        return {}

    data = {}

    for t in TICKERS + ["SPY"]:
        try:
            df = yf.download(t, period="1y", interval="1d", progress=False)

            if df is None or df.empty:
                continue

            closes = df["Close"].dropna().tolist()

            if len(closes) >= 120:
                data[t] = closes[-120:]

        except Exception as e:
            print(f"Fetch failed {t}: {e}")

    return data


def get_data():
    real = fetch_real_data()

    if len(real) == len(TICKERS) + 1:
        return real

    print("⚠️ Using fallback data")
    return generate_fallback()


# ----------------------------
# ✅ PRICES (FIXED)
# ----------------------------
def get_prices(market):
    prices = {}

    for t in TICKERS:
        if t in market and len(market[t]) > 0:
            prices[t] = market[t][-1]
        else:
            prices[t] = 100  # ✅ fallback price

    return prices


# ----------------------------
# ✅ VALUE (WITH DEBUG)
# ----------------------------
def compute_portfolio_value(portfolio, prices):
    value = portfolio["cash"]

    for t, shares in portfolio["positions"].items():
        price = prices.get(t, 0)
        print(f"{t}: shares={shares}, price={price}")  # DEBUG

        value += shares * price

    print("TOTAL VALUE:", value)

    return value


# ----------------------------
# ✅ SIMPLE SIGNALS (placeholder)
# ----------------------------
def build_signals():
    return [
        {"ticker": "AAPL", "signal": "BUY", "weight": 0.5},
        {"ticker": "MSFT", "signal": "BUY", "weight": 0.5},
        {"ticker": "NVDA", "signal": "HOLD", "weight": 0},
        {"ticker": "AMZN", "signal": "HOLD", "weight": 0},
        {"ticker": "META", "signal": "HOLD", "weight": 0},
    ]


# ----------------------------
# ✅ PIPELINE
# ----------------------------
def build_data():
    global DATA, PORTFOLIO

    market = get_data()
    prices = get_prices(market)

    value = compute_portfolio_value(PORTFOLIO, prices)

    PORTFOLIO["history"].append(value)

    DATA = {
        "portfolio_value": value,
        "cash": PORTFOLIO["cash"],
        "positions": PORTFOLIO["positions"],
        "signals": build_signals()
    }


def background_job():
    while True:
        build_data()
        time.sleep(86400)


@app.on_event("startup")
def startup():
    build_data()

    thread = threading.Thread(target=background_job)
    thread.daemon = True
    thread.start()


# ----------------------------
# ✅ API
# ----------------------------
@app.get("/")
def root():
    return {"status": "running"}


@app.get("/portfolio")
def portfolio():
    return DATA


@app.post("/reset")
def reset():
    global PORTFOLIO
    PORTFOLIO = {
        "cash": 10000,
        "positions": {},
        "history": []
    }
    return {"status": "reset"}


@app.post("/update_portfolio")
async def update_portfolio(request: Request):
    global PORTFOLIO

    data = await request.json()

    PORTFOLIO["cash"] = data.get("cash", PORTFOLIO["cash"])
    PORTFOLIO["positions"] = data.get("positions", PORTFOLIO["positions"])

    print("✅ UPDATED PORTFOLIO:", PORTFOLIO)

    return {"status": "updated"}


@app.get("/dashboard")
def dashboard():
    return FileResponse("dashboard.html")