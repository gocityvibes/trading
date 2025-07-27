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


import json
from datetime import datetime

def log_trade(symbol, gpt35_score, gpt4o_score, expected_price, fill_price):
    log_entry = {
        "symbol": symbol,
        "timestamp": datetime.utcnow().isoformat(),
        "gpt_3_5_score": gpt35_score,
        "gpt_4o_score": gpt4o_score,
        "expected_price": expected_price,
        "fill_price": fill_price,
        "slippage_pct": round(((fill_price - expected_price) / expected_price) * 100, 2) if expected_price else None
    }

    try:
        with open("trade_log.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    data.append(log_entry)

    with open("trade_log.json", "w") as f:
        json.dump(data, f, indent=2)


import csv
import os

def close_trade_with_outcome(symbol, fill_price, exit_price):
    try:
        with open("trade_log.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return

    for entry in reversed(data):
        if entry["symbol"] == symbol and "exit_price" not in entry:
            entry["exit_price"] = exit_price
            entry["outcome"] = "WIN" if exit_price > fill_price else "LOSS"
            break

    with open("trade_log.json", "w") as f:
        json.dump(data, f, indent=2)

def export_log_to_csv():
    try:
        with open("trade_log.json", "r") as f:
            data = json.load(f)
    except Exception:
        return None

    fieldnames = ["symbol", "timestamp", "gpt_3_5_score", "gpt_4o_score", "expected_price", "fill_price", "slippage_pct", "exit_price", "outcome"]
    csv_path = "trade_log.csv"

    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

    return csv_path
