
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/trade-log')
def trade_log():
    return jsonify({"status": "ok", "message": "Backend is connected and CORS is working."})

if __name__ == '__main__':
    app.run(debug=True)
