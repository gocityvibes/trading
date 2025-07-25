
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

bot_status = {"running": False}
trade_log = []

@app.route("/start", methods=["GET"])
def start():
    if not bot_status["running"]:
        bot_status["running"] = True
        trade_log.append("Bot started.")
        return jsonify({"message": "Bot started"}), 200
    return jsonify({"message": "Bot already running"}), 200

@app.route("/stop", methods=["GET"])
def stop():
    if bot_status["running"]:
        bot_status["running"] = False
        trade_log.append("Bot stopped.")
        return jsonify({"message": "Bot stopped"}), 200
    return jsonify({"message": "Bot already stopped"}), 200

@app.route("/trade-log", methods=["GET"])
def get_log():
    return jsonify({"log": trade_log}), 200
