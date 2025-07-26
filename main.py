
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import time
from gpt_logic import analyze_symbol
from risk_manager import place_trade

app = Flask(__name__)
CORS(app)

bot_active = False
TRADE_LOG = []
WATCHLIST = []

@app.route('/start', methods=['POST'])
def start_bot():
    global bot_active
    bot_active = True
    WATCHLIST.clear()
    WATCHLIST.extend(request.json.get("symbols", []))

    thread = threading.Thread(target=run_scan)
    thread.start()
    return jsonify({"status": "Bot started", "symbols": WATCHLIST})

@app.route('/stop', methods=['POST'])
def stop_bot():
    global bot_active
    bot_active = False
    return jsonify({"status": "Bot stopped"})

@app.route('/trade-log', methods=['GET'])
def trade_log():
    return jsonify(TRADE_LOG)

def run_scan():
    global bot_active
    for symbol in WATCHLIST:
        if not bot_active:
            break
        try:
            result = analyze_symbol(symbol)
            if result["score"] >= 90 and result["float"] < 100_000_000 and result["sentiment"] == "bullish" and result["pattern_confirmed"]:
                trade = place_trade(symbol, result)
                TRADE_LOG.append({"symbol": symbol, "status": "TRADE_PLACED", "details": trade})
            else:
                TRADE_LOG.append({"symbol": symbol, "status": "SKIPPED", "reason": "Did not meet Elite Mode criteria", "details": result})
        except Exception as e:
            TRADE_LOG.append({"symbol": symbol, "status": "ERROR", "message": str(e)})
        time.sleep(1)

if __name__ == '__main__':
    app.run(debug=True)
