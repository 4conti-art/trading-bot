from fastapi import FastAPI
import json
import os
from datetime import datetime
import pytz
import yfinance as yf
import numpy as np
import pandas as pd

app = FastAPI()

PORTFOLIO_FILE = "portfolio.json"
CACHE_FILE = "signals_cache.json"
LAST_RUN_FILE = "last_run.json"
TICKERS_FILE = "tickers.txt"

TOP_N = 15
MAX_PER_SECTOR_WEIGHT = 0.30
TURNOVER_PENALTY = 0.2
MIN_WEIGHT_THRESHOLD = 0.01

MAX_SINGLE_POSITION = 0.15
TARGET_VOL = 0.20
MIN_CASH = 0.05

NY_TZ = pytz.timezone("America/New_York")

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_tickers():
    if not os.path.exists(TICKERS_FILE):
        return []
    with open(TICKERS_FILE, "r") as f:
        return [t.strip().upper() for t in f if t.strip()]

PORTFOLIO = load_json(PORTFOLIO_FILE, {"cash": 10000, "positions": {}})
LAST_RUN = load_json(LAST_RUN_FILE, {"date": None})

# 🔥 force run (testing)
def should_run_today():
    return True

def mark_run():
    LAST_RUN["date"] = datetime.now(NY_TZ).strftime("%Y-%m-%d")
    save_json(LAST_RUN_FILE, LAST_RUN)

SECTOR_CACHE = {}

def get_sector(ticker):
    if ticker in SECTOR_CACHE:
        return SECTOR_CACHE[ticker]
    try:
        s = yf.Ticker(ticker).info.get("sector", "UNKNOWN")
    except:
        s = "UNKNOWN"
    SECTOR_CACHE[ticker] = s
    return s

def fetch_returns(tickers, period="2y", batch_size=20):
    all_prices = []

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]

        try:
            df = yf.download(batch, period=period, progress=False)

            if df is None or df.empty:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df = df["Close"]
            else:
                df = df[["Close"]]
                df.columns = batch

            all_prices.append(df)

        except:
            continue

    if not all_prices:
        return None

    prices = pd.concat(all_prices, axis=1)
    prices = prices.ffill()
    prices = prices.dropna(axis=1, thresh=int(len(prices)*0.5))

    returns = prices.pct_change().dropna()

    return returns

def compute_signal_scores(returns):
    return returns.mean().sort_values(ascending=False)

def select_top_assets(scores, n=TOP_N):
    return list(scores.index[:n])

def compute_mean_variance_weights(returns_subset):
    mean = returns_subset.mean().values
    cov = np.cov(returns_subset.values, rowvar=False)

    inv_cov = np.linalg.pinv(cov)
    w = inv_cov @ mean
    w = np.maximum(w, 0)

    if w.sum() == 0:
        return np.ones(len(w)) / len(w)

    return w / w.sum()

def apply_volatility_target(weights, returns_subset):
    cov = np.cov(returns_subset.values, rowvar=False)
    port_vol = np.sqrt(weights.T @ cov @ weights) * np.sqrt(252)

    if port_vol == 0:
        return weights

    return weights * (TARGET_VOL / port_vol)

def apply_position_caps(weights):
    weights = np.minimum(weights, MAX_SINGLE_POSITION)
    return weights / weights.sum()

def apply_turnover_penalty(weights, tickers):
    return weights  # ignore in backtest for now

def apply_sector_constraints(weights, tickers):
    return weights

def optimize_portfolio(returns, tickers):
    subset = returns[tickers].dropna()

    if subset.shape[1] == 0:
        return {}

    w = compute_mean_variance_weights(subset)
    w = apply_volatility_target(w, subset)
    w = apply_position_caps(w)

    return dict(zip(tickers, w))

def build_portfolio(returns):
    scores = compute_signal_scores(returns)
    top = select_top_assets(scores)
    weights = optimize_portfolio(returns, top)
    weights = {k: v * (1 - MIN_CASH) for k, v in weights.items()}
    return weights

# 🔥 BACKTEST ENGINE
def run_backtest():
    tickers = load_tickers()
    returns = fetch_returns(tickers)

    if returns is None:
        return {"error": "no data"}

    portfolio_value = 10000
    history = []

    for i in range(60, len(returns)):
        window = returns.iloc[:i]

        weights = build_portfolio(window)

        if not weights:
            continue

        daily_ret = returns.iloc[i][list(weights.keys())]
        w = np.array(list(weights.values()))

        portfolio_return = np.dot(w, daily_ret)

        portfolio_value *= (1 + portfolio_return)

        history.append({
            "date": str(returns.index[i].date()),
            "value": float(portfolio_value)
        })

    return {
        "final_value": portfolio_value,
        "return": portfolio_value / 10000 - 1,
        "history": history[-10:]
    }

def run_eod():
    weights = build_portfolio(fetch_returns(load_tickers()))

    return {
        "date": datetime.now(NY_TZ).strftime("%Y-%m-%d"),
        "target_portfolio": weights
    }

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/run")
def run():
    return run_eod()

@app.get("/backtest")
def backtest():
    return run_backtest()