import express from "express";
const router = express.Router();

function requireKey(req, res, next) {
  const k = req.header("X-API-Key");
  if (!process.env.API_KEY) return res.status(500).json({ ok:false, error:"API_KEY not set" });
  if (k !== process.env.API_KEY) return res.status(401).json({ ok:false, error:"Unauthorized" });
  next();
}

globalThis.__RUNTIME_CONFIG__ = globalThis.__RUNTIME_CONFIG__ || {
  filters: { atr_min:1.0, atr_max:15.0, rsi14_buy:30.0, rsi14_sell:70.0, ema_fast:9, ema_slow:21 },
};

router.get("/", requireKey, (req, res) => {
  res.json({ ok:true, config: globalThis.__RUNTIME_CONFIG__ });
});

router.post("/", requireKey, (req, res) => {
  const { filters } = req.body || {};
  if (filters && typeof filters === "object") {
    globalThis.__RUNTIME_CONFIG__.filters = { ...globalThis.__RUNTIME_CONFIG__.filters, ...filters };
  }
  res.json({ ok:true, config: globalThis.__RUNTIME_CONFIG__ });
});

export default router;
