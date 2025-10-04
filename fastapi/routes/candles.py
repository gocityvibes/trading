from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from db import get_session

router = APIRouter(prefix="/candles")

@router.get("/latest")
def latest(symbol: str, tf: str):
    with get_session() as s:
        rows = s.execute(text("""
            select ts_utc, open, high, low, close, volume
            from candles_raw
            where symbol = :symbol and timeframe = :tf
            order by ts_utc desc limit 1
        """), {"symbol": symbol, "tf": tf}).mappings().all()
    return {"ok": True, "rows": rows}

@router.get("/recent")
def recent(symbol: str, tf: str, limit: int = 5):
    with get_session() as s:
        rows = s.execute(text("""
            select ts_utc, open, high, low, close, volume
            from candles_raw
            where symbol = :symbol and timeframe = :tf
            order by ts_utc desc limit :limit
        """), {"symbol": symbol, "tf": tf, "limit": limit}).mappings().all()
    return {"ok": True, "rows": rows}

@router.get("/count")
def count(symbol: str, tf: str, since: str = "1h"):
    with get_session() as s:
        sql = text(f"""
            select count(*)::int as count
            from candles_raw
            where symbol = :symbol and timeframe = :tf
              and ts_utc >= now() - interval '{since}'
        """ )
        count = s.execute(sql, {"symbol": symbol, "tf": tf}).scalar()
    return {"ok": True, "count": count}
