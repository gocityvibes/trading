from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import time
from gpt_logic import analyze_symbol
from risk_manager import place_trade

app = Flask(__name__)
CORS(app)

bot_active = False
TRADE_LOG = []
WATCHLIST = []

@app.route('/start', methods=['POST'])
def start_bot():
    global bot_active
    bot_active = True
    WATCHLIST.clear()
    WATCHLIST.extend(request.json.get("symbols", []))

    thread = threading.Thread(target=run_scan)
    thread.start()
    return jsonify({"status": "Bot started", "symbols": WATCHLIST})

@app.route('/stop', methods=['POST'])
def stop_bot():
    global bot_active
    bot_active = False
    return jsonify({"status": "Bot stopped"})

@app.route('/trade-log', methods=['GET'])
def trade_log():
    return jsonify(TRADE_LOG)

def run_scan():
    global bot_active
    for symbol in WATCHLIST:
        if not bot_active:
            break
        try:
            result = analyze_symbol(symbol)
            if result["score"] >= 90 and result["float"] < 100_000_000 and result["sentiment"] == "bullish" and result["pattern_confirmed"]:
                trade = place_trade(symbol, result)
                TRADE_LOG.append({"symbol": symbol, "status": "TRADE_PLACED", "details": trade})
            else:
                TRADE_LOG.append({"symbol": symbol, "status": "SKIPPED", "reason": "Did not meet Elite Mode criteria", "details": result})
        except Exception as e:
            TRADE_LOG.append({"symbol": symbol, "status": "ERROR", "message": str(e)})
        time.sleep(1)

if __name__ == '__main__':
    app.run(debug=True)


import requests

# 👉 Taapi.io API Key placeholder (replace this with your actual Pro key later)
TAAPI_API_KEY = "your_pro_api_key_here"
TAAPI_BASE = "https://api.taapi.io"

@app.route("/indicators/<symbol>", methods=["GET"])
def get_indicators(symbol):
    interval = "1h"  # Adjustable

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

    # Fetch indicators
    rsi = fetch("rsi").get("value", 100)
    macd_data = fetch("macd")
    macd = macd_data.get("valueMACD", 0)
    signal = macd_data.get("valueMACDSignal", 0)
    ema9 = fetch("ema", {"optInTimePeriod": 9}).get("value", 0)
    ema21 = fetch("ema", {"optInTimePeriod": 21}).get("value", 0)
    ema50 = fetch("ema", {"optInTimePeriod": 50}).get("value", 0)

    # Apply filter rules
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


import time

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
        time.sleep(1)  # Respect Taapi.io Pro rate limit

    return jsonify(results)


import openai

# Set your GPT API key here or load from env
GPT_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = GPT_API_KEY

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

        # Prompt for GPT-4o
        prompt = f"""
Evaluate this trade setup and give a confidence score (0-100). Only approve if score ≥ 90.

Symbol: {symbol}
RSI: {rsi}
MACD: {macd}
EMA9: {ema9}
EMA21: {ema21}
EMA50: {ema50}

Also check:
- Float size < 100M (assume YES)
- Bullish sentiment (assume YES)
- SPY/QQQ market mood is positive (assume YES)
- Pattern looks like breakout (assume YES)

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
