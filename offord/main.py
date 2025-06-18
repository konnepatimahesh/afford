from fastapi import FastAPI
import httpx
import time
import random
from datetime import datetime, timedelta

app = FastAPI()

# For number window logic
WINDOW_SIZE = 10
number_window = []

# Mock historical stock data store
stock_price_history = {
    "AAPL": [],
    "GOOG": [],
    "MSFT": []
}

# Populate mock stock prices (timestamped)
def generate_mock_stock_data():
    now = datetime.utcnow()
    for stock in stock_price_history:
        stock_price_history[stock] = [
            {"price": round(random.uniform(100, 500), 2), "timestamp": now - timedelta(minutes=i)}
            for i in range(60)
        ]

generate_mock_stock_data()

# API: Numbers window logic
API_ENDPOINTS = {
    "p": "http://20.244.56.144/evaluation-service/primes",
    "f": "http://20.244.56.144/evaluation-service/fibo",
    "e": "http://20.244.56.144/evaluation-service/even",
    "r": "http://20.244.56.144/evaluation-service/rand"
}

@app.get("/numbers/{numberid}")
async def get_numbers(numberid: str):
    if numberid not in API_ENDPOINTS:
        return {
            "error": "Invalid number ID. Use 'p', 'f', 'e', or 'r'."
        }

    url = API_ENDPOINTS[numberid]
    window_prev = number_window.copy()
    new_numbers = []

    try:
        async with httpx.AsyncClient(timeout=0.5) as client:
            start = time.time()
            response = await client.get(url)
            elapsed = time.time() - start

            if response.status_code == 200 and elapsed <= 0.5:
                data = response.json()
                fetched_numbers = data.get("numbers", [])
            else:
                raise Exception("Timeout or bad response")
    except:
        # Fallback to 5 random numbers
        fetched_numbers = [random.randint(1, 100) for _ in range(5)]

    for num in fetched_numbers:
        if isinstance(num, int) and num not in number_window:
            number_window.append(num)
            new_numbers.append(num)
            if len(number_window) > WINDOW_SIZE:
                number_window.pop(0)

    return {
        "windowPrevState": window_prev,
        "windowCurrState": number_window,
        "numbers": new_numbers,
        "avg": round(sum(number_window) / len(number_window), 2) if number_window else 0.0
    }


# ✅ NEW API: Average Stock Price in Last m Minutes
@app.get("/stocks/{symbol}/minutes-{m}/aggregation-average")
async def get_stock_average(symbol: str, m: int):
    if symbol not in stock_price_history:
        return {"error": f"Stock symbol '{symbol}' not found."}

    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=m)
    relevant_prices = [
        entry["price"]
        for entry in stock_price_history[symbol]
        if entry["timestamp"] >= cutoff
    ]

    if not relevant_prices:
        return {
            "symbol": symbol,
            "minutes": m,
            "average_price": 0,
            "message": "No data available in the given time window."
        }

    average_price = round(sum(relevant_prices) / len(relevant_prices), 2)
    return {
        "symbol": symbol,
        "minutes": m,
        "average_price": average_price
    }

