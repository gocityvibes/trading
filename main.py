import os
import openai
import requests
import threading
import time
from datetime import datetime
from alpaca_trade_api.rest import REST, TimeFrame
from flask import Flask, jsonify

app = Flask(__name__)

# Load keys from environment
ALPACA_KEY = os.getenv("ALPACA_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY
alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

bot_running = False
trade_log = []
tickers = ["AAPL", "TSLA", "NVDA", "AMD", "MSFT"]  # You can add more tickers

def analyze_ticker(ticker):
    # Get last bar data
    barset = alpaca.get_bars(ticker, TimeFrame.Minute, limit=5)
    if len(barset) == 0:
        return None

    current_price = barset[-1].c
    prompt = f"Analyze stock {ticker} with current price {current_price}. Is this a bullish breakout setup? Respond with YES or NO only."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10
        )
        decision = response.choices[0].message.content.strip().upper()
        return decision == "YES"
    except Exception as e:
        print(f"[{datetime.now()}] GPT error for {ticker}: {e}")
        return None

def trade_ticker(ticker):
    qty = 1  # For paper trading, fixed quantity
    try:
        alpaca.submit_order(symbol=ticker, qty=qty, side="buy", type="market", time_in_force="gtc")
        trade_log.append(f"[{datetime.now()}] Bought {qty} of {ticker} at market price.")
        print(f"[{datetime.now()}] ✅ Trade executed: BUY {ticker}")
    except Exception as e:
        print(f"[{datetime.now()}] Trade failed for {ticker}: {e}")
        trade_log.append(f"[{datetime.now()}] Trade failed for {ticker}: {e}")

def trading_loop():
    global bot_running
    while bot_running:
        for ticker in tickers:
            print(f"[{datetime.now()}] Scanning {ticker}...")
            signal = analyze_ticker(ticker)
            if signal:
                trade_ticker(ticker)
            time.sleep(5)  # Wait between tickers
        time.sleep(20)  # Pause before rescanning all tickers

@app.route("/start", methods=["POST"])
def start_bot():
    global bot_running
    if not bot_running:
        bot_running = True
        threading.Thread(target=trading_loop, daemon=True).start()
    return jsonify({"message": "Bot started"}), 200

@app.route("/stop", methods=["POST"])
def stop_bot():
    global bot_running
    bot_running = False
    return jsonify({"message": "Bot stopped"}), 200

@app.route("/trade-log", methods=["GET"])
def get_trade_log():
    return jsonify({"log": trade_log}), 200

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"running": bot_running}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
