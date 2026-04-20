import numpy as np
import pandas as pd
from fastapi import FastAPI
import yfinance as yf
import json
import os

app = FastAPI()

TICKERS_FILE = "tickers.txt"

# -----------------------------
# Helpers
# -----------------------------
def load_tickers():
    with open(TICKERS_FILE, "r") as f:
        return [t.strip() for t in f.readlines()]

def fetch_data(tickers, start="2015-01-01"):
    data = yf.download(tickers, start=start)["Adj Close"]
    return data.dropna(axis=1, how="all")

# -----------------------------
# SIGNAL
# -----------------------------
def compute_signal(prices):
    returns = prices.pct_change()

    mom_3m = prices.pct_change(63).shift(1)
    mom_6m = prices.pct_change(126).shift(1)

    momentum = (mom_3m + mom_6m) / 2

    momentum_z = momentum.sub(momentum.mean(axis=1), axis=0)
    momentum_z = momentum_z.div(momentum.std(axis=1), axis=0)

    vol = returns.rolling(63).std() * np.sqrt(252)

    signal = momentum_z - vol

    return signal

# -----------------------------
# PORTFOLIO (UPDATED)
# -----------------------------
def construct_portfolio(signal, returns):
    latest = signal.iloc[-1]

    ranked = latest.dropna().sort_values(ascending=False)
    selected = ranked.index[:10]

    if len(selected) == 0:
        return pd.Series(dtype=float)

    sub_returns = returns[selected].fillna(0)

    cov = sub_returns.cov()
    cov += np.eye(len(cov)) * 1e-5

    inv_cov = np.linalg.pinv(cov.values)

    ones = np.ones(len(selected))
    weights = inv_cov @ ones

    # ✅ NEW: sanitize weights
    if np.isnan(weights).any() or abs(weights.sum()) < 1e-8:
        weights = np.ones(len(selected)) / len(selected)
    else:
        weights = weights / weights.sum()

    weights = pd.Series(weights, index=selected)

    return weights

# -----------------------------
# BACKTEST
# -----------------------------
def backtest(prices):
    returns = prices.pct_change().dropna()
    signal = compute_signal(prices)

    portfolio_returns = []

    for i in range(252, len(prices) - 1):
        window_prices = prices.iloc[:i]
        window_returns = returns.iloc[:i]

        sig = compute_signal(window_prices)
        weights = construct_portfolio(sig, window_returns)

        if len(weights) == 0:
            portfolio_returns.append(0)
            continue

        next_ret = returns.iloc[i + 1].reindex(weights.index).fillna(0)

        port_ret = (weights * next_ret).sum()

        portfolio_returns.append(port_ret)

    portfolio_returns = pd.Series(portfolio_returns)

    total_return = (1 + portfolio_returns).prod() - 1
    drawdown = (portfolio_returns.cumsum() - portfolio_returns.cumsum().cummax()).min()

    return {
        "return": float(total_return),
        "drawdown": float(drawdown)
    }

# -----------------------------
# API
# -----------------------------
@app.get("/")
def health():
    return {"status": "ok"}

@app.get("/backtest")
def run_backtest():
    tickers = load_tickers()
    prices = fetch_data(tickers)

    results = backtest(prices)

    return results