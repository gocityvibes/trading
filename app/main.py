
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os
from urllib.parse import quote

app = FastAPI(title="Trading Control + Candle Status")

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

@app.get("/health")
def health():
    return {"ok": True, "service": "trading-ozhy", "status": "up"}

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
<!doctype html>
<html><head><meta charset='utf-8'><title>Control Panel</title></head>
<body style='font-family:sans-serif;margin:40px;'>
<h2>Trading Control Panel</h2>
<a href='/control/get?action=start&key={CONTROL_KEY_URLSAFE}'><button>Start</button></a>
<a href='/control/get?action=stop&key={CONTROL_KEY_URLSAFE}'><button>Stop</button></a>
<a href='/control/get?action=status&key={CONTROL_KEY_URLSAFE}'><button>Status</button></a>
<a href='/health'><button>Health</button></a>
<a href='/candles/status'><button>Candles</button></a>
<p>CONTROL_KEY={CONTROL_KEY_URLSAFE}</p>
</body></html>
"""
    return HTMLResponse(content=html)

@app.get("/candles/status")
def candles_status():
    if not DATABASE_URL:
        return {"ok": False, "error": "DATABASE_URL not set"}
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) AS count, MAX(timestamp) AS latest FROM candles_raw"))
            row = result.first()
            return {"ok": True, "candles": row._mapping["count"], "latest": str(row._mapping["latest"])}
    except Exception as e:
        return {"ok": False, "error": str(e)}
