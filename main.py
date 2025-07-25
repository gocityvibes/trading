
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/trade-log', methods=['GET'])
def trade_log():
    # Sample placeholder data
    return jsonify([
        {"symbol": "AAPL", "status": "Closed +$2.70", "score": 95},
        {"symbol": "NVDA", "status": "Closed +$18.60", "score": 92}
    ])

@app.route('/start', methods=['POST'])
def start_bot():
    # Simulate bot starting
    return jsonify({"message": "Bot started successfully."})

@app.route('/', methods=['GET'])
def root():
    return 'Trading Bot Backend is Running'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
