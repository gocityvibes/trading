
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os
from urllib.parse import quote
from datetime import datetime, timedelta, timezone

# Optional backfill import guarded to keep import errors readable
try:
    import yfinance as yf
except Exception as _e:
    yf = None

app = FastAPI(title="Trading Control + Candle Status + Backfill")

# CORS
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
    act = action.lower()
    if act == "start":
        STATE["trading"] = True
        return {"ok": True, "action": "start", "trading": True}
    elif act == "stop":
        STATE["trading"] = False
        return {"ok": True, "action": "stop", "trading": False}
    elif act == "status":
        return {"ok": True, "action": "status", "trading": STATE["trading"]}
    else:
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
  <a href='/candles/init?key={CONTROL_KEY_URLSAFE}'><button>🧱 Init Table</button></a>
  <a href='/candles/backfill?key={CONTROL_KEY_URLSAFE}&symbol=ES=F&tf=1m&days=60'><button>⤵ Backfill 60d ES 1m</button></a>
</div>
<p style='margin-top:14px;color:#555'>Key (URL-encoded): <code>{CONTROL_KEY_URLSAFE}</code></p>
</body></html>
"""
    return HTMLResponse(content=html)

@app.get("/candles/init")
def candles_init(key: str = Query(...)):
    check_key(key)
    if not DATABASE_URL:
        return {"ok": False, "error": "DATABASE_URL not set"}
    url = norm_db_url(DATABASE_URL)
    try:
        engine = create_engine(url, pool_pre_ping=True)
        ddl = """
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
        CREATE INDEX IF NOT EXISTS idx_candles_symbol_tf_ts
            ON candles_raw (symbol, timeframe, timestamp);
        """
        with engine.begin() as conn:
            for stmt in ddl.split(";"):
                s = stmt.strip()
                if s:
                    conn.execute(text(s))
        return {"ok": True, "created": True, "table": "candles_raw"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/candles/status")
def candles_status():
    if not DATABASE_URL:
        return {"ok": False, "error": "DATABASE_URL not set"}
    url = norm_db_url(DATABASE_URL)
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) AS count, MAX(timestamp) AS latest FROM candles_raw"))
            row = result.first()
            count = row._mapping["count"] if row else 0
            latest = str(row._mapping["latest"]) if row and row._mapping["latest"] is not None else None
            return {"ok": True, "candles": count, "latest": latest}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/candles/backfill")
def candles_backfill(
    key: str = Query(...),
    symbol: str = Query("ES=F"),
    tf: str = Query("1m"),
    days: int = Query(60, ge=1, le=365),
):
    check_key(key)
    if not DATABASE_URL:
        return {"ok": False, "error": "DATABASE_URL not set"}
    if yf is None:
        return {"ok": False, "error": "yfinance not installed"}
    # Map tf to yfinance interval
    interval_map = {"1m": "1m", "5m": "5m", "15m": "15m"}
    interval = interval_map.get(tf)
    if not interval:
        return {"ok": False, "error": "unsupported tf; use 1m,5m,15m"}

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    try:
        df = yf.download(tickers=symbol, interval=interval, start=start, end=end, progress=False)
        if df is None or df.empty:
            return {"ok": False, "rows": 0, "note": "no data returned"}
        # yfinance returns columns: Open, High, Low, Close, Volume
        df = df.reset_index().rename(columns={
            "Datetime": "ts",
            "Date": "ts"  # sometimes 'Date' depending on interval
        })
        # Ensure timestamp column name
        ts_col = "ts" if "ts" in df.columns else df.columns[0]
        records = []
        for _, r in df.iterrows():
            ts = r[ts_col]
            # Normalize to ISO string; let Postgres parse it
            records.append({
                "symbol": symbol,
                "timeframe": tf,
                "timestamp": ts if isinstance(ts, str) else getattr(ts, "to_pydatetime", lambda: ts)(),
                "open": float(r.get("Open", r.get("open", 0))),
                "high": float(r.get("High", r.get("high", 0))),
                "low": float(r.get("Low", r.get("low", 0))),
                "close": float(r.get("Close", r.get("close", 0))),
                "volume": int(r.get("Volume", r.get("volume", 0)) or 0),
            })

        url = norm_db_url(DATABASE_URL)
        engine = create_engine(url, pool_pre_ping=True)
        inserted = 0
        with engine.begin() as conn:
            # upsert-ish: ignore duplicates by (symbol,timeframe,timestamp)
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ux_candles_symbol_tf_ts
                ON candles_raw(symbol, timeframe, timestamp);
            """))
            for rec in records:
                conn.execute(text("""
                    INSERT INTO candles_raw (symbol, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (:symbol, :timeframe, :timestamp, :open, :high, :low, :close, :volume)
                    ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING;
                """), rec)
                inserted += 1
        return {"ok": True, "symbol": symbol, "tf": tf, "days": days, "rows_attempted": len(records), "rows_inserted": inserted}
    except Exception as e:
        return {"ok": False, "error": str(e)}
