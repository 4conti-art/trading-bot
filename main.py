import requests 
from fastapi import FastAPI 
 
app = FastAPI() 
 
API_KEY = "d79t519r01qspme61vogd79t519r01qspme61vp0" 
 
TICKERS = ["AAPL","MSFT","NVDA","AMZN","META"] 
 
def fetch_price(ticker): 
    url = "https://finnhub.io/api/v1/quote" 
    params = {"symbol": ticker, "token": API_KEY} 
    return requests.get(url, params=params).json() 
 
@app.get("/") 
def root(): 
    return {"status": "running"} 
 
@app.get("/top") 
def top(): 
    results = [] 
    for t in TICKERS: 
        d = fetch_price(t) 
        if "c" not in d or "pc" not in d: 
            continue 
        if d["pc"] == 0: 
            continue 
        change = (d["c"] - d["pc"]) / d["pc"] 
        results.append({"ticker": t, "price": d["c"], "score": change}) 
    return sorted(results, key=lambda x: x["score"], reverse=True) 
