import os
import openai
import requests
from alpaca_trade_api.rest import REST, TimeFrame
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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