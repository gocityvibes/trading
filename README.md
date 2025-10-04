
# Trading Control + Candle Status

Endpoints:
- /health
- /control/get?action=start|stop|status&key=YOUR_KEY
- /control-panel (with buttons)
- /candles/status (checks candles_raw table in DATABASE_URL)

### Deploy
1. Add env vars in Render:
   - CONTROL_KEY=jcpclov3$$
   - DATABASE_URL=postgres://... (your actual DB URL)
2. Start command:
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
