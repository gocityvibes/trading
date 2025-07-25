
import os
import openai
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread
import time
from alpaca_trade_api.rest import REST, TimeFrame

# ENV VARS
ALPACA_KEY = os.getenv("ALPACA_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

# APP SETUP
app = Flask(__name__)
CORS(app, origins=["https://subtle-twilight-946787.netlify.app", "https://tradetestbot.netlify.app"])

# STATE
trading_active = False
trade_log_data = []

# BACKGROUND BOT
def run_trading_loop():
    global trading_active, trade_log_data
    while trading_active:
        try:
            positions = alpaca.list_positions()
            account = alpaca.get_account()
            trade_log_data.append({
                "ticker": "AAPL",
                "score": 95,
                "entry": 189.5,
                "exit": 192.2,
                "equity": float(account.equity)
            })
        except Exception as e:
            trade_log_data.append({"error": str(e)})
        time.sleep(60)  # Check every 60 seconds

# ROUTES
@app.route("/start", methods=["POST"])
def start_trading():
    global trading_active
    if not trading_active:
        trading_active = True
        Thread(target=run_trading_loop).start()
        return jsonify({"status": "started"})
    return jsonify({"status": "already running"})

@app.route("/stop", methods=["POST"])
def stop_trading():
    global trading_active
    trading_active = False
    return jsonify({"status": "stopped"})

@app.route("/trade-log")
def trade_log():
    return jsonify({
        "status": "success",
        "trades": trade_log_data
    })

@app.route("/trade")
def trade_info():
    try:
        positions = alpaca.list_positions()
        account = alpaca.get_account()
        return jsonify({
            "positions": [p.symbol for p in positions],
            "equity": account.equity
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run()
