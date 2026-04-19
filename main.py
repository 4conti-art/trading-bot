from fastapi import FastAPI
import os
import yfinance as yf
import numpy as np
import pandas as pd

app = FastAPI()

TICKERS_FILE = "tickers.txt"

TOP_N = 15
MAX_SINGLE_POSITION = 0.15
TARGET_VOL = 0.20
MIN_CASH = 0.05

TRANSACTION_COST = 0.001

def load_tickers():
    if not os.path.exists(TICKERS_FILE):
        return []
    with open(TICKERS_FILE, "r") as f:
        return [t.strip().upper() for t in f if t.strip()]

def fetch_prices(tickers, period="2y", batch_size=20):
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

    return prices

# 🔥 SIGNAL (momentum)
def compute_signal_scores(prices):
    shifted = prices.shift(5)

    mom_3m = shifted.pct_change(63)
    mom_6m = shifted.pct_change(126)

    score = 0.5 * mom_3m.iloc[-1] + 0.5 * mom_6m.iloc[-1]

    return score.sort_values(ascending=False)

def select_top_assets(scores):
    return list(scores.index[:TOP_N])

def compute_weights(price_subset):
    returns = price_subset.pct_change().dropna()

    mean = returns.mean().values
    cov = np.cov(returns.values, rowvar=False)

    inv_cov = np.linalg.pinv(cov)
    w = inv_cov @ mean
    w = np.maximum(w, 0)

    if w.sum() == 0:
        w = np.ones(len(w)) / len(w)
    else:
        w = w / w.sum()

    port_vol = np.sqrt(w.T @ cov @ w) * np.sqrt(252)
    if port_vol > 0:
        w *= TARGET_VOL / port_vol

    w = np.minimum(w, MAX_SINGLE_POSITION)
    w = w / w.sum()

    return w

def build_portfolio(prices):
    scores = compute_signal_scores(prices)
    top = select_top_assets(scores)

    subset = prices[top].dropna()
    if subset.shape[1] == 0:
        return {}

    w = compute_weights(subset)
    w = w * (1 - MIN_CASH)

    return dict(zip(top, w))

def run_backtest():
    tickers = load_tickers()
    prices = fetch_prices(tickers)

    if prices is None:
        return {"error": "no data"}

    returns = prices.pct_change().dropna()

    portfolio_value = 10000
    prev_weights = None

    peak = portfolio_value
    max_drawdown = 0

    history = []

    for i in range(200, len(returns)):
        price_window = prices.iloc[:i]
        weights_dict = build_portfolio(price_window)

        if not weights_dict:
            continue

        tickers_now = list(weights_dict.keys())
        weights = np.array(list(weights_dict.values()))

        if prev_weights is not None:
            prev_vec = np.array([prev_weights.get(t, 0) for t in tickers_now])
            turnover = np.sum(np.abs(weights - prev_vec))
            cost = turnover * TRANSACTION_COST
        else:
            cost = 0

        daily_ret = returns.iloc[i][tickers_now].values
        port_ret = np.dot(weights, daily_ret)

        portfolio_value *= (1 + port_ret - cost)

        prev_weights = weights_dict

        peak = max(peak, portfolio_value)
        drawdown = (portfolio_value - peak) / peak
        max_drawdown = min(max_drawdown, drawdown)

        history.append({
            "date": str(returns.index[i].date()),
            "value": float(portfolio_value)
        })

    total_return = portfolio_value / 10000 - 1

    return {
        "final_value": portfolio_value,
        "return": total_return,
        "max_drawdown": max_drawdown,
        "history": history[-10:]
    }

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/backtest")
def backtest():
    return run_backtest()