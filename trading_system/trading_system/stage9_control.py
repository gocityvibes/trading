import re
import json
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from config import Config, FilterConfig
from database import init_database, Candidate, Trade, Label, OptimizationReport
from stage8_orchestrator import Orchestrator
from stage7_backtest import WalkForwardBacktester

class Controller:
    """Stage 9: Natural-language control layer.
    Supported intents (examples in `help_text()`):
      - "turn on/off gpt" → toggles Config.GPT_ENABLED
      - "trade ES 5m only" / "symbols ES,NQ timeframes 5m" → sets working lists (process-level)
      - "orchestrate [days 3] [provider openai] [model gpt-3.5]" → runs the full pipeline
      - "report" / "report recent 20" → prints summary and recent trades
      - "ab test {json-config}" → backtest current vs provided FilterConfig on same windows
      - "set filters {json-config}" → updates active FilterConfig (in-memory) or persist via FilterHistory if "--persist" outside this layer
    Note: This layer changes the *current process* Config; persist via Stage 6 approval if desired.
    """
    def __init__(self, session):
        self.session = session
        self.symbols = Config.SYMBOLS[:]
        self.timeframes = Config.TIMEFRAMES[:]

    def help_text(self) -> str:
        return (
            "Commands:\n"
            "  turn off gpt | turn on gpt\n"
            "  symbols ES timeframes 5m\n"
            "  trade ES 5m only\n"
            "  orchestrate days 3 provider openai model gpt-3.5\n"
            "  report [recent N]\n"
            "  ab test {\"rsi14_buy\":25,\"ema_fast\":8,\"ema_slow\":21}\n"
            "  set filters {json}\n"
        )

    # -------- intents --------

    def _parse_list(self, s: str) -> List[str]:
        return [x.strip().upper() for x in re.split(r"[ ,]+", s) if x.strip()]

    def cmd_toggle_gpt(self, on: bool) -> Dict[str, Any]:
        Config.GPT_ENABLED = bool(on)
        return {"ok": True, "gpt_enabled": Config.GPT_ENABLED}

    def cmd_set_symbols_timeframes(self, symbols: List[str], tfs: List[str]) -> Dict[str, Any]:
        self.symbols = symbols or self.symbols
        self.timeframes = tfs or self.timeframes
        return {"ok": True, "symbols": self.symbols, "timeframes": self.timeframes}

    def cmd_orchestrate(self, days: int = 0, provider: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        if provider: Config.GPT_PROVIDER = provider
        if model: Config.GPT_MODEL_KEY = model
        orch = Orchestrator(self.session)
        orch.run_once(days=days, symbols=self.symbols, timeframes=self.timeframes,
                      provider=Config.GPT_PROVIDER, model_key=Config.GPT_MODEL_KEY)
        return {"ok": True}

    def cmd_report(self, recent: int = 20) -> Dict[str, Any]:
        total_cands = self.session.query(Candidate).count()
        total_trades = self.session.query(Trade).count()
        total_labels = self.session.query(Label).count()
        last_trades = (self.session.query(Trade).order_by(Trade.entry_time.desc()).limit(recent).all())
        pnl_sum = sum(t.pnl for t in last_trades)
        win_rate = (sum(1 for t in last_trades if t.pnl_ticks >= 0) / len(last_trades)) if last_trades else 0.0
        last_reports = (self.session.query(OptimizationReport).order_by(OptimizationReport.created_at.desc()).limit(3).all())
        return {
            "candidates": total_cands,
            "trades": total_trades,
            "labels": total_labels,
            "recent_trades": [
                dict(id=t.id, symbol=t.symbol, dir=t.direction, entry=str(t.entry_time),
                     exit=str(t.exit_time), pnl=t.pnl, pnl_ticks=t.pnl_ticks, reason=t.exit_reason)
                for t in last_trades
            ],
            "recent_pnl": pnl_sum,
            "recent_win_rate": win_rate,
            "optimization_reports": [
                dict(id=r.id, stat_sig=r.statistical_significance, approved=r.approved) for r in last_reports
            ],
            "gpt_enabled": Config.GPT_ENABLED,
            "provider": Config.GPT_PROVIDER,
            "model": Config.GPT_MODEL_KEY,
            "symbols": self.symbols,
            "timeframes": self.timeframes,
        }

    def _cfg_from_json(self, js: Dict[str, Any]) -> FilterConfig:
        base = Config.FILTERS.to_dict()
        base.update(js or {})
        return FilterConfig.from_dict(base)

    def cmd_ab_test(self, js_cfg: Dict[str, Any], train_days: int = Config.WALK_FORWARD_TRAIN_DAYS, test_days: int = Config.WALK_FORWARD_TEST_DAYS, steps: int = 2) -> Dict[str, Any]:
        # current config vs candidate
        from stage6_optimization import Optimizer
        bt = WalkForwardBacktester(self.session)
        cand_cfg = self._cfg_from_json(js_cfg)
        res_A = bt.run(train_days=train_days, test_days=test_days, steps=steps, symbols=self.symbols, timeframes=self.timeframes, filt_cfg=Config.FILTERS)
        res_B = bt.run(train_days=train_days, test_days=test_days, steps=steps, symbols=self.symbols, timeframes=self.timeframes, filt_cfg=cand_cfg)
        diff = {
            "test_avg_win_rate_delta": (res_B["test_avg_win_rate"] - res_A["test_avg_win_rate"]),
            "test_total_pnl_delta": (res_B["test_total_pnl"] - res_A["test_total_pnl"])
        }
        return {"A_current": res_A, "B_candidate": res_B, "delta": diff}

    def cmd_set_filters(self, js_cfg: Dict[str, Any]) -> Dict[str, Any]:
        new_cfg = self._cfg_from_json(js_cfg)
        Config.FILTERS = new_cfg
        return {"ok": True, "filters": new_cfg.to_dict()}

    # -------- natural-language dispatcher --------

    def handle(self, text: str) -> Dict[str, Any]:
        t = text.strip().lower()

        if t in ("help", "?", "commands"):
            return {"help": self.help_text()}

        # toggle gpt
        if re.search(r"\bturn\s+off\s+gpt\b", t):
            return self.cmd_toggle_gpt(False)
        if re.search(r"\bturn\s+on\s+gpt\b", t):
            return self.cmd_toggle_gpt(True)

        # symbols/timeframes
        m = re.search(r"symbols\s+([a-z0-9, ]+)\s+timeframes\s+([a-z0-9, ]+)", t)
        if m:
            syms = self._parse_list(m.group(1))
            tfs = [x.strip() for x in re.split(r"[ ,]+", m.group(2)) if x.strip()]
            return self.cmd_set_symbols_timeframes(syms, tfs)

        m = re.search(r"trade\s+([a-z0-9, ]+)\s+(1m|3m|5m|15m|30m|60m|1h)\s+only", t)
        if m:
            syms = self._parse_list(m.group(1))
            tf = m.group(2)
            return self.cmd_set_symbols_timeframes(syms, [tf])

        # orchestrate
        if t.startswith("orchestrate"):
            days = 0
            provider = None
            model = None
            md = re.search(r"days\s+(\d+)", t); days = int(md.group(1)) if md else 0
            mp = re.search(r"provider\s+(openai|anthropic)", t); provider = mp.group(1) if mp else None
            mm = re.search(r"model\s+(gpt-3\.5|gpt-4\.0)", t); model = mm.group(1) if mm else None
            return self.cmd_orchestrate(days=days, provider=provider, model=model)

        # report
        if t.startswith("weekly report") or t == "report last week" or t == "weekly pnl":
            return self.cmd_weekly_gpt_report()

        if t.startswith("report") or t == "report":
            recent = 20
            mr = re.search(r"recent\s+(\d+)", t); recent = int(mr.group(1)) if mr else 20
            return self.cmd_report(recent=recent)

        # set filters
        if t.startswith("set filters"):
            js = t.split("set filters", 1)[1].strip()
            data = json.loads(js) if js else {}
            return self.cmd_set_filters(data)

        # ab test
        if t.startswith("ab test"):
            js = t.split("ab test", 1)[1].strip()
            data = json.loads(js) if js else {}
            return self.cmd_ab_test(data)

        # nlp fallback: ask GPT to parse into structured intent
        parsed = self._nlp_intent(text)
        intent = parsed.get('intent','')
        params = parsed.get('params',{}) if isinstance(parsed.get('params',{}), dict) else {}
        if intent == 'report':
            days = int(params.get('recent_days', 7))
            # simple reuse: weekly path only supports 7; for arbitrary days reuse report() with slice
            return self.cmd_report(recent=9999)
        if intent == 'orchestrate':
            return self.cmd_orchestrate(days=int(params.get('days',0)), provider=params.get('provider'), model=params.get('model'))
        if intent == 'set_filters':
            return self.cmd_set_filters(params.get('filters', {}))
        if intent == 'ab_test':
            return self.cmd_ab_test(params.get('filters', {}), params.get('train_days', 21), params.get('test_days', 7), params.get('steps', 2))
        if intent == 'toggle_gpt':
            return self.cmd_toggle_gpt(bool(params.get('enabled', True)))
        if intent == 'trade_compare_window':
            return self.cmd_trade_compare_window(days=int(params.get('days', 7)), cfgA=params.get('A', {}), cfgB=params.get('B', {}))
        if intent == 'ask' or not intent:
            # Fallback: treat the whole text as a question over the DB
            return self.cmd_ask(text)
        return {"ok": False, "error": "Unrecognized command after NLP parse."}

    def _call_openai_report(self, prompt: str, provider: str = None, model_key: str = None) -> str:
        provider = provider or Config.GPT_PROVIDER
        model_key = model_key or Config.GPT_MODEL_KEY
        model = Config.resolve_model(provider, model_key)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=Config.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "You are a concise trading performance analyst. Write clear, bullet-friendly summaries with numbers."},
                    {"role": "user", "content": prompt}
                ]
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"[report generation failed: {e}]"

    def cmd_weekly_gpt_report(self, provider: str = None, model_key: str = None) -> dict:
        now = dt.datetime.utcnow()
        start = now - dt.timedelta(days=7)
        trades = (self.session.query(Trade)
                  .filter(Trade.entry_time >= start)
                  .order_by(Trade.entry_time.asc())
                  .all())

        total_pnl = sum(t.pnl for t in trades) if trades else 0.0
        win = sum(1 for t in trades if t.pnl_ticks >= 0)
        count = len(trades)
        win_rate = (win / count) if count else 0.0

        # per symbol/tf
        per_bucket = {}
        for t in trades:
            key = f"{t.symbol}:{getattr(t, 'timeframe', 'NA')}"  # timeframe not stored in Trade; keep NA
            b = per_bucket.setdefault(key, dict(trades=0, pnl=0.0, wins=0))
            b['trades'] += 1
            b['pnl'] += float(t.pnl or 0.0)
            b['wins'] += 1 if (t.pnl_ticks or 0) >= 0 else 0

        # collect unique filter configs used
        unique_filters = []
        seen = set()
        for t in trades:
            cfg = t.filter_config or {}
            # create a deterministic signature
            sig = json.dumps(cfg, sort_keys=True)
            if sig not in seen:
                seen.add(sig)
                unique_filters.append(cfg)

        # Build prompt
        summary = {
            "range": {"start_utc": start.isoformat(), "end_utc": now.isoformat()},
            "overall": {"trades": count, "win_rate": win_rate, "total_pnl": total_pnl},
            "buckets": [
                {"bucket": k, "trades": v["trades"], "win_rate": (v["wins"]/v["trades"]) if v["trades"] else 0.0, "pnl": v["pnl"]}
                for k, v in sorted(per_bucket.items())
            ],
            "filters_used": unique_filters
        }

        prompt = (
            "Generate a trading performance report for the last 7 days.\n"
            "Use the JSON below. Include: executive summary, overall PnL and win rate, per-bucket highlights,\n"
            "and a concise bullet list of the filter settings observed. Keep it crisp.\n\n"
            f"JSON:\n{json.dumps(summary, indent=2)}"
        )

        report = self._call_openai_report(prompt, provider=provider, model_key=model_key)
        return {"ok": True, "data": summary, "report": report}
    

    # ---------- GPT-powered intent parsing ----------
    def _nlp_intent(self, text: str) -> dict:
        """Ask GPT to convert freeform user text into a structured intent JSON.
        Expected schema:
        {
          "intent": "<one of: report, orchestrate, set_filters, ab_test, toggle_gpt, trade_compare_window>",
          "params": { ... }
        }
        Examples of params:
          - report: {"recent_days": 7}
          - orchestrate: {"days": 3, "provider": "openai", "model": "gpt-3.5"}
          - set_filters: {"filters": {...}}
          - ab_test: {"filters": {...}, "train_days": 21, "test_days": 7, "steps": 2}
          - toggle_gpt: {"enabled": true}
          - trade_compare_window: {"days": 7, "A": {...}, "B": {...}}
        """
        system = (
            "You convert natural language control requests for a trading pipeline into STRICT JSON. "
            "Do not explain. Only output JSON. "
            "If dates like 'last week' are mentioned, convert to days=7. "
            "Recognize synonyms like 'turn off gpt', 'pause gpt', 'gpt off'."
        )
        examples = [
            {"in": "give me pnl for last week and filters used", "out": {"intent":"report","params":{"recent_days":7}}},
            {"in": "run full pipeline for ES 5m today with gpt-3.5", "out": {"intent":"orchestrate","params":{"days":1,"provider":"openai","model":"gpt-3.5"}}},
            {"in": "trade 1 week two different filter settings", "out": {"intent":"trade_compare_window","params":{"days":7,"A":{},"B":{}}}},
            {"in": "gpt off", "out": {"intent":"toggle_gpt","params":{"enabled":false}}},
        ]
        prompt = {
            "system": system,
            "examples": examples,
            "user": text
        }
        try:
            from openai import OpenAI
            client = OpenAI(api_key=Config.OPENAI_API_KEY)
            model = Config.resolve_model(Config.GPT_PROVIDER, Config.GPT_MODEL_KEY)
            content = (
                "Convert the request into a single JSON object (no prose).\n"
                f"Context examples: {json.dumps(examples)}\n"
                f"User: {text}"
            )
            resp = client.chat.completions.create(
                model=model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": content},
                ]
            )
            raw = resp.choices[0].message.content
            # try parse
            data = None
            try:
                data = json.loads(raw)
            except Exception:
                # best effort: extract {...}
                import re as _re
                m = _re.search(r"\{.*\}", raw, flags=_re.DOTALL)
                data = json.loads(m.group(0)) if m else {}
            if not isinstance(data, dict):
                data = {}
            return data
        except Exception as e:
            return {"intent":"", "params":{}, "error": f"parser failed: {e}"}
    
    def cmd_trade_compare_window(self, days: int, cfgA: dict, cfgB: dict) -> dict:
        from stage6_optimization import Optimizer
        opt = Optimizer(self.session)
        end = dt.datetime.utcnow()
        start = end - dt.timedelta(days=days)

        # Build configs
        A = self._cfg_from_json(cfgA or {})
        B = self._cfg_from_json(cfgB or {})

        # Run A
        trades_A = opt._rescan_execute_window(self.symbols, self.timeframes, start, end, A)
        mA = opt._metrics_from_trades(trades_A)

        # Run B
        trades_B = opt._rescan_execute_window(self.symbols, self.timeframes, start, end, B)
        mB = opt._metrics_from_trades(trades_B)

        delta = {
            "win_rate_delta": (mB["win_rate"] - mA["win_rate"]),
            "total_pnl_delta": (mB["total_pnl"] - mA["total_pnl"]),
            "sharpe_delta": (mB["sharpe"] - mA["sharpe"]),
            "max_drawdown_delta": (mB["max_drawdown"] - mA["max_drawdown"]),
        }

        # Build a small JSON and ask GPT to summarize the A/B outcome
        summary = {"window_days": days, "symbols": self.symbols, "timeframes": self.timeframes,
                   "A_metrics": mA, "B_metrics": mB, "delta": delta, "A_cfg": A.to_dict(), "B_cfg": B.to_dict()}
        prompt = (
            "Write a concise A/B trade performance comparison for the specified window. "
            "Include a verdict (A vs B), highlight win rate, PnL, drawdown, and any trade-offs. "
            "Return short bullet points and a one-line recommendation.\n\nJSON:\n"
            + json.dumps(summary, indent=2)
        )
        narrative = self._call_openai_report(prompt)

        return {"ok": True, "window": {"start_utc": start.isoformat(), "end_utc": end.isoformat()}, "A": mA, "B": mB, "delta": delta, "report": narrative}
    
    # ---------- Universal ASK: schema → GPT SQL → execute → summarize ----------
    def _db_schema_summary(self) -> str:
        from database import Candle, Candidate, Trade, Label, FilterHistory, OptimizationReport
        schema = {
            "candles_raw": ["id","symbol","timeframe","timestamp","open","high","low","close","volume","atr","rsi14","rsi5","rsi2","ema_fast","ema_slow","vwap"],
            "candidates": ["id","symbol","timeframe","timestamp","candle_id","atr","rsi14","rsi5","rsi2","ema_cross","volume_surge","vwap_dev","gpt_score","gpt_reasoning","direction","created_at"],
            "trades": ["id","candidate_id","symbol","direction","entry_time","entry_price","position_size","exit_time","exit_price","exit_reason","stop_loss","take_profit","pnl","pnl_ticks","mfe","mae","bars_held","filter_config","gpt_score","created_at"],
            "labels": ["id","trade_id","label_type","win","pnl","mfe_ratio","mae_ratio","bars_to_target","bars_to_stop","setup_context","created_at"],
            "filter_history": ["id","config","reason","is_active","trades_count","win_rate","total_pnl","sharpe_ratio","max_drawdown","created_at","deactivated_at"],
            "optimization_reports": ["id","train_start","train_end","test_start","test_end","old_config","new_config","reasoning","old_results","new_results","statistical_significance","approved","approved_by","rejection_reason","created_at"]
        }
        return json.dumps(schema, indent=2)

    def _gpt_to_sql(self, question: str, schema_json: str) -> str:
        system = (
            "You write STRICT, READ-ONLY SQL for SQLite, based on the provided schema. "
            "Only use SELECT, WHERE, GROUP BY, ORDER BY, LIMIT. Never write DML/DDL."
        )
        user = (
            "Schema (tables→columns):\n" + schema_json + "\n\n"
            "Write ONE SELECT query that answers:\n" + question + "\n"
            "Rules: LIMIT 1000 max. Use ISO timestamps. Only columns in schema. Return SQL only."
        )
        try:
            from openai import OpenAI
            client = OpenAI(api_key=Config.OPENAI_API_KEY)
            model = Config.resolve_model(Config.GPT_PROVIDER, Config.GPT_MODEL_KEY)
            resp = client.chat.completions.create(
                model=model, temperature=0.0,
                messages=[{"role":"system","content":system},{"role":"user","content":user}]
            )
            sql = resp.choices[0].message.content.strip()
            # extract code if fenced
            m = re.search(r"SELECT[\s\S]*", sql, flags=re.IGNORECASE)
            return m.group(0).strip().rstrip(';') + " LIMIT 1000"
        except Exception as e:
            return f"-- ERROR: {e}"

    def _execute_safe_sql(self, sql: str):
        if not re.match(r"^\s*select\s", sql, flags=re.IGNORECASE):
            raise ValueError("Only SELECT queries are allowed.")
        forbidden = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|pragma|vacuum)\b", re.IGNORECASE)
        if forbidden.search(sql):
            raise ValueError("Forbidden SQL keyword detected.")
        # execute
        from sqlalchemy import text
        self.session.flush()
        conn = self.session.bind.connect()
        try:
            res = conn.execute(text(sql))
            rows = [dict(r._mapping) for r in res]
            return rows
        finally:
            conn.close()

    def _gpt_summarize_rows(self, question: str, rows: list) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=Config.OPENAI_API_KEY)
            model = Config.resolve_model(Config.GPT_PROVIDER, Config.GPT_MODEL_KEY)
            prompt = (
                "Answer the user's question using ONLY the table rows below. "
                "Be concise and numeric where possible; include totals, averages, and time ranges if relevant.\n\n"
                f"Question: {question}\n"
                f"Rows JSON (limit 50 shown):\n{json.dumps(rows[:50], default=str, indent=2)}"
            )
            resp = client.chat.completions.create(
                model=model, temperature=0.2,
                messages=[{"role":"system","content":"You are a precise trading data analyst."},
                          {"role":"user","content":prompt}]
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"[summary failed: {e}]"

    def cmd_ask(self, question: str) -> dict:
        schema = self._db_schema_summary()
        sql = self._gpt_to_sql(question, schema)
        try:
            rows = self._execute_safe_sql(sql)
        except Exception as e:
            return {"ok": False, "error": str(e), "sql": sql}
        report = self._gpt_summarize_rows(question, rows)
        return {"ok": True, "sql": sql, "rows": rows[:50], "report": report}
    