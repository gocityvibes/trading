
# Trading Control + Candle Status (psycopg2 included)

Endpoints:
- /health
- /control/get?action=start|stop|status&key=YOUR_KEY
- /control-panel (with buttons)
- /candles/status (checks candles_raw table in DATABASE_URL)

### Deploy
1. Add env vars in Render:
   - CONTROL_KEY=jcpclov3$$
   - DATABASE_URL=postgresql://<user>:<pass>@<host>/<db>  (or postgresql+psycopg2://...)
2. Start command:
   uvicorn app.main:app --host 0.0.0.0 --port $PORT

Notes:
- This build includes psycopg2-binary to avoid "No module named 'psycopg2'".
- The /candles/status route auto-upgrades postgres:// to postgresql+psycopg2:// for driver reliability.
