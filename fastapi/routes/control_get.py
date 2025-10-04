import os
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/control/get")
API_KEY = os.getenv("API_KEY")
TRADING_ENABLED = {"value": True}

@router.get("")
def control_get(action: str = Query(..., pattern="^(start|stop|status)$"), key: str = Query(...)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY not set")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if action == "start":
        TRADING_ENABLED["value"] = True
    elif action == "stop":
        TRADING_ENABLED["value"] = False
    return {"ok": True, "trading_enabled": TRADING_ENABLED["value"]}
