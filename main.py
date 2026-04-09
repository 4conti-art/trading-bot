import requests 
from fastapi import FastAPI 
 
app = FastAPI() 
 
API_KEY = "d79t519r01qspme61vogd79t519r01qspme61vp0" 
 
@app.get("/") 
def root(): 
    return {"status": "running"} 
 
@app.get("/top") 
def top(): 
    url = "https://api.twelvedata.com/time_series" 
    params = {"symbol": "AAPL", "interval": "1day", "outputsize": 60, "apikey": API_KEY} 
    r = requests.get(url, params=params) 
    return r.json() 
