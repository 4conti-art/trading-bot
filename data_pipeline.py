import json
import random

OUTPUT_FILE = "signals.json"

UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META",
    "SPY", "QQQ", "GLD"
]

def run_pipeline():
    results = []

    for symbol in UNIVERSE:
        # ✅ simulate realistic scores
        score = random.uniform(0.5, 1.5)

        results.append({
            "ticker": symbol,
            "score": score
        })

        print(f"✅ {symbol}")

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f)

    print("\n✅ signals.json updated")


if __name__ == "__main__":
    run_pipeline()