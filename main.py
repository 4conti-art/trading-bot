from fastapi import FastAPI
import numpy as np
import threading
import time

app = FastAPI()

TICKERS = ["AAPL","MSFT","NVDA","AMZN","META"]
TOP_N = 2

DATA = []

# ✅ deterministic price series (no external dependency)
STATIC_DATA = {
    "AAPL": np.linspace(150, 180, 60),
    "MSFT": np.linspace(300, 280, 60),
    "NVDA": np.linspace(400, 460, 60),
    "AMZN": np.linspace(120, 170, 60),
    "META": np.linspace(250, 240, 60),
}


def compute_score(prices):
    close = np.array(prices)

    short = (close[-1] / close[-3]) - 1
    medium = (close[-1] / close[-7]) - 1

    momentum = 0.7 * short + 0.3 * medium

    log_returns = np.diff(np.log(close))
    volatility = np.std(log_returns)

    if volatility == 0 or np.isnan(volatility):
        return 0

    return momentum / (volatility * 5)


def build_data():
    global DATA

    results = []

    for t in TICKERS:
        prices = STATIC_DATA[t]
        score = compute_score(prices)

        results.append({
            "ticker": t,
            "score": float(score)
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    for i, r in enumerate(results):
        if i < TOP_N:
            r["signal"] = "BUY"
        elif i == len(results) - 1:
            r["signal"] = "SELL"
        else:
            r["signal"] = "HOLD"

    DATA = results


def background_job():
    while True:
        build_data()
        time.sleep(86400)


@app.on_event("startup")
def startup_event():
    build_data()  # ✅ immediate population (no empty state)
    thread = threading.Thread(target=background_job)
    thread.daemon = True
    thread.start()


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/top")
def top():
    return DATA