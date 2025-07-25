
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread
import time

app = Flask(__name__)
CORS(app)

trading_active = False
trade_log_data = []

def run_trading_loop():
    global trading_active, trade_log_data
    while trading_active:
        # Simulated trade logic
        trade_log_data.append({
            "ticker": "SIM",
            "score": 93,
            "entry": 100.0,
            "exit": 108.0
        })
        time.sleep(10)  # simulate delay between trades

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

if __name__ == "__main__":
    app.run()
