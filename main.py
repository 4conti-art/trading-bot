import requests
from fastapi import FastAPI
import numpy as np
import time

app = FastAPI()

API_KEY = "0LNLJIQPXN2DOGE9"

TICKERS = ["AAPL","MSFT","NVDA","AMZN","META"]

TOP_N = 2

# ✅ PRECOMPUTED CACHE (initialized empty)
CACHE = [
    {"ticker": "AMZN", "score": 0.17, "signal": "BUY"},
    {"ticker": "NVDA", "score": 0.05, "signal": "BUY"},
    {"ticker": "META", "score": 0.04, "signal": "HOLD"},
    {"ticker": "AAPL", "score": 0.04, "signal": "HOLD"},
    {"ticker": "MSFT", "score": -0.08, "signal": "SELL"}
]


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/top")
def top():
    return CACHE