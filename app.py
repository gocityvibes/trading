
from flask import Flask, jsonify
import os

# Import backend logic
from main import get_trade_log  # assumes main.py defines this function

app = Flask(__name__)

@app.route("/trade-log")
def trade_log():
    # Return live GPT trade log
    return jsonify(get_trade_log())

if __name__ == "__main__":
    app.run(debug=True)
