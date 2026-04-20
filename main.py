import numpy as np
import pandas as pd
from fastapi import FastAPI
import yfinance as yf

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
# BACKTEST (DEBUG VERSION)
# -----------------------------
def backtest(prices):
    returns = prices.pct_change().dropna()

    portfolio_returns = []

    for i in range(252, len(prices) - 1):
        window_returns = returns.iloc[:i]

        # ✅ DEBUG: force equal weights
        cols = window_returns.columns[:10]
        weights = pd.Series(1 / len(cols), index=cols)

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