
# Trading Control + Candle Status + Init

Endpoints:
- /health
- /control/get?action=start|stop|status&key=YOUR_KEY
- /control-panel
- /candles/init?key=YOUR_KEY   (creates candles_raw table + index if missing)
- /candles/status              (reports count + latest ts)

## Deploy on Render
1. Env vars:
   - CONTROL_KEY=jcpclov3$$
   - DATABASE_URL=postgresql://<user>:<pass>@<host>/<db>
2. Start:
   uvicorn app.main:app --host 0.0.0.0 --port $PORT

Then visit:
- /control-panel  (has a button for Init and Candles)
- /candles/init?key=jcpclov3%24%24
- /candles/status
