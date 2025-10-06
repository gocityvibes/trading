
# Trading Control + Diagnostics

Endpoints:
- /health
- /control/get?action=start|stop|status&key=YOUR_KEY
- /control-panel
- /candles/status
- /candles/yfcheck?symbol=AAPL&tf=60m&period=5d  -> returns dataframe metadata + head (no DB write)
- /candles/mockload?key=YOUR_KEY&rows=50&symbol=TEST&tf=1m -> inserts synthetic rows to verify DB pipeline

If yfcheck returns rows > 0 but status stays 0, the DB insert logic is the issue.
If yfcheck rows = 0 for AAPL/60m/5d, Yahoo is likely blocking or rate-limiting from your server.
