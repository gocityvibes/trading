from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy import and_, asc

from config import Config, FilterConfig
from database import Candle
from stage2_filter import TripleRSIFilter
from stage4_execution import PaperExecutor

class WalkForwardBacktester:
    """
    Stage 7: Walk-forward backtest using current DB candles.
    For each step:
      - TRAIN N days: set filters (current or candidate) and run Stage2+Stage4 to generate trades.
      - TEST M days: run Stage2+Stage4 with *same* filters and compute metrics.
    Returns a JSON-like dict with summary.
    """

    def __init__(self, session):
        self.session = session

    def _metrics(self, trades) -> Dict[str, Any]:
        if not trades:
            return dict(count=0, win_rate=0.0, pnl=0.0)
        pnl = [t.pnl for t in trades]
        wins = [1 for t in trades if t.pnl_ticks >= 0]
        return dict(count=len(trades), win_rate=sum(wins)/len(trades), pnl=sum(pnl))

    def _time_has_candles(self, start: datetime, end: datetime) -> bool:
        c = (self.session.query(Candle)
             .filter(and_(Candle.timestamp >= start, Candle.timestamp < end))
             .first())
        return c is not None

    def run(self,
            train_days: int = Config.WALK_FORWARD_TRAIN_DAYS,
            test_days: int = Config.WALK_FORWARD_TEST_DAYS,
            steps: int = 2,
            symbols=None,
            timeframes=None,
            filt_cfg: FilterConfig = None) -> Dict[str, Any]:
        symbols = symbols or Config.SYMBOLS
        timeframes = timeframes or Config.TIMEFRAMES
        filt_cfg = filt_cfg or Config.FILTERS

        end = datetime.utcnow()
        window = train_days + test_days

        results = []
        for k in range(steps, 0, -1):
            test_end = end - timedelta(days=(steps - k) * window)
            train_start = test_end - timedelta(days=window)
            train_end = test_end - timedelta(days=test_days)
            test_start = train_end

            if not self._time_has_candles(train_start, test_end):
                continue

            # Use Stage 6 method: rescan/execute in each window with given filt_cfg
            from stage6_optimization import Optimizer
            opt = Optimizer(self.session)

            _ = opt._rescan_execute_window(symbols, timeframes, train_start, train_end, filt_cfg)
            train_trades = opt._trades_between(train_start, train_end)

            _ = opt._rescan_execute_window(symbols, timeframes, test_start, test_end, filt_cfg)
            test_trades = opt._trades_between(test_start, test_end)

            m_train = self._metrics(train_trades)
            m_test = self._metrics(test_trades)

            results.append(dict(
                train=dict(start=train_start.isoformat(), end=train_end.isoformat(), **m_train),
                test=dict(start=test_start.isoformat(), end=test_end.isoformat(), **m_test)
            ))

        # aggregate
        agg = dict(
            steps=len(results),
            train_avg_win_rate=float(pd.Series([r['train']['win_rate'] for r in results]).mean()) if results else 0.0,
            test_avg_win_rate=float(pd.Series([r['test']['win_rate'] for r in results]).mean()) if results else 0.0,
            test_total_pnl=float(pd.Series([r['test']['pnl'] for r in results]).sum()) if results else 0.0,
            detail=results
        )
        return agg
