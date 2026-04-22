import requests
from fastapi import FastAPI

app = FastAPI()

API_KEY = "69e8cdc7e8f9d9.44028983"

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/eod")
def get_bulk_eod():
    url = f"https://eodhd.com/api/eod-bulk-last-day/US?api_token={API_KEY}&fmt=json"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        sample = data[:50] if isinstance(data, list) else []

        return {
            "total_received": len(data) if isinstance(data, list) else 0,
            "sample": sample
        }

    except Exception as e:
        return {"error": str(e)}
