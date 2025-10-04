import os
from fastapi import APIRouter, Header, HTTPException

router = APIRouter(prefix="/config")
API_KEY = os.getenv("API_KEY")
RUNTIME_CONFIG = {"filters": {"atr_min":1.0,"atr_max":15.0,"rsi14_buy":30.0,"rsi14_sell":70.0,"ema_fast":9,"ema_slow":21}}

def check_key(x_api_key: str | None):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY not set")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("")
def get_config(x_api_key: str | None = Header(default=None)):
    check_key(x_api_key)
    return {"ok": True, "config": RUNTIME_CONFIG}

@router.post("")
def set_config(body: dict, x_api_key: str | None = Header(default=None)):
    check_key(x_api_key)
    filters = (body or {}).get("filters", {})
    if isinstance(filters, dict):
        RUNTIME_CONFIG["filters"].update(filters)
    return {"ok": True, "config": RUNTIME_CONFIG}
