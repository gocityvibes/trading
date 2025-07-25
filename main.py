import os
import openai
import requests
from alpaca_trade_api.rest import REST, TimeFrame
from flask import Flask, jsonify

app = Flask(__name__)

ALPACA_KEY = os.getenv("ALPACA_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY
alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

@app.route("/trade")
def trade():
    try:
        positions = alpaca.list_positions()
        account = alpaca.get_account()
        return jsonify({"positions": [p.symbol for p in positions], "equity": account.equity})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/log")
def get_trade_log():
    return jsonify({"log": "Sample trade log. GPT filters go here."})

@app.get("/trade-log")
async def trade_log():
    return {"log": trade_log_data}  # Replace with real log source

@app.post("/start")
async def start_bot():
    global bot_running
    bot_running = True
    return {"message": "Bot started"}

@app.post("/stop")
async def stop_bot():
    global bot_running
    bot_running = False
    return {"message": "Bot stopped"}
