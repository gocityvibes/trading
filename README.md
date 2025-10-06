
# Trading Control + Candle Status + Backfill2 (period-based intraday)

Adds `/candles/backfill2` which uses Yahoo's **period** parameter for intraday:
- 1m -> up to 7d
- 2m/5m/15m/30m -> up to ~60d
- 60m -> up to ~730d

Examples:
- /candles/backfill2?key=...&symbol=AAPL&tf=1m&period=5d
- /candles/backfill2?key=...&symbol=ES=F&tf=5m&period=60d

Other endpoints:
- /health
- /control/get?action=start|stop|status&key=...
- /control-panel
- /candles/status
