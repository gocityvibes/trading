import express from "express";
import dotenv from "dotenv";
import pkg from "pg";
dotenv.config();

const { Pool } = pkg;
const app = express();
app.use(express.json());

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// Simple health that also pings DB
app.get("/health", async (req, res) => {
  try {
    const now = await pool.query("select now()");
    res.json({ ok: true, service: "trading", time: now.rows[0].now, trading_enabled: globalThis.__TRADING_ENABLED__ ?? true });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

// mount routers
import controlRouter from "./routes/control.js";
import configRouter from "./routes/config.js";
import reportRouter from "./routes/report.js";
import candlesRouter from "./routes/candles.js";

app.use("/control", controlRouter);
app.use("/config", configRouter);
app.use("/report", reportRouter);
app.use("/candles", candlesRouter);

// default
app.get("/", (req, res) => res.json({ ok: true, routes: ["/health","/control","/config","/report","/candles"] }));

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`Stage9 API up on ${port}`));
