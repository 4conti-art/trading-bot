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
MIN_WEIGHT_THRESHOLD = 0.01  # 🔥 ignore tiny/zero weights

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

# ✅ RESTORED EOD LOGIC
def is_market_closed():
    now = datetime.now(NY_TZ)
    close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return now >= close

def should_run_today():
    today = datetime.now(NY_TZ).strftime("%Y-%m-%d")
    return LAST_RUN.get("date") != today and is_market_closed()

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

# 🔥 ROBUST DATA PIPELINE
def fetch_returns(tickers, period="6mo", batch_size=20):
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

    if prices.shape[1] == 0:
        return None

    returns = prices.pct_change().dropna()

    if returns.empty:
        return None

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

def apply_turnover_penalty(weights, tickers):
    current = PORTFOLIO.get("positions", {})

    curr_vec = []
    for t in tickers:
        if t in current:
            curr_vec.append(1 / max(len(current), 1))
        else:
            curr_vec.append(0)

    curr_vec = np.array(curr_vec)

    return (1 - TURNOVER_PENALTY)*weights + TURNOVER_PENALTY*curr_vec

def apply_sector_constraints(weights, tickers):
    sector_map = {}

    for i, t in enumerate(tickers):
        s = get_sector(t)
        sector_map.setdefault(s, []).append(i)

    for s, idx in sector_map.items():
        total = weights[idx].sum()
        if total > MAX_PER_SECTOR_WEIGHT:
            weights[idx] *= MAX_PER_SECTOR_WEIGHT / total

    return weights / weights.sum()

def optimize_portfolio(returns, tickers):
    subset = returns[tickers].dropna()

    if subset.shape[1] == 0:
        return {}

    w = compute_mean_variance_weights(subset)
    w = apply_turnover_penalty(w, tickers)
    w = apply_sector_constraints(w, tickers)

    return dict(zip(tickers, w))

def build_portfolio():
    tickers = load_tickers()

    returns = fetch_returns(tickers)

    if returns is None:
        return {}

    scores = compute_signal_scores(returns)
    top = select_top_assets(scores)

    weights = optimize_portfolio(returns, top)

    return weights

# 🔥 CLEAN ACTIONS (no zero-weight buys)
def generate_actions(weights):
    current = PORTFOLIO.get("positions", {})

    actions = []

    # SELL positions not in target OR too small
    for t in current:
        if t not in weights or weights.get(t, 0) < MIN_WEIGHT_THRESHOLD:
            actions.append({"ticker": t, "action": "SELL"})

    # BUY only meaningful weights
    for t, w in weights.items():
        if w >= MIN_WEIGHT_THRESHOLD and t not in current:
            actions.append({
                "ticker": t,
                "action": "BUY",
                "target_weight": w
            })

    return actions

def run_eod():
    if not should_run_today():
        return load_json(CACHE_FILE, {"status": "waiting"})

    weights = build_portfolio()
    actions = generate_actions(weights)

    output = {
        "date": datetime.now(NY_TZ).strftime("%Y-%m-%d"),
        "target_portfolio": weights,
        "actions": actions
    }

    save_json(CACHE_FILE, output)
    mark_run()

    return output

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/signals")
def signals():
    return load_json(CACHE_FILE, {"status": "no data"})

@app.get("/run")
def run():
    return run_eod()

@app.get("/backtest")
def backtest():
    return {"status": "not run yet"}