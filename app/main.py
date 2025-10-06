
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os
from urllib.parse import quote
from datetime import datetime, timedelta, timezone

try:
    import yfinance as yf
except Exception:
    yf = None

app = FastAPI(title="Trading Control + Candle Status + Backfill2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONTROL_KEY = os.getenv("CONTROL_KEY", "jcpclov3$$")
CONTROL_KEY_URLSAFE = quote(CONTROL_KEY, safe="")
DATABASE_URL = os.getenv("DATABASE_URL", "")

STATE = {"trading": False}

def check_key(key: str):
    if not CONTROL_KEY:
        raise HTTPException(status_code=500, detail="CONTROL_KEY not set")
    if key != CONTROL_KEY:
        raise HTTPException(status_code=401, detail="Invalid key")

def norm_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if "+psycopg" not in url and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

@app.get("/health")
def health():
    return {"ok": True, "service": "trading-ozhy", "status": "up"}

@app.get("/favicon.ico")
def favicon():
    return Response(content=b"", media_type="image/x-icon")

@app.get("/control/get")
def control_get(action: str = Query(...), key: str = Query(...)):
    check_key(key)
    a = action.lower()
    if a == "start":
        STATE["trading"] = True
        return {"ok": True, "action": "start", "trading": True}
    if a == "stop":
        STATE["trading"] = False
        return {"ok": True, "action": "stop", "trading": False}
    if a == "status":
        return {"ok": True, "action": "status", "trading": STATE["trading"]}
    raise HTTPException(status_code=400, detail="Unknown action")

@app.get("/control-panel", response_class=HTMLResponse)
def control_panel():
    html = f"""
<!doctype html><html><head><meta charset='utf-8'><title>Control Panel</title></head>
<body style='font-family:sans-serif;margin:40px;'>
<h2>Trading Control Panel</h2>
<div style='display:flex; gap:10px; flex-wrap:wrap'>
  <a href='/control/get?action=start&key={CONTROL_KEY_URLSAFE}'><button>▶ Start</button></a>
  <a href='/control/get?action=stop&key={CONTROL_KEY_URLSAFE}'><button>⏹ Stop</button></a>
  <a href='/control/get?action=status&key={CONTROL_KEY_URLSAFE}'><button>📊 Status</button></a>
  <a href='/health'><button>🩺 Health</button></a>
  <a href='/candles/status'><button>🕯️ Candles</button></a>
</div>
<div style='margin-top:16px'>
  <a href='/candles/backfill2?key={CONTROL_KEY_URLSAFE}&symbol=AAPL&tf=1m&period=5d'><button>⤵ Backfill2 AAPL 1m 5d</button></a>
  <a href='/candles/backfill2?key={CONTROL_KEY_URLSAFE}&symbol=ES=F&tf=5m&period=60d'><button>⤵ Backfill2 ES 5m 60d</button></a>
</div>
<p style='margin-top:14px;color:#555'>Key (URL-encoded): <code>{CONTROL_KEY_URLSAFE}</code></p>
</body></html>
"""
    return HTMLResponse(content=html)

@app.get("/candles/status")
def candles_status():
    if not DATABASE_URL:
        return {"ok": False, "error": "DATABASE_URL not set"}
    url = norm_db_url(DATABASE_URL)
    try:
        eng = create_engine(url, pool_pre_ping=True)
        with eng.connect() as conn:
            r = conn.execute(text("SELECT COUNT(*) AS count, MAX(timestamp) AS latest FROM candles_raw"))
            row = r.first()
            count = row._mapping["count"] if row else 0
            latest = str(row._mapping["latest"]) if row and row._mapping["latest"] is not None else None
            return {"ok": True, "candles": count, "latest": latest}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/candles/backfill2")
def candles_backfill2(
    key: str = Query(...),
    symbol: str = Query("AAPL"),
    tf: str = Query("1m"),
    period: str = Query("5d"),
):
    check_key(key)
    if not DATABASE_URL:
        return {"ok": False, "error": "DATABASE_URL not set"}
    if yf is None:
        return {"ok": False, "error": "yfinance not installed"}

    # Validate interval support and Yahoo limitations
    valid_tfs = {"1m": "7d", "2m": "60d", "5m": "60d", "15m": "60d", "30m": "60d", "60m": "730d"}
    if tf not in valid_tfs:
        return {"ok": False, "error": "unsupported tf; try 1m,2m,5m,15m,30m,60m"}
    # Clamp period if user asks too much for given interval
    max_period = valid_tfs[tf]
    # Very light validation; rely on Yahoo to error for odd periods
    # Examples: 1m <= 7d, 5m/15m/30m <= 60d

    try:
        df = yf.download(tickers=symbol, interval=tf, period=period, progress=False, auto_adjust=False)
        if df is None or df.empty:
            return {"ok": False, "rows": 0, "note": "no data returned"}

        df = df.reset_index().rename(columns={"Datetime": "ts", "Date": "ts"})
        ts_col = "ts" if "ts" in df.columns else df.columns[0]

        url = norm_db_url(DATABASE_URL)
        eng = create_engine(url, pool_pre_ping=True)
        inserted = 0
        with eng.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS candles_raw (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    open DOUBLE PRECISION NOT NULL,
                    high DOUBLE PRECISION NOT NULL,
                    low DOUBLE PRECISION NOT NULL,
                    close DOUBLE PRECISION NOT NULL,
                    volume BIGINT NOT NULL DEFAULT 0
                );
            """))
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ux_candles_symbol_tf_ts
                ON candles_raw(symbol, timeframe, timestamp);
            """))
            for _, r in df.iterrows():
                ts = r[ts_col]
                conn.execute(text("""
                    INSERT INTO candles_raw (symbol, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (:symbol, :timeframe, :timestamp, :open, :high, :low, :close, :volume)
                    ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING;
                """), dict(
                    symbol=symbol,
                    timeframe=tf,
                    timestamp=ts if isinstance(ts, str) else getattr(ts, "to_pydatetime", lambda: ts)(),
                    open=float(r.get("Open", r.get("open", 0))),
                    high=float(r.get("High", r.get("high", 0))),
                    low=float(r.get("Low", r.get("low", 0))),
                    close=float(r.get("Close", r.get("close", 0))),
                    volume=int(r.get("Volume", r.get("volume", 0)) or 0),
                ))
                inserted += 1

        return {"ok": True, "symbol": symbol, "tf": tf, "period": period, "rows_inserted": inserted}
    except Exception as e:
        return {"ok": False, "error": str(e)}
