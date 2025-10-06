
# Trading Control + Candle Status + Backfill

Endpoints:
- /health
- /control/get?action=start|stop|status&key=YOUR_KEY
- /control-panel
- /candles/init?key=YOUR_KEY
- /candles/status
- /candles/backfill?key=YOUR_KEY&symbol=ES=F&tf=1m&days=60

Backfill uses yfinance. Intervals supported: 1m, 5m, 15m.

Render env:
- CONTROL_KEY=jcpclov3$$
- DATABASE_URL=postgresql://<user>:<pass>@<host>/<db>

Start command:
uvicorn app.main:app --host 0.0.0.0 --port $PORT
