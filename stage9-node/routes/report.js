import express from "express";
import pkg from "pg";
const { Pool } = pkg;
const router = express.Router();
const pool = new Pool({ connectionString: process.env.DATABASE_URL });

function requireKey(req, res, next) {
  const k = req.header("X-API-Key");
  if (!process.env.API_KEY) return res.status(500).json({ ok:false, error:"API_KEY not set" });
  if (k !== process.env.API_KEY) return res.status(401).json({ ok:false, error:"Unauthorized" });
  next();
}

/* expects table trades(ts_utc timestamptz, symbol text, side text, points numeric, pnl numeric, label text, exit_reason text) */
router.post("/", requireKey, async (req, res) => {
  try {
    const { type, days=10, min_points, label, symbol } = req.body || {};
    const since = `${days} days`;
    if (type === "win_loss") {
      const sql = `
        with r as (
          select date(ts_utc) d,
                 count(*) total,
                 sum(case when pnl>0 then 1 else 0 end) wins,
                 sum(case when pnl<=0 then 1 else 0 end) losses,
                 avg(pnl) avg_pnl
          from trades
          where ts_utc >= now() - interval '${since}'
            ${symbol ? "and symbol = $1" : ""}
          group by 1 order by 1
        )
        select *, (wins::float/nullif(total,0))::float win_rate from r;
      `;
      const rows = (await pool.query(sql, symbol ? [symbol] : [])).rows;
      return res.json({ ok:true, type, days, symbol: symbol||null, rows });
    }
    if (type === "by_label") {
      const sql = `
        select label, count(*) trades, avg(pnl) avg_pnl,
               sum(case when pnl>0 then 1 else 0 end)::float/count(*) win_rate
        from trades
        where ts_utc >= now() - interval '${since}'
          ${symbol ? "and symbol = $1" : ""}
        group by 1 order by 1;
      `;
      const rows = (await pool.query(sql, symbol ? [symbol] : [])).rows;
      return res.json({ ok:true, type, days, symbol: symbol||null, rows });
    }
    if (type === "top_moves") {
      const params = [];
      let i = 1;
      const clauses = [];
      if (min_points) { clauses.push(`abs(points) >= $${i++}`); params.push(min_points); }
      if (label)      { clauses.push(`label = $${i++}`); params.push(label); }
      if (symbol)     { clauses.push(`symbol = $${i++}`); params.push(symbol); }
      const where = clauses.length ? `and ${clauses.join(" and ")}` : "";
      const sql = `
        select ts_utc, symbol, side, points, pnl, label, exit_reason
        from trades
        where ts_utc >= now() - interval '${since}' ${where}
        order by abs(points) desc limit 100;
      `;
      const rows = (await pool.query(sql, params)).rows;
      return res.json({ ok:true, type, days, rows });
    }
    res.status(400).json({ ok:false, error:"unknown report type" });
  } catch (e) {
    res.status(500).json({ ok:false, error:e.message });
  }
});

export default router;
