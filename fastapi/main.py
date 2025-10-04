from fastapi import FastAPI, Request, HTTPException
from sqlalchemy import text
from db import get_session
from fastapi.responses import HTMLResponse

app = FastAPI(title="Stage9 Control + Candles + UI")

@app.get("/health")
def health():
    with get_session() as s:
        now = s.execute(text("select now()")).scalar()
    return {"ok": True, "service": "trading", "time": str(now)}

# Control panel UI
@app.get("/control-panel", response_class=HTMLResponse)
def control_panel():
    return '''<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Control Panel</title>
<style>body{font-family:system-ui;max-width:560px;margin:40px auto;padding:0 16px;background:#0b0b0b;color:#eaeaea}
input,button{font-size:16px}input{width:100%;padding:10px;border-radius:8px;border:1px solid #333;background:#111;color:#eee;box-sizing:border-box}
button{margin-right:10px;margin-top:10px;padding:10px 14px;border-radius:10px;border:0;background:#4b8bff;color:#fff;cursor:pointer}
pre{background:#0a0a0a;border:1px solid #222;color:#9cff9c;padding:12px;border-radius:10px;white-space:pre-wrap}</style></head>
<body><h2>Stage 9 Control</h2>
<label>API Key<br><input id="k" type="password" placeholder="Enter your API key"></label>
<div><button onclick="go('status')">Status</button><button onclick="go('start')">Start</button><button onclick="go('stop')">Stop</button></div>
<p><small>This page sends POST requests to <code>/control</code> with your key in the <code>X-API-Key</code> header.</small></p>
<pre id="out">Click a button to see the response...</pre>
<script>
async function go(action){
  const key = document.getElementById('k').value;
  const r = await fetch('/control', {method:'POST',headers:{'Content-Type':'application/json','X-API-Key':key},body: JSON.stringify({action})});
  document.getElementById('out').textContent = await r.text();
}
</script></body></html>'''

from routes import control, config, report, candles, control_get
app.include_router(control.router)
app.include_router(config.router)
app.include_router(report.router)
app.include_router(candles.router)
app.include_router(control_get.router)

@app.get("/")
def index():
    return {"ok": True, "routes": ["/health","/control","/control/get","/control-panel","/config","/report","/candles"]}
