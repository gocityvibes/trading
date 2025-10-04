
# Trading Control (FastAPI)

Simple FastAPI app that exposes these endpoints:

- `GET /health` – health check
- `GET /control/get?action=start|stop|status&key=YOUR_KEY` – start/stop/status
- `GET /control-panel` – buttons that call the endpoints (key embedded URL-encoded)

## Quick Start (Local)

```bash
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
export CONTROL_KEY="jcpclov3$$"   # Windows PowerShell: $Env:CONTROL_KEY='jcpclov3$$'
uvicorn app.main:app --host 0.0.0.0 --port 10000
```

Open:
- http://localhost:10000/health
- http://localhost:10000/control-panel
- http://localhost:10000/control/get?action=status&key=jcpclov3%24%24

## Deploy on Render

1. Create a **Web Service** from your repo.
2. **Environment**: add `CONTROL_KEY` with your exact key (e.g. `jcpclov3$$`).
3. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Deploy. Then visit:
   - `https://<your-service>.onrender.com/health`
   - `https://<your-service>.onrender.com/control-panel`
   - `https://<your-service>.onrender.com/control/get?action=start&key=jcpclov3%24%24`
   - `https://<your-service>.onrender.com/control/get?action=status&key=jcpclov3%24%24`

## Notes

- `$` must be URL-encoded as `%24` inside query strings. The control panel handles this automatically.
- The in-memory `STATE["trading"]` flag is for switching on/off. Wire it to your trading loop as needed.
