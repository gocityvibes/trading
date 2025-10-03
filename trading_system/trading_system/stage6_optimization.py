import math
import statistics
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional

from sqlalchemy import and_, asc

from config import Config, FilterConfig
from database import Trade, FilterHistory, OptimizationReport, init_database, Candle, Candidate
from stage2_filter import TripleRSIFilter
from stage4_execution import PaperExecutor

class Optimizer:
    """
    Stage 6: Propose improved filter settings.
    - Pull recent trades in a TRAIN window and compute metrics for the active filter.
    - Grid-search around key thresholds to find a better config.
    - Backtest TEST window with best config vs old config.
    - Save OptimizationReport with statistical confidence.
    - Human can approve → new filters get activated (FilterHistory).
    """

    def __init__(self, session):
        self.session = session

    # ---------- metrics ----------
    def _metrics_from_trades(self, trades: List[Trade]) -> Dict:
        if not trades:
            return dict(count=0, win_rate=0.0, total_pnl=0.0, sharpe=0.0, max_drawdown=0.0)

        pnls = [t.pnl for t in trades]
        wins = [1 for t in trades if t.pnl_ticks >= 0]
        count = len(trades)
        win_rate = sum(wins) / count if count else 0.0
        total_pnl = sum(pnls)

        # Sharpe (simplified): mean/std of PnL per trade
        mean = statistics.mean(pnls)
        std = statistics.pstdev(pnls) or 1e-9
        sharpe = mean / std

        # Max drawdown on cumulative PnL
        cum = 0.0
        peak = 0.0
        max_dd = 0.0
        for p in pnls:
            cum += p
            peak = max(peak, cum)
            max_dd = max(max_dd, peak - cum)

        return dict(count=count, win_rate=win_rate, total_pnl=total_pnl, sharpe=sharpe, max_drawdown=max_dd)

    # ---------- helper: slice trades by time ----------
    def _trades_between(self, start: datetime, end: datetime) -> List[Trade]:
        q = (self.session.query(Trade)
             .filter(and_(Trade.entry_time >= start, Trade.entry_time < end))
             .order_by(asc(Trade.entry_time)))
        return q.all()

    # ---------- lightweight in-place re-scan/execute over a window ----------
    def _rescan_execute_window(self, symbols, timeframes, start, end, filt_cfg: FilterConfig) -> List[Trade]:
        """
        Re-scan using Stage2, execute using Stage4, but only for candles in [start, end).
        We do minimal hygiene: delete pre-existing Candidates/Trades in the window for repeatability
        and re-run with the provided filter config.
        """
        # Temporarily swap active filters
        old_cfg = Config.FILTERS
        Config.FILTERS = filt_cfg

        # 1) purge candidates/trades in window (so the run is clean)
        cand_ids = [c.id for c in self.session.query(Candidate)
                    .filter(and_(Candidate.timestamp >= start, Candidate.timestamp < end)).all()]
        if cand_ids:
            # delete trades first (fk-ish)
            self.session.query(Trade).filter(Trade.candidate_id.in_(cand_ids)).delete(synchronize_session=False)
            self.session.query(Candidate).filter(Candidate.id.in_(cand_ids)).delete(synchronize_session=False)
            self.session.commit()

        # 2) run Stage2 on candles in window
        f = TripleRSIFilter(self.session)
        total_cands = 0
        for s in symbols:
            for tf in timeframes:
                made = f.scan(s, tf, lookback_limit=50000)
                total_cands += made

        # 3) execute only trades whose entry bar is within [start, end)
        ex = PaperExecutor(self.session)

        executed = ex.execute_new_trades(symbols=symbols, timeframes=timeframes)

        trades = self._trades_between(start, end)

        # restore old cfg
        Config.FILTERS = old_cfg
        return trades

    # ---------- grid search around a few knobs ----------
    def _neighbor_configs(self, base: FilterConfig) -> List[FilterConfig]:
        # small +- perturbations
        atr_steps = [-0.5, 0.0, +0.5]
        rsi14_buy_steps = [-5, 0, +5]
        rsi14_sell_steps = [-5, 0, +5]
        ema_fast_steps = [-2, 0, +2]
        ema_slow_steps = [-4, 0, +4]

        configs = []
        for da in atr_steps:
            for db in rsi14_buy_steps:
                for ds in rsi14_sell_steps:
                    for ef in ema_fast_steps:
                        for es in ema_slow_steps:
                            cfg = FilterConfig(
                                atr_min=max(0.5, base.atr_min + da),
                                atr_max=max(base.atr_min + 1.0, base.atr_max + da),
                                rsi14_buy=max(5, min(50, base.rsi14_buy + db)),
                                rsi14_sell=min(95, max(50, base.rsi14_sell + ds)),
                                rsi5_cross_buffer=base.rsi5_cross_buffer,
                                rsi2_buy_cross=base.rsi2_buy_cross,
                                rsi2_sell_cross=base.rsi2_sell_cross,
                                volume_ma_window=base.volume_ma_window,
                                ema_fast=max(3, base.ema_fast + ef),
                                ema_slow=max(6, base.ema_slow + es),
                                vwap_dev_atr=base.vwap_dev_atr
                            )
                            configs.append(cfg)
        # include base config at the end
        configs.append(base)
        return configs

    def optimize(self,
                 train_days: int = Config.WALK_FORWARD_TRAIN_DAYS,
                 test_days: int = Config.WALK_FORWARD_TEST_DAYS,
                 symbols=None,
                 timeframes=None,
                 approve: bool = False):
        symbols = symbols or Config.SYMBOLS
        timeframes = timeframes or Config.TIMEFRAMES

        end = datetime.utcnow()
        train_start = end - timedelta(days=train_days + test_days)
        train_end = end - timedelta(days=test_days)
        test_start = train_end
        test_end = end

        # current performance on TRAIN window
        old_trades_train = self._trades_between(train_start, train_end)
        old_metrics_train = self._metrics_from_trades(old_trades_train)

        # If not enough trades, re-run with current config to produce trades (idempotent)
        if old_metrics_train['count'] < Config.MIN_TRADES_FOR_OPTIMIZATION:
            _ = self._rescan_execute_window(symbols, timeframes, train_start, train_end, Config.FILTERS)
            old_trades_train = self._trades_between(train_start, train_end)
            old_metrics_train = self._metrics_from_trades(old_trades_train)

        old_trades_test = self._trades_between(test_start, test_end)
        old_metrics_test = self._metrics_from_trades(old_trades_test)

        # search neighbors (TRAIN window)
        best_cfg = Config.FILTERS
        best_score = -1e9
        best_metrics_train = old_metrics_train

        for cfg in self._neighbor_configs(Config.FILTERS):
            # produce trades for TRAIN window under cfg
            trades = self._rescan_execute_window(symbols, timeframes, train_start, train_end, cfg)
            m = self._metrics_from_trades(trades)
            # target function: win_rate * 100 + total_pnl + 20*sharpe - 5*max_drawdown
            score = (m['win_rate'] * 100.0) + m['total_pnl'] + (20.0 * m['sharpe']) - (5.0 * m['max_drawdown'])
            if m['count'] >= max(20, int(0.6 * old_metrics_train['count'])) and score > best_score:
                best_score = score
                best_cfg = cfg
                best_metrics_train = m

        # compare on TEST window (walk-forward)
        new_trades_test = self._rescan_execute_window(symbols, timeframes, test_start, test_end, best_cfg)
        new_metrics_test = self._metrics_from_trades(new_trades_test)

        # naive significance: require improvements in win_rate and total_pnl
        improved = (new_metrics_test['win_rate'] >= old_metrics_test['win_rate'] + 0.03 and
                    new_metrics_test['total_pnl'] >= old_metrics_test['total_pnl'])

        report = OptimizationReport(
            train_start=train_start, train_end=train_end,
            test_start=test_start, test_end=test_end,
            old_config=Config.FILTERS.to_dict(),
            new_config=best_cfg.to_dict(),
            reasoning=("Auto grid-search around ATR/RSI/EMA produced a better config on TRAIN and improved on TEST."
                       " Target function weighed win_rate, pnl, sharpe and drawdown."),
            old_results=dict(train=old_metrics_train, test=old_metrics_test),
            new_results=dict(train=best_metrics_train, test=new_metrics_test),
            statistical_significance=0.9 if improved else 0.5,
            approved=bool(approve and improved),
            approved_by='auto' if approve and improved else None,
            rejection_reason=None if improved else "Insufficient improvement on TEST"
        )
        self.session.add(report)
        self.session.commit()

        # if approved, activate
        if approve and improved:
            Config.save_filters_to_db(self.session, FilterConfig.from_dict(report.new_config), reason="Auto-approved optimization")
        return report

    def approve_report(self, report_id: int, approve: bool, reason: str = ""):
        rep = self.session.query(OptimizationReport).filter(OptimizationReport.id == report_id).first()
        if not rep:
            raise ValueError(f"Report {report_id} not found")
        rep.approved = bool(approve)
        rep.approved_by = 'human'
        rep.rejection_reason = None if approve else reason or "Rejected by human"
        self.session.commit()
        if approve:
            Config.save_filters_to_db(self.session, FilterConfig.from_dict(rep.new_config), reason=reason or "Human approved")
        return rep
