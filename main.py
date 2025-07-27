from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "Backend is running"

@app.route('/start', methods=['POST'])
def start_bot():
    return jsonify({"message": "Dummy trade executed", "status": "success"})

@app.route('/trade-log', methods=['GET'])
def get_trade_log():
    return jsonify([])