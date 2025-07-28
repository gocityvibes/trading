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


import json
import time

# ====== LIVE PRICE PATCH BEGIN ======
def get_live_price(symbol):
    # TODO: Replace this with your actual price API call
    mock_prices = {
        "TSLA": 327.56,
        "AAPL": 198.12,
        "NVDA": 914.32
    }
    return mock_prices.get(symbol, 0)

def scan_stocks_in_chunks():
        check_and_close_trades():
    try:
        with open("trade_log.json", "r") as f:
            trades = json.load(f)
    except:
        trades = []

    for trade in trades:
        if trade.get("status") == "OPEN":
            current_price = get_live_price(trade["symbol"])
            entry = trade["entry"]
            target = entry * 1.03  # 3% take profit

            if current_price >= target:
                trade["status"] = "CLOSED"
                trade["exit"] = current_price
                trade["profit"] = round(current_price - entry, 2)
                trade["closed_time"] = time.strftime('%I:%M %p')

    with open("trade_log.json", "w") as f:
        json.dump(trades, f, indent=2)
# ====== LIVE PRICE PATCH END ======


# ====== SCAN LOOP PATCH BEGIN ======
import threading

running = False


# ====== CHUNKED SCANNING PATCH BEGIN ======
def get_top_100_stocks():
    # Replace with your real stock fetching logic
    return [f"STOCK{i}" for i in range(1, 101)]

def scan_stocks_in_chunks():
    all_stocks = get_top_100_stocks()
    for i in range(0, len(all_stocks), 20):
        chunk = all_stocks[i:i+20]
        print(f"🔍 Scanning chunk: {chunk}")
        filtered = gpt35_scan(chunk)
        for symbol in filtered:
            score = gpt40_score(symbol)
            if score >= 85:
                print(f"✅ Trade triggered: {symbol} | Score: {score}")
                execute_trade(symbol, score)
        time.sleep(1)  # small delay between chunks if needed

# Replace scan_stocks_in_chunks()
        check_and_close_trades() call with this new logic
# Called inside scan_loop
# ====== CHUNKED SCANNING PATCH END ======


# ====== FULL GPT SCAN PATCH BEGIN ======
import openai
import random

openai.api_key = "your-gpt-api-key-here"  # TODO: Replace with your actual GPT key

def gpt35_scan(symbols):
    # Simulate GPT-3.5 scanning logic
    scanned = []
    for sym in symbols:
        # Pretend GPT-3.5 is filtering and returns maybe half
        if random.random() > 0.5:
            scanned.append(sym)
    return scanned

def gpt40_score(symbol):
    # Simulate GPT-4o scoring (placeholder, replace with real GPT call)
    score = random.randint(80, 100)
    return score

def execute_trade(symbol, score):
    entry_price = get_live_price(symbol)
    trade = {
        "symbol": symbol,
        "entry": entry_price,
        "status": "OPEN",
        "score": score,
        "time": time.strftime('%I:%M %p')
    }
    try:
        with open("trade_log.json", "r") as f:
            trades = json.load(f)
    except:
        trades = []

    trades.append(trade)

    with open("trade_log.json", "w") as f:
        json.dump(trades, f, indent=2)
# ====== FULL GPT SCAN PATCH END ======


# ====== AUTO SHUTDOWN PATCH BEGIN ======
def is_past_shutdown_time():
    now = datetime.datetime.now()
    shutdown_hour = 15  # 3 PM
    shutdown_minute = 30
    if now.hour > shutdown_hour or (now.hour == shutdown_hour and now.minute >= shutdown_minute):
        return True
    return False
# ====== AUTO SHUTDOWN PATCH END ======

def scan_loop():
    global running
    while running:
        if is_past_shutdown_time():
            print("🛑 Auto-shutdown: Market close reached (3:30 PM CT)")
            running = False
            break
        print("🔄 Running trade scan and close cycle...")
        scan_stocks_in_chunks()
        check_and_close_trades()
        # TODO: Add GPT scan and trade entry here if unfrozen
        time.sleep(60)  # Wait 60 seconds between scans

@app.route("/start", methods=["POST"])
def start_bot_loop():
    global running
    if not running:
        running = True
        threading.Thread(target=scan_loop).start()
    return jsonify({"status": "Bot is now running continuously."})

@app.route("/stop", methods=["POST"])
def stop_bot_loop():
    global running
    running = False
    return jsonify({"status": "Bot has been stopped."})
# ====== SCAN LOOP PATCH END ======

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
# Old wrapper removed
    scan_stocks_in_chunks()
        check_and_close_trades()
    # Replaced by scan_loop


def start_bot():  # renamed to avoid route clash
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



@app.route('/trade-log')
def get_trade_log():
    import json
    try:
        with open("trade_log.json", "r") as f:
            return json.load(f)
    except Exception as e:
        return {"error": "Could not load trade log", "details": str(e)}


@app.route('/daily-summary')
def daily_summary():
    import json
    from datetime import datetime

    try:
        with open("trade_log.json", "r") as f:
            data = json.load(f)
    except:
        return {"error": "Unable to load trade log"}

    today = datetime.utcnow().date().isoformat()
    wins = 0
    losses = 0
    total_pnl = 0
    trades_today = 0

    for trade in data:
        if trade["timestamp"].startswith(today):
            trades_today += 1
            if trade.get("outcome") == "WIN":
                wins += 1
                total_pnl += (trade.get("exit_price", 0) - trade.get("fill_price", 0))
            elif trade.get("outcome") == "LOSS":
                losses += 1
                total_pnl += (trade.get("exit_price", 0) - trade.get("fill_price", 0))

    win_rate = round((wins / trades_today) * 100, 2) if trades_today else 0

    return {
        "date": today,
        "total_trades": trades_today,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": win_rate,
        "pnl": round(total_pnl, 2)
    }

@app.route('/download-log')
def download_log():
    from flask import send_file
    csv_path = export_log_to_csv()
    if csv_path and os.path.exists(csv_path):
        return send_file(csv_path, as_attachment=True)
    else:
        return {"error": "Unable to generate CSV file"}
