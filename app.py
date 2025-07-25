
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/trade-log")
def trade_log():
    return jsonify({
        "status": "success",
        "trades": [
            {"ticker": "AAPL", "score": 95, "entry": 189.5, "exit": 192.2},
            {"ticker": "NVDA", "score": 92, "entry": 900.0, "exit": 918.6}
        ]
    })

if __name__ == "__main__":
    app.run()
