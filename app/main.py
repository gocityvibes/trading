
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os, json
from urllib.parse import quote
from datetime import datetime, timedelta, timezone

try:
    import yfinance as yf
    import pandas as pd
except Exception:
    yf = None
    pd = None

app = FastAPI(title="Trading Control + Diagnostics")

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
<h2>Trading Diagnostics Panel</h2>
<div style='display:flex; gap:10px; flex-wrap:wrap'>
  <a href='/control/get?action=start&key={CONTROL_KEY_URLSAFE}'><button>▶ Start</button></a>
  <a href='/control/get?action=stop&key={CONTROL_KEY_URLSAFE}'><button>⏹ Stop</button></a>
  <a href='/control/get?action=status&key={CONTROL_KEY_URLSAFE}'><button>📊 Status</button></a>
  <a href='/health'><button>🩺 Health</button></a>
  <a href='/candles/status'><button>🕯️ Candles</button></a>
  <a href='/candles/yfcheck?symbol=AAPL&tf=60m&period=5d'><button>🔍 YF Check AAPL 60m 5d</button></a>
  <a href='/candles/mockload?key={CONTROL_KEY_URLSAFE}&rows=50&symbol=TEST&tf=1m'><button>🧪 Mockload 50</button></a>
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

@app.get("/candles/yfcheck")
def yfcheck(symbol: str = Query("AAPL"), tf: str = Query("60m"), period: str = Query("5d")):
    if yf is None:
        return {"ok": False, "error": "yfinance/pandas not installed"}
    try:
        df = yf.download(tickers=symbol, interval=tf, period=period, progress=False, auto_adjust=False)
        # Return only metadata, not full data (to keep response small)
        if df is None or df.empty:
            return {"ok": True, "rows": 0, "columns": [], "head": []}
        df = df.reset_index()
        cols = list(df.columns)
        head = df.head(5).astype(str).to_dict(orient="records")
        return {"ok": True, "rows": int(df.shape[0]), "columns": cols, "head": head}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/candles/mockload")
def mockload(
    key: str = Query(...),
    rows: int = Query(50, ge=1, le=2000),
    symbol: str = Query("TEST"),
    tf: str = Query("1m"),
):
    check_key(key)
    if not DATABASE_URL:
        return {"ok": False, "error": "DATABASE_URL not set"}
    url = norm_db_url(DATABASE_URL)
    try:
        eng = create_engine(url, pool_pre_ping=True)
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
                CREATE UNIQUE INDEX IF NOT EXISTS ux_candles_symbol_tf_ts
                ON candles_raw(symbol, timeframe, timestamp);
            """))
            base = datetime.now(timezone.utc) - timedelta(minutes=rows)
            inserted = 0
            for i in range(rows):
                ts = base + timedelta(minutes=i)
                o = 100 + i * 0.1
                h = o + 0.5
                l = o - 0.5
                c = o + 0.1
                v = 1000 + i
                conn.execute(text("""
                    INSERT INTO candles_raw (symbol, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (:symbol, :tf, :ts, :o, :h, :l, :c, :v)
                    ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING;
                """), {"symbol": symbol, "tf": tf, "ts": ts, "o": o, "h": h, "l": l, "c": c, "v": v})
                inserted += 1
        return {"ok": True, "inserted": inserted, "symbol": symbol, "tf": tf}
    except Exception as e:
        return {"ok": False, "error": str(e)}
