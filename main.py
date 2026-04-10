from fastapi import FastAPI
import numpy as np

app = FastAPI()

TICKERS = ["AAPL","MSFT","NVDA","AMZN","META"]

TOP_N = 2

# ✅ STATIC MOCK DATA (stable, no API dependency)
DATA = {
    "AAPL": np.linspace(150, 180, 60),
    "MSFT": np.linspace(300, 290, 60),
    "NVDA": np.linspace(400, 450, 60),
    "AMZN": np.linspace(120, 160, 60),
    "META": np.linspace(250, 280, 60),
}


def compute_score(prices):
    close = np.array(prices)

    short = (close[-1] / close[-5]) - 1
    medium = (close[-1] / close[-15]) - 1

    momentum = 0.7 * short + 0.3 * medium

    log_returns = np.diff(np.log(close))
    volatility = np.std(log_returns)

    if volatility == 0:
        return None

    return momentum / volatility


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/top")
def top():
    results = []

    for t in TICKERS:
        prices = DATA[t]
        score = compute_score(prices)

        if score is None:
            continue

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

    return results