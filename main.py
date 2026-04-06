from fastapi import FastAPI

app = FastAPI()

# In-memory state (persists while app is running)
current_position = None


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/top")
def top():
    global current_position

    # State test only (no strategy logic yet)
    if current_position is None:
        current_position = "TEST"
        return {"state": "SET", "value": current_position}
    else:
        return {"state": "EXISTS", "value": current_position}
