import express from "express";
const router = express.Router();

function requireKey(req, res, next) {
  const k = req.header("X-API-Key");
  if (!process.env.API_KEY) return res.status(500).json({ ok:false, error:"API_KEY not set" });
  if (k !== process.env.API_KEY) return res.status(401).json({ ok:false, error:"Unauthorized" });
  next();
}

// in-memory flag
globalThis.__TRADING_ENABLED__ = (globalThis.__TRADING_ENABLED__ === undefined) ? true : globalThis.__TRADING_ENABLED__;

router.post("/", requireKey, (req, res) => {
  const { action } = req.body || {};
  if (action === "start") globalThis.__TRADING_ENABLED__ = true;
  else if (action === "stop") globalThis.__TRADING_ENABLED__ = false;
  else if (action !== "status") return res.status(400).json({ ok:false, error:"action must be start|stop|status" });
  res.json({ ok:true, trading_enabled: globalThis.__TRADING_ENABLED__ });
});

export default router;
