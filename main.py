from fastapi import FastAPI

app = FastAPI()

# In-memory state (persists while app is running)
current_position = None


@app.get("/top")
def top():
    global current_position

    # TEMP: simple state test endpoint behavior
    if current_position is None:
        current_position = "TEST"
        return {"state": "SET", "value": current_position}
    else:
        return {"state": "EXISTS", "value": current_position}
