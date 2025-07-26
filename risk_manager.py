
import os
import requests

ALPACA_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = "https://paper-api.alpaca.markets"

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET
}

def place_trade(symbol, analysis):
    # Calculate position size (fixed $3000 per trade)
    price = get_latest_price(symbol)
    qty = int(3000 // price)

    order = {
        "symbol": symbol,
        "qty": qty,
        "side": "buy",
        "type": "market",
        "time_in_force": "gtc",
        "order_class": "bracket",
        "take_profit": {"limit_price": round(price * 1.10, 2)},
        "stop_loss": {
            "stop_price": round(price * 0.95, 2),
            "limit_price": round(price * 0.94, 2)
        }
    }

    res = requests.post(f"{BASE_URL}/v2/orders", json=order, headers=HEADERS)
    response = res.json()

    return {
        "filled_at": response.get("filled_at"),
        "qty": qty,
        "entry_price": price,
        "target": f"{round(price * 1.10, 2)}",
        "stop_loss": f"{round(price * 0.95, 2)}",
        "alpaca_response": response
    }

def get_latest_price(symbol):
    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/quotes/latest"
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET
    }
    res = requests.get(url, headers=headers)
    latest = res.json()
    return float(latest["quote"]["ap"])

