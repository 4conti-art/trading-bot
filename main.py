from fastapi import FastAPI
import json
import os
from datetime import datetime, timedelta
import pytz
import yfinance as yf
import numpy as np

app = FastAPI()

# =========================================================
# FILE PATHS
# =========================================================
PORTFOLIO_FILE = "portfolio.json"
CACHE_FILE = "signals_cache.json"
LAST_RUN_FILE = "last_run.json"
TICKERS_FILE = "tickers.txt"

# =========================================================
# CONFIGURATION
# =========================================================
TOP_N = 15

# constraints
MAX_PER_SECTOR_WEIGHT = 0.30

# turnover control
TURNOVER_PENALTY = 0.2

# time
NY_TZ = pytz.timezone("America/New_York")

# =========================================================
# LOAD / SAVE UTILITIES
# =========================================================
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

# =========================================================
# GLOBAL STATE
# =========================================================
PORTFOLIO = load_json(PORTFOLIO_FILE, {"cash": 10000, "positions": {}})
LAST_RUN = load_json(LAST_RUN_FILE, {"date": None})

# =========================================================
# MARKET TIMING
# =========================================================
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

# =========================================================
# SECTOR LOOKUP (CACHED)
# =========================================================
SECTOR_CACHE = {}

def get_sector(ticker):
    if ticker in SECTOR_CACHE:
        return SECTOR_CACHE[ticker]

    try:
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "UNKNOWN")
    except:
        sector = "UNKNOWN"

    SECTOR_CACHE[ticker] = sector
    return sector

# =========================================================
# DATA LAYER
# =========================================================
def fetch_returns(tickers, period="6mo"):
    """
    Fetch price data and convert to returns
    """
    if len(tickers) == 0:
        return None

    df = yf.download(tickers, period=period)["Close"]

    if isinstance(df, float) or df is None:
        return None

    returns = df.pct_change().dropna()

    return returns

# =========================================================
# SIGNAL GENERATION
# =========================================================
def compute_signal_scores(returns):
    """
    Simple momentum proxy: mean return
    """
    scores = returns.mean().sort_values(ascending=False)
    return scores

def select_top_assets(scores, n=TOP_N):
    """
    Select top N assets by score
    """
    top_assets = list(scores.index[:n])
    return top_assets

# =========================================================
# PORTFOLIO OPTIMIZER (INSTITUTIONAL STYLE)
# =========================================================
def compute_mean_variance_weights(returns_subset):
    """
    Core mean-variance solution (max Sharpe style)
    """
    mean_returns = returns_subset.mean().values
    cov_matrix = np.cov(returns_subset.values, rowvar=False)

    inv_cov = np.linalg.pinv(cov_matrix)

    raw_weights = inv_cov @ mean_returns

    # enforce long-only
    raw_weights = np.maximum(raw_weights, 0)

    if raw_weights.sum() == 0:
        weights = np.ones(len(raw_weights)) / len(raw_weights)
    else:
        weights = raw_weights / raw_weights.sum()

    return weights

def apply_turnover_penalty(new_weights, tickers):
    """
    Blend with current portfolio to reduce turnover
    """
    current_positions = PORTFOLIO.get("positions", {})

    current_vector = []
    for t in tickers:
        if t in current_positions:
            current_vector.append(1 / max(len(current_positions), 1))
        else:
            current_vector.append(0)

    current_vector = np.array(current_vector)

    adjusted_weights = (
        (1 - TURNOVER_PENALTY) * new_weights +
        TURNOVER_PENALTY * current_vector
    )

    return adjusted_weights

def apply_sector_constraints(weights, tickers):
    """
    Enforce sector caps
    """
    sector_map = {}

    # group indices by sector
    for i, t in enumerate(tickers):
        sector = get_sector(t)
        sector_map.setdefault(sector, []).append(i)

    weights = weights.copy()

    for sector, indices in sector_map.items():
        sector_weight = weights[indices].sum()

        if sector_weight > MAX_PER_SECTOR_WEIGHT:
            scale = MAX_PER_SECTOR_WEIGHT / sector_weight
            weights[indices] *= scale

    # renormalize
    total = weights.sum()
    if total > 0:
        weights = weights / total

    return weights

def optimize_portfolio(returns, tickers):
    """
    Full optimization pipeline
    """

    returns_subset = returns[tickers].dropna()

    if returns_subset.shape[1] == 0:
        return {}

    # 1. base optimizer
    base_weights = compute_mean_variance_weights(returns_subset)

    # 2. turnover control
    turnover_adjusted = apply_turnover_penalty(base_weights, tickers)

    # 3. sector constraints
    final_weights = apply_sector_constraints(turnover_adjusted, tickers)

    return dict(zip(tickers, final_weights))

# =========================================================
# FULL PIPELINE
# =========================================================
def build_portfolio():
    tickers = load_tickers()

    returns = fetch_returns(tickers)

    if returns is None or returns.empty:
        return {}

    # step 1: compute signals
    scores = compute_signal_scores(returns)

    # step 2: select top assets
    top_assets = select_top_assets(scores)

    # step 3: optimize weights
    weights = optimize_portfolio(returns, top_assets)

    return weights

# =========================================================
# ACTION GENERATION
# =========================================================
def generate_actions(target_weights):
    current_positions = PORTFOLIO.get("positions", {})

    actions = []

    # sells
    for ticker in current_positions:
        if ticker not in target_weights:
            actions.append({
                "ticker": ticker,
                "action": "SELL"
            })

    # buys
    for ticker, weight in target_weights.items():
        if ticker not in current_positions:
            actions.append({
                "ticker": ticker,
                "action": "BUY",
                "target_weight": weight
            })

    return actions

# =========================================================
# BACKTEST (ALIGNED WITH LIVE LOGIC)
# =========================================================
def run_backtest(days=120):
    tickers = load_tickers()

    price_data = yf.download(tickers, period="1y")["Close"]
    returns = price_data.pct_change().dropna()

    portfolio_value = 10000
    history = []

    for i in range(60, len(returns)):
        window = returns.iloc[:i]

        scores = compute_signal_scores(window)
        top_assets = select_top_assets(scores)

        weights = optimize_portfolio(window, top_assets)

        daily_returns = returns.iloc[i][top_assets].values
        weight_vector = np.array([weights[t] for t in top_assets])

        portfolio_return = np.dot(weight_vector, daily_returns)

        portfolio_value *= (1 + portfolio_return)

        history.append({
            "date": str(returns.index[i].date()),
            "value": float(portfolio_value)
        })

    return {
        "final_value": portfolio_value,
        "return": portfolio_value / 10000 - 1,
        "history": history
    }

# =========================================================
# EOD EXECUTION
# =========================================================
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

# =========================================================
# API
# =========================================================
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
    return run_backtest()