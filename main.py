from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import numpy as np

# Optional data source
try:
    import yfinance as yf
    YF_AVAILABLE = True
except:
    YF_AVAILABLE = False

app = FastAPI()

TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "META"]

DATA = {}

# ✅ USER PORTFOLIO (PERSISTS WHILE APP RUNS)
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
# ✅ PRICES
# ----------------------------
def get_prices(market):
    prices = {}

    for t in TICKERS:
        if t in market and len(market[t]) > 0:
            prices[t] = market[t][-1]
        else:
            prices[t] = 100  # fallback

    return prices


# ----------------------------
# ✅ VALUE
# ----------------------------
def compute_portfolio_value():
    market = get_data()
    prices = get_prices(market)

    value = PORTFOLIO["cash"]

    for t, shares in PORTFOLIO["positions"].items():
        price = prices.get(t, 100)
        value += shares * price

    return value


# ----------------------------
# ✅ SIGNALS (STATIC FOR NOW)
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
# ✅ API
# ----------------------------
@app.get("/")
def root():
    return {"status": "running"}


@app.get("/portfolio")
def portfolio():
    value = compute_portfolio_value()

    return {
        "portfolio_value": value,
        "cash": PORTFOLIO["cash"],
        "positions": PORTFOLIO["positions"],
        "signals": build_signals()
    }


@app.post("/update_portfolio")
async def update_portfolio(request: Request):
    data = await request.json()

    PORTFOLIO["cash"] = data.get("cash", PORTFOLIO["cash"])
    PORTFOLIO["positions"] = data.get("positions", PORTFOLIO["positions"])

    print("✅ UPDATED PORTFOLIO:", PORTFOLIO)

    return {"status": "updated"}


@app.post("/reset")
def reset():
    PORTFOLIO["cash"] = 10000
    PORTFOLIO["positions"] = {}
    PORTFOLIO["history"] = []

    return {"status": "reset"}


@app.get("/dashboard")
def dashboard():
    return FileResponse("dashboard.html")