def format_order_id(symbol, score, flags):
    return f"{symbol}_score{score}_{flags}"

from datetime import datetime, time

def within_trading_hours():
    now = datetime.utcnow().time()
    market_open = time(13, 31)   # 9:31 AM ET
    last_entry = time(19, 0)     # 3:00 PM ET
    return market_open <= now <= last_entry

def should_flatten_positions():
    now = datetime.utcnow().time()
    flatten_cutoff = time(19, 45)  # 3:45 PM ET
    return now >= flatten_cutoff

import os
import time
import requests
import openai
import alpaca_trade_api as tradeapi
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# API Keys
TAAPI_API_KEY = os.getenv("TAAPI_API_KEY")
GPT_API_KEY = os.getenv("OPENAI_API_KEY")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

openai.api_key = GPT_API_KEY
api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL, api_version='v2')

# Bot status
bot_active = False

@app.route("/start", methods=["POST"])
def start_bot():
    global bot_active
    bot_active = True
    return jsonify({"status": "started"})

@app.route("/stop", methods=["POST"])
def stop_bot():
    global bot_active
    bot_active = False
    return jsonify({"status": "stopped"})

@app.route("/indicators/<symbol>", methods=["GET"])
def get_indicators(symbol):
    interval = "1h"
    TAAPI_BASE = "https://api.taapi.io"

    def fetch(endpoint, params={}):
        params.update({
            "secret": TAAPI_API_KEY,
            "exchange": "binance",
            "symbol": f"{symbol}/USDT",
            "interval": interval
        })
        try:
            r = requests.get(f"{TAAPI_BASE}/{endpoint}", params=params)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    data = {
        "rsi": fetch("rsi"),
        "macd": fetch("macd"),
        "ema9": fetch("ema", {"optInTimePeriod": 9}),
        "ema21": fetch("ema", {"optInTimePeriod": 21}),
        "ema50": fetch("ema", {"optInTimePeriod": 50}),
    }
    return jsonify(data)

@app.route("/filter/<symbol>", methods=["GET"])
def filter_stock(symbol):
    interval = "1h"
    TAAPI_BASE = "https://api.taapi.io"

    def fetch(endpoint, params={}):
        params.update({
            "secret": TAAPI_API_KEY,
            "exchange": "binance",
            "symbol": f"{symbol}/USDT",
            "interval": interval
        })
        try:
            r = requests.get(f"{TAAPI_BASE}/{endpoint}", params=params)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    rsi = fetch("rsi").get("value", 100)
    macd_data = fetch("macd")
    macd = macd_data.get("valueMACD", 0)
    signal = macd_data.get("valueMACDSignal", 0)
    ema9 = fetch("ema", {"optInTimePeriod": 9}).get("value", 0)
    ema21 = fetch("ema", {"optInTimePeriod": 21}).get("value", 0)
    ema50 = fetch("ema", {"optInTimePeriod": 50}).get("value", 0)

    pass_rsi = rsi < 30
    pass_macd = macd > signal
    pass_ema = ema9 > ema21 > ema50

    result = {
        "symbol": symbol,
        "rsi": rsi,
        "macd": macd,
        "signal": signal,
        "ema9": ema9,
        "ema21": ema21,
        "ema50": ema50,
        "passes": pass_rsi and pass_macd and pass_ema
    }

    return jsonify(result)

@app.route("/scan", methods=["POST"])
def scan_all():
    data = request.get_json()
    tickers = data.get("tickers", [])
    results = []

    for symbol in tickers:
        try:
            r = requests.get(f"http://localhost:5000/filter/{symbol}")
            result = r.json()
            if result.get("passes"):
                results.append(result)
        except Exception as e:
            results.append({
                "symbol": symbol,
                "status": "ERROR",
                "message": str(e)
            })
        time.sleep(1)

    return jsonify(results)

@app.route("/score", methods=["POST"])
def score_trades():
    data = request.get_json()
    candidates = data.get("candidates", [])

    approved = []
    for stock in candidates:
        symbol = stock.get("symbol", "UNKNOWN")
        rsi = stock.get("rsi")
        macd = stock.get("macd")
        ema9 = stock.get("ema9")
        ema21 = stock.get("ema21")
        ema50 = stock.get("ema50")

        prompt = f"""
Evaluate this trade setup and give a confidence score (0-100). Only approve if score ≥ 90.

Symbol: {symbol}
RSI: {rsi}
MACD: {macd}
EMA9: {ema9}
EMA21: {ema21}
EMA50: {ema50}

Assume:
- Float size < 100M
- Bullish sentiment
- Positive market mood
- Pattern breakout structure

Respond only with JSON:
{{
  "symbol": "...",
  "score": 0-100,
  "reason": "...",
  "approve": true/false
}}
"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            gpt_reply = response["choices"][0]["message"]["content"]
            approved.append({
                "symbol": symbol,
                "gpt_reply": gpt_reply
            })
        except Exception as e:
            approved.append({
                "symbol": symbol,
                "error": str(e)
            })

    return jsonify(approved)

@app.route("/trade", methods=["POST"])
def execute_trade():
    data = request.get_json()
    symbol = data.get("symbol")

    try:
        barset = api.get_latest_trade(symbol)
        price = float(barset.price)
        quantity = int(500 / price)

        take_profit_price = round(price * 1.10, 2)
        stop_loss_price = round(price * 0.95, 2)

        order = api.submit_order(
            symbol=symbol,
            qty=quantity,
            side='buy',
            type='market',
            time_in_force='gtc',
            order_class='bracket',
            take_profit={'limit_price': take_profit_price},
            stop_loss={'stop_price': stop_loss_price}
        )

        return jsonify({
            "symbol": symbol,
            "qty": quantity,
            "price": price,
            "take_profit": take_profit_price,
            "stop_loss": stop_loss_price,
            "status": "submitted",
            "order_id": order.id
        })

    except Exception as e:
        return jsonify({
            "symbol": symbol,
            "status": "ERROR",
            "message": str(e)
        })

    except Exception as e:
        return jsonify({
            "symbol": symbol,
            "status": "ERROR",
            "message": str(e)
        })

@app.route("/trade-log", methods=["GET"])
def get_trade_log():
    try:
        with open("trade_log.json", "r") as f:
            trades = f.read()
        return app.response_class(trades, mimetype='application/json')
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)})
