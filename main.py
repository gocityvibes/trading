
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

trade_log = []

@app.route("/start", methods=["POST"])
def start():
    return jsonify({"status": "Bot started (dummy)"})

@app.route("/trade-log", methods=["GET"])
def get_trade_log():
    return jsonify(trade_log)

@app.route("/add-dummy-trade", methods=["GET"])
def add_dummy_trade():
    trade_log.append("TSLA — Closed +$155.00 @ $262.78\n🧠 GPT: Test Score 99")
    return jsonify({"status": "Dummy trade added"})

if __name__ == "__main__":
    app.run()
