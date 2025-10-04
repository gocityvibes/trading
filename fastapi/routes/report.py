import os
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text
from db import get_session

router = APIRouter(prefix="/report")
API_KEY = os.getenv("API_KEY")

def check_key(x_api_key: str | None):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY not set")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.post("")
def report(body: dict, x_api_key: str | None = Header(default=None)):
    check_key(x_api_key)
    with get_session() as s:
        typ = (body or {}).get("type")
        days = int((body or {}).get("days", 10))
        symbol = (body or {}).get("symbol")
        label = (body or {}).get("label")
        min_points = (body or {}).get("min_points")
        since = f"{days} days"
        if typ == "win_loss":
            sql = f"""
            with r as (
              select date(ts_utc) d,
                     count(*) total,
                     sum(case when pnl>0 then 1 else 0 end) wins,
                     sum(case when pnl<=0 then 1 else 0 end) losses,
                     avg(pnl) avg_pnl
              from trades
              where ts_utc >= now() - interval '{since}'
              { "and symbol = :symbol" if symbol else "" }
              group by 1 order by 1
            )
            select *, wins::float/nullif(total,0) win_rate from r;
            """
            rows = s.execute(text(sql), {"symbol": symbol} if symbol else {}).mappings().all()
            return {"ok": True, "type": typ, "days": days, "symbol": symbol, "rows": rows}
        if typ == "by_label":
            sql = f"""
            select label, count(*) trades, avg(pnl) avg_pnl,
                   sum(case when pnl>0 then 1 else 0 end)::float/count(*) win_rate
            from trades
            where ts_utc >= now() - interval '{since}'
            { "and symbol = :symbol" if symbol else "" }
            group by 1 order by 1;
            """
            rows = s.execute(text(sql), {"symbol": symbol} if symbol else {}).mappings().all()
            return {"ok": True, "type": typ, "days": days, "symbol": symbol, "rows": rows}
        if typ == "top_moves":
            clauses = []
            params = {}
            if min_points is not None:
                clauses.append("abs(points) >= :min_points")
                params["min_points"] = min_points
            if label:
                clauses.append("label = :label")
                params["label"] = label
            if symbol:
                clauses.append("symbol = :symbol")
                params["symbol"] = symbol
            where = (" and " + " and ".join(clauses)) if clauses else ""
            sql = f"""
              select ts_utc, symbol, side, points, pnl, label, exit_reason
              from trades
              where ts_utc >= now() - interval '{since}' {where}
              order by abs(points) desc limit 100;
            """
            rows = s.execute(text(sql), params).mappings().all()
            return {"ok": True, "type": typ, "days": days, "rows": rows}
        raise HTTPException(status_code=400, detail="unknown report type")
