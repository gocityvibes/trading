
from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

bot_running = False
trade_log = []

@app.route("/start", methods=["POST"])
def start_bot():
    global bot_running
    bot_running = True

    def scanning_loop():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Bot started scanning.")
        try:
            while bot_running:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning tickers...")
                time.sleep(10)
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Scanning loop crashed: {e}")

    threading.Thread(target=scanning_loop, daemon=True).start()
    return jsonify({"message": "Bot started"}), 200

@app.route("/stop", methods=["POST"])
def stop_bot():
    global bot_running
    bot_running = False
    return jsonify({"message": "Bot stopped"}), 200

@app.route("/trade-log", methods=["GET"])
def get_log():
    return jsonify({"log": trade_log}), 200

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"running": bot_running}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
