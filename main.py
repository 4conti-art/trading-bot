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
# ✅ MARKET REGIME FILTER (NEW)
# ----------------------------
def market_is_risk_on(spy_prices):
    if len(spy_prices) < 100:
        return True

    close = np.array(spy_prices)

    ma50 = np.mean(close[-50:])
    ma200 = np.mean(close[-100:])

    # risk-on only if strong trend
    return close[-1] > ma50 and ma50 > ma200


# ----------------------------
# ✅ MOMENTUM + TREND
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

    # trend filter
    ma50 = np.mean(close[-50:])
    if close[-1] < ma50:
        momentum *= 0.2

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

    for t in TICKERS + ["SPY"]:
        prices = [100]
        for _ in range(150):
            drift = 0.0005
            noise = np.random.normal(0, 0.01)
            prices.append(prices[-1] * (1 + drift + noise))
        data[t] = prices[-150:]

    return data


# ----------------------------
# ✅ REAL DATA
# ----------------------------
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
        print("✅ REAL DATA")
        return real

    print("⚠️ FALLBACK DATA")
    return generate_fallback()


# ----------------------------
# ✅ PORTFOLIO ENGINE (DEFENSIVE)
# ----------------------------
def build_portfolio(market):
    spy = market["SPY"]

    # ✅ GLOBAL MARKET FILTER
    if not market_is_risk_on(spy):
        print("⚠️ RISK OFF → CASH")
        return [{"ticker": t, "signal": "CASH", "weight": 0} for t in TICKERS]

    results = []

    for t in TICKERS:
        score = compute_score(market[t])
        results.append({"ticker": t, "score": score})

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    # ✅ ONLY STRONG POSITIVE SIGNALS
    buy = [r for r in results if r["score"] > 0.05]

    if not buy:
        print("⚠️ NO STRONG SIGNALS → CASH")
        return [{"ticker": t, "signal": "CASH", "weight": 0} for t in TICKERS]

    # ✅ LIMIT POSITIONS (DEFENSIVE)
    buy = buy[:3]

    total_score = sum(r["score"] for r in buy)

    for r in results:
        if r in buy:
            r["signal"] = "BUY"
            r["weight"] = r["score"] / total_score if total_score > 0 else 0
        else:
            r["signal"] = "HOLD"
            r["weight"] = 0

    # ✅ CAP WEIGHTS
    for r in buy:
        r["weight"] = min(r["weight"], MAX_WEIGHT)

    # ✅ NORMALIZE
    norm = sum(r["weight"] for r in buy)
    if norm > 0:
        for r in buy:
            r["weight"] /= norm

    return results


# ----------------------------
# ✅ DRAWDOWN PROTECTION (STRONGER)
# ----------------------------
def apply_drawdown_control(portfolio):
    global EQUITY

    if len(EQUITY) < 5:
        return portfolio

    peak = max(EQUITY)
    current = EQUITY[-1]
    dd = (peak - current) / peak

    if dd > 0.08:
        print("🚨 HARD RISK OFF (DD > 8%)")
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

    # simulate equity (conservative)
    daily_return = sum(r["weight"] * 0.0005 for r in portfolio if r["signal"] == "BUY")
    EQUITY.append(EQUITY[-1] * (1 + daily_return))

    DATA = portfolio


def background_job():
    while True:
        build_data()
        time.sleep(604800)  # weekly


@app.on_event("startup")
def startup():
    build_data()

    thread = threading.Thread(target=background_job)
    thread.daemon = True
    thread.start()


@app.get("/")
def root():
    return {"status": "defensive bot running"}


@app.get("/top")
def top():
    return DATA