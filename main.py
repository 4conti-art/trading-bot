from fastapi import FastAPI
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

DATA = []
EQUITY = [1.0]


# ----------------------------
# ✅ MOMENTUM + TREND + VOL
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

    # ✅ Trend filter
    ma = np.mean(close[-50:])
    if close[-1] < ma:
        momentum *= 0.3

    score = momentum / (vol * 5)

    if np.isnan(score) or np.isinf(score):
        return 0

    return float(score)


# ----------------------------
# ✅ FALLBACK DATA
# ----------------------------
def generate_fallback():
    data = {}
    np.random.seed(42)

    for t in TICKERS:
        prices = [100]
        for _ in range(120):
            drift = 0.0008
            noise = np.random.normal(0, 0.01)
            prices.append(prices[-1] * (1 + drift + noise))
        data[t] = prices[-120:]

    return data


# ----------------------------
# ✅ REAL DATA (OPTIONAL)
# ----------------------------
def fetch_real_data():
    if not YF_AVAILABLE:
        return {}

    data = {}

    for t in TICKERS:
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

    if len(real) == len(TICKERS):
        print("✅ REAL DATA")
        return real

    print("⚠️ FALLBACK DATA")
    return generate_fallback()


# ----------------------------
# ✅ PORTFOLIO ENGINE
# ----------------------------
def build_portfolio(market):
    results = []

    for t in market:
        score = compute_score(market[t])
        results.append({"ticker": t, "score": score})

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    # ✅ Only positive scores
    buy = [r for r in results if r["score"] > 0]

    if not buy:
        return [{"ticker": r["ticker"], "signal": "CASH", "weight": 0} for r in results]

    # ✅ Dynamic top-N
    buy = buy[: min(5, len(buy))]

    total_score = sum(r["score"] for r in buy)

    for r in results:
        if r in buy:
            r["signal"] = "BUY"
            r["weight"] = r["score"] / total_score if total_score > 0 else 0
        else:
            r["signal"] = "HOLD"
            r["weight"] = 0

    # ✅ Cap weights
    excess = 0
    for r in buy:
        if r["weight"] > MAX_WEIGHT:
            excess += r["weight"] - MAX_WEIGHT
            r["weight"] = MAX_WEIGHT

    remaining = [r for r in buy if r["weight"] < MAX_WEIGHT]

    if remaining and excess > 0:
        rem_total = sum(r["weight"] for r in remaining)
        for r in remaining:
            r["weight"] += excess * (r["weight"] / rem_total)

    # ✅ Normalize
    norm = sum(r["weight"] for r in buy)
    if norm > 0:
        for r in buy:
            r["weight"] /= norm

    return results


# ----------------------------
# ✅ DRAWDOWN CONTROL
# ----------------------------
def apply_drawdown_control(portfolio):
    global EQUITY

    if len(EQUITY) < 2:
        return portfolio

    peak = max(EQUITY)
    current = EQUITY[-1]
    dd = (peak - current) / peak

    if dd > 0.10:
        print("⚠️ DRAWDOWN PROTECTION ACTIVE")
        return [{"ticker": r["ticker"], "signal": "CASH", "weight": 0} for r in portfolio]

    return portfolio


# ----------------------------
# ✅ PIPELINE
# ----------------------------
def build_data():
    global DATA, EQUITY

    market = get_data()
    portfolio = build_portfolio(market)
    portfolio = apply_drawdown_control(portfolio)

    # ✅ simulate equity (simple)
    daily_return = sum(r["weight"] * 0.001 for r in portfolio if r["signal"] == "BUY")
    EQUITY.append(EQUITY[-1] * (1 + daily_return))

    DATA = portfolio


def background_job():
    while True:
        build_data()
        time.sleep(604800)  # ✅ weekly


@app.on_event("startup")
def startup():
    build_data()

    thread = threading.Thread(target=background_job)
    thread.daemon = True
    thread.start()


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/top")
def top():
    return DATA