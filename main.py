def generate_fallback():
    # simple synthetic data (deterministic enough)
    data = {}
    for t in TICKERS:
        base = 100
        prices = [base]
        for i in range(60):
            prices.append(prices[-1] * (1 + 0.001))  # small drift
        data[t] = prices[-60:]
    return data


def fetch_data():
    data = {}

    for t in TICKERS:
        try:
            df = yf.download(t, period="6mo", interval="1d", progress=False)

            if df.empty:
                continue

            closes = df["Close"]
            closes = closes.squeeze()
            closes = closes.dropna().tolist()

            if len(closes) >= 60:
                data[t] = closes[-60:]

        except Exception as e:
            print(f"Error fetching {t}: {e}")

    # ✅ FALLBACK TRIGGER
    if len(data) < len(TICKERS):
        print("⚠️ Using fallback data")
        return generate_fallback()

    return data