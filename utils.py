


import os
import requests

def send_trade_to_alpaca(symbol, notional, client_order_id):
    api_key = os.getenv("APCA_API_KEY_ID")
    api_secret = os.getenv("APCA_API_SECRET_KEY")
    base_url = "https://paper-api.alpaca.markets"

    url = f"{base_url}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "Content-Type": "application/json"
    }
    order_data = {
        "symbol": symbol,
        "notional": notional,
        "side": "buy",
        "type": "market",
        "time_in_force": "day",
        "client_order_id": client_order_id
    }

    response = requests.post(url, json=order_data, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {
            "error": True,
            "status": response.status_code,
            "response": response.text
        }
