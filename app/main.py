
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from urllib.parse import quote

app = FastAPI(title="Trading Control")

# CORS (optional; safe defaults)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Read key from env, default to provided one so it "just works" on first run
CONTROL_KEY = os.getenv("CONTROL_KEY", "jcpclov3$$")

# URL-safe version (for buttons/links in HTML)
CONTROL_KEY_URLSAFE = quote(CONTROL_KEY, safe="")

STATE = {"trading": False}

def check_key(key: str):
    if not CONTROL_KEY:
        raise HTTPException(status_code=500, detail="CONTROL_KEY not set on server")
    if key != CONTROL_KEY:
        raise HTTPException(status_code=401, detail="invalid key")

@app.get("/")
def root():
    return {"ok": True, "message": "Trading Control service is up", "routes": ["/health", "/control/get", "/control-panel"]}

@app.get("/health")
def health():
    return {"ok": True, "service": "trading-ozhy", "status": "up"}

@app.get("/control/get")
def control_get(action: str = Query(..., description="start | stop | status"), key: str = Query(..., description="control API key")):
    check_key(key)
    act = (action or "").lower()
    if act == "start":
        STATE["trading"] = True
        return {"ok": True, "action": "start", "trading": True}
    elif act == "stop":
        STATE["trading"] = False
        return {"ok": True, "action": "stop", "trading": False}
    elif act == "status":
        return {"ok": True, "action": "status", "trading": STATE["trading"]}
    else:
        raise HTTPException(status_code=400, detail="unknown action")

@app.get("/control-panel", response_class=HTMLResponse)
def control_panel():
    html = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Trading Control Panel</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; }}
    .wrap {{ max-width: 600px; margin: 0 auto; }}
    h1 {{ font-size: 22px; }}
    .row {{ display: flex; gap: 12px; margin: 16px 0; }}
    button {{ padding: 10px 14px; border-radius: 10px; border: 1px solid #ddd; cursor: pointer; }}
    a {{ text-decoration: none; }}
    .foot {{ margin-top: 24px; color: #666; font-size: 14px; }}
    .url {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Trading Control Panel</h1>
    <div class="row">
      <a href="/control/get?action=start&key={CONTROL_KEY_URLSAFE}"><button>▶ Start</button></a>
      <a href="/control/get?action=stop&key={CONTROL_KEY_URLSAFE}"><button>⏹ Stop</button></a>
      <a href="/control/get?action=status&key={CONTROL_KEY_URLSAFE}"><button>📊 Status</button></a>
      <a href="/health"><button>🩺 Health</button></a>
    </div>
    <div class="foot">
      <div>Using key: <span class="url">{CONTROL_KEY_URLSAFE}</span> (URL‑encoded)</div>
      <div>Set <code>CONTROL_KEY</code> in your environment to change it.</div>
    </div>
  </div>
</body>
</html>
    """
    return HTMLResponse(content=html)
