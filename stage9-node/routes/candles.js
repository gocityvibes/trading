import express from "express";
import pkg from "pg";
const { Pool } = pkg;
const router = express.Router();
const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// latest candle
router.get("/latest", async (req, res) => {
  try {
    const { symbol, tf } = req.query;
    if (!symbol || !tf) return res.status(400).json({ ok:false, error:"symbol and tf required" });
    const sql = `
      select ts_utc, open, high, low, close, volume
      from candles_raw
      where symbol = $1 and timeframe = $2
      order by ts_utc desc limit 1;
    `;
    const rows = (await pool.query(sql, [symbol, tf])).rows;
    res.json({ ok:true, rows });
  } catch (e) {
    res.status(500).json({ ok:false, error:e.message });
  }
});

// recent N candles
router.get("/recent", async (req, res) => {
  try {
    const { symbol, tf, limit=5 } = req.query;
    if (!symbol || !tf) return res.status(400).json({ ok:false, error:"symbol and tf required" });
    const sql = `
      select ts_utc, open, high, low, close, volume
      from candles_raw
      where symbol = $1 and timeframe = $2
      order by ts_utc desc limit $3;
    `;
    const rows = (await pool.query(sql, [symbol, tf, limit])).rows;
    res.json({ ok:true, rows });
  } catch (e) {
    res.status(500).json({ ok:false, error:e.message });
  }
});

// count since interval
router.get("/count", async (req, res) => {
  try {
    const { symbol, tf, since="1h" } = req.query;
    if (!symbol || !tf) return res.status(400).json({ ok:false, error:"symbol and tf required" });
    const sql = `
      select count(*)::int as count
      from candles_raw
      where symbol = $1 and timeframe = $2
        and ts_utc >= now() - interval '${"$"}{since}';
    `;
    const rows = (await pool.query(sql, [symbol, tf])).rows;
    res.json({ ok:true, count: rows[0]?.count ?? 0 });
  } catch (e) {
    res.status(500).json({ ok:false, error:e.message });
  }
});

export default router;
