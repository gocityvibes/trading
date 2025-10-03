# GPT-Assisted Trading System (Stages 1–8)

## Quick Start

1. **Install deps**
```bash
pip install -r requirements.txt
```

2. **Set env**
```bash
export DATABASE_URL='sqlite:///trading.db'  # or your Render Postgres URL
export OPENAI_API_KEY='sk-...'
# optional if using Anthropic:
# export ANTHROPIC_API_KEY='...'
```

3. **Run end-to-end once**
```bash
python trading_system/main.py orchestrate --days 3 --symbols ES --timeframes 5m --provider openai --model gpt-4.0
```

## Useful commands
```bash
# Collect candles + indicators
python trading_system/main.py collect --days 3

# Build triple-RSI candidates
python trading_system/main.py filter --symbols ES --timeframes 5m

# GPT-score candidates
python trading_system/main.py gpt-score --provider openai --model gpt-3.5

# Execute paper trades
python trading_system/main.py execute --symbols ES --timeframes 5m

# Label gold / hard_negative
python trading_system/main.py label

# Optimize filters (auto-approve if improved)
python trading_system/main.py optimize --approve --symbols ES --timeframes 5m

# Walk-forward backtest
python trading_system/main.py backtest --steps 2 --symbols ES --timeframes 5m
```

## Notes
- Default DB is SQLite for simplicity. Swap to Postgres by setting `DATABASE_URL` env.
- Symbols use ES/NQ/YM mapped to Yahoo futures tickers (ES=F, NQ=F, YM=F).
- GPT models toggle at runtime via CLI; JSON parsing is hardened.


## Natural-language control (Stage 9)

Examples:
```bash
python trading_system/main.py control "turn off gpt"
python trading_system/main.py control "trade ES 5m only"
python trading_system/main.py control "give me pnl for last week and filters used"
python trading_system/main.py control "trade 1 week two different filter settings: A { \"rsi14_buy\":25 } vs B { \"ema_fast\":8 }"
python trading_system/main.py control "orchestrate days 3 provider openai model gpt-3.5"
```
The control layer will fetch data, run experiments, and ask GPT to write the summary back to you.


### Ask anything (DB-aware)
You can type free text and the controller will have GPT write a safe SELECT query, run it, and summarize:
```bash
python trading_system/main.py control "what was my total pnl on ES last week and average win rate?"
python trading_system/main.py control "list the top 10 trades by pnl with exit reasons"
```
