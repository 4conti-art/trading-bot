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
MAX_WEIGHT = 0.5

DATA = {}

# ✅ USER PORTFOLIO (PERSISTS IN MEMORY)
PORTFOLIO = {
    "cash": 10000,
    "positions": {},
    "history": []
}

# ----------------------------
# ✅ MARKET FILTER
# ----------------------------
def market_is_risk_on(spy_prices):
    if len(spy_prices) < 100:
        return True

    close = np.array(spy_prices)

    ma50 = np.mean(close[-50:])
    ma200 = np.mean(close[-100:])

    return close[-1] > ma50 and ma50 > ma200


# ----------------------------
# ✅ MOMENTUM
# ----------------------------
def compute_score(close):
    if len(close) < 61:
        return 0

    close = np.array(close)

    short = (close[-1] / close[-6]) - 1
    medium = (close[-1] / close[-21]) - 1
    long = (close[-1] / close[-61]) - 1

    momentum = 0.5 * short + 0.3 * medium + 0.2 * long

    log_returns = np.diff(np.log(close))
    vol = np.std(log_returns)

    if vol == 0 or np.isnan(vol):
        return 0

    ma50 = np.mean(close[-50:])
    if close[-1] < ma50:
        momentum *= 0.2

    score = momentum / (vol * 5)

    if np.isnan(score) or np.isinf(score):
        return 0

    return float(score)


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

    return generate_fallback()


# ----------------------------
# ✅ BOT SIGNALS ONLY (NO AUTO TRADING)
# ----------------------------
def build_portfolio(market):
    spy = market["SPY"]

    if not market_is_risk_on(spy):
        return [{"ticker": t, "signal": "CASH", "weight": 0} for t in TICKERS]

    results = []

    for t in TICKERS:
        score = compute_score(market[t])
        results.append({"ticker": t, "score": score})

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    buy = [r for r in results if r["score"] > 0.05]

    if not buy:
        return [{"ticker": t, "signal": "CASH", "weight": 0} for t in TICKERS]

    buy = buy[:3]

    total_score = sum(r["score"] for r in buy)

    for r in results:
        if r in buy:
            r["signal"] = "BUY"
            r["weight"] = r["score"] / total_score if total_score > 0 else 0
        else:
            r["signal"] = "HOLD"
            r["weight"] = 0

    for r in buy:
        r["weight"] = min(r["weight"], MAX_WEIGHT)

    norm = sum(r["weight"] for r in buy)
    if norm > 0:
        for r in buy:
            r["weight"] /= norm

    return results


# ----------------------------
# ✅ PORTFOLIO VALUE (USER CONTROLLED)
# ----------------------------
def get_prices(market):
    return {t: market[t][-1] for t in TICKERS}


def compute_portfolio_value(portfolio, prices):
    value = portfolio["cash"]

    for t, shares in portfolio["positions"].items():
        value += shares * prices.get(t, 0)

    return value


# ----------------------------
# ✅ PIPELINE (NO OVERWRITE)
# ----------------------------
def build_data():
    global DATA, PORTFOLIO

    market = get_data()

    signals = build_portfolio(market)
    prices = get_prices(market)

    # ✅ ONLY READ USER PORTFOLIO
    value = compute_portfolio_value(PORTFOLIO, prices)

    PORTFOLIO["history"].append(value)

    DATA = {
        "portfolio_value": value,
        "cash": PORTFOLIO["cash"],
        "positions": PORTFOLIO["positions"],
        "signals": signals
    }


def background_job():
    while True:
        build_data()
        time.sleep(86400)  # daily


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
    return {"status": "bot running"}


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
    return FileResponse("index.html")