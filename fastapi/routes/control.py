import os
from fastapi import APIRouter, Header, HTTPException

router = APIRouter(prefix="/control")

TRADING_ENABLED = {"value": True}
API_KEY = os.getenv("API_KEY")

def check_key(x_api_key: str | None):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY not set")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.post("")
def control(action: dict, x_api_key: str | None = Header(default=None)):
    check_key(x_api_key)
    act = (action or {}).get("action")
    if act == "start":
        TRADING_ENABLED["value"] = True
    elif act == "stop":
        TRADING_ENABLED["value"] = False
    elif act != "status":
        raise HTTPException(status_code=400, detail="action must be start|stop|status")
    return {"ok": True, "trading_enabled": TRADING_ENABLED["value"]}
