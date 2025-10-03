from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy import asc
import pandas as pd

from config import Config
from database import Candle, Candidate, Trade
from utils import ticks_to_price

class PaperExecutor:
    """
    Stage 4: Paper execution with bracket exits (TP/SL) and MFE/MAE tracking.

    Logic:
      - Find Candidates with gpt_score >= threshold and direction in {'long','short'} and no Trade yet.
      - Enter on the **next bar open** after candidate timestamp.
      - Compute stop/target using STOP_LOSS_TICKS / TAKE_PROFIT_TICKS and symbol tick size.
      - Step forward bar-by-bar until stop or target hit; otherwise exit by EOD/MaxBars rule.
      - Track MFE (max favorable) / MAE (max adverse) in price; store pnl, pnl_ticks, bars_held, exit_reason.
    """

    # conservative hold cap to avoid “overnight” on intraday bars
    MAX_HOLD_BARS = 60  # adjust if you want a stricter/looser cap per TF

    def __init__(self, session):
        self.session = session

    def _load_frame(self, symbol: str, timeframe: str, start_ts: datetime, limit: int = 5000) -> pd.DataFrame:
        q = (self.session.query(Candle)
             .filter(Candle.symbol == symbol,
                     Candle.timeframe == timeframe,
                     Candle.timestamp >= start_ts)
             .order_by(asc(Candle.timestamp))
             .limit(limit))
        rows = q.all()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([{
            'id': r.id, 'ts': r.timestamp, 'open': r.open, 'high': r.high, 'low': r.low, 'close': r.close,
            'volume': r.volume
        } for r in rows])
        return df

    def _entry_row_after(self, df: pd.DataFrame, ts: datetime) -> Optional[int]:
        if df.empty:
            return None
        idx = df.index[df['ts'] > ts]
        if len(idx) == 0:
            return None
        return int(idx[0])

    def _simulate(self, df: pd.DataFrame, start_i: int, direction: str, tick_size: float,
                  stop_ticks: int, target_ticks: int) -> Tuple[int, float, str, float, float]:
        """
        Step forward from start_i, return:
          exit_index, exit_price, exit_reason, MFE_price, MAE_price
        """
        entry_open = float(df.iloc[start_i]['open'])
        stop_price = ticks_to_price(entry_open, stop_ticks, tick_size, 'short' if direction == 'long' else 'long')
        target_price = ticks_to_price(entry_open, target_ticks, tick_size, direction)

        mfe = 0.0  # measured as favorable price distance (abs) from entry
        mae = 0.0  # measured as adverse price distance (abs) from entry

        for i in range(start_i, min(len(df), start_i + self.MAX_HOLD_BARS)):
            bar = df.iloc[i]
            high = float(bar['high'])
            low = float(bar['low'])

            if direction == 'long':
                # favorable move is high - entry; adverse is entry - low
                mfe = max(mfe, max(0.0, high - entry_open))
                mae = max(mae, max(0.0, entry_open - low))
                # check exits
                if high >= target_price:
                    return i, target_price, 'target', mfe, mae
                if low <= stop_price:
                    return i, stop_price, 'stop', mfe, mae
            else:  # short
                # favorable move is entry - low; adverse is high - entry
                mfe = max(mfe, max(0.0, entry_open - low))
                mae = max(mae, max(0.0, high - entry_open))
                if low <= target_price:
                    return i, target_price, 'target', mfe, mae
                if high >= stop_price:
                    return i, stop_price, 'stop', mfe, mae

        # if not exited by cap, exit at last close (EOD-like)
        last = df.iloc[min(len(df)-1, start_i + self.MAX_HOLD_BARS - 1)]
        return int(min(len(df)-1, start_i + self.MAX_HOLD_BARS - 1)), float(last['close']), 'eod', mfe, mae

    def execute_new_trades(self, symbols=None, timeframes=None) -> int:
        symbols = symbols or Config.SYMBOLS
        timeframes = timeframes or Config.TIMEFRAMES
        created = 0

        # query untraded, scored candidates
        q = (self.session.query(Candidate)
             .filter(Candidate.gpt_score.isnot(None))
             .filter(Candidate.gpt_score >= Config.GPT_SCORE_THRESHOLD)
             .filter(Candidate.direction.in_(('long', 'short')))
             .order_by(asc(Candidate.timestamp)))

        existing_cand_ids = {t.candidate_id for t in self.session.query(Trade.candidate_id)}
        rows = [c for c in q.all() if c.id not in existing_cand_ids and c.symbol in symbols and c.timeframe in timeframes]
        if not rows:
            return 0

        for cand in rows:
            tick_size = Config.TICK_SIZE.get(cand.symbol, 0.25)
            df = self._load_frame(cand.symbol, cand.timeframe, cand.timestamp)
            start_i = self._entry_row_after(df, cand.timestamp)
            if start_i is None:
                continue

            # simulate forward
            exit_i, exit_price, exit_reason, mfe_price, mae_price = self._simulate(
                df=df,
                start_i=start_i,
                direction=cand.direction,
                tick_size=tick_size,
                stop_ticks=Config.STOP_LOSS_TICKS,
                target_ticks=Config.TAKE_PROFIT_TICKS
            )

            entry_bar = df.iloc[start_i]
            exit_bar = df.iloc[exit_i]
            entry_price = float(entry_bar['open'])

            # pnl in ticks
            diff = exit_price - entry_price
            if cand.direction == 'short':
                diff = -diff
            pnl_ticks = int(round(diff / tick_size))
            pnl = pnl_ticks * tick_size  # price delta (ticks * tick_size)

            # compute favorable/adverse in ticks
            mfe_ticks = int(round(mfe_price / tick_size))
            mae_ticks = int(round(mae_price / tick_size))

            t = Trade(
                candidate_id=cand.id,
                symbol=cand.symbol,
                direction=cand.direction,
                entry_time=pd.to_datetime(entry_bar['ts']),
                entry_price=entry_price,
                position_size=1,  # simple 1-contract paper position
                exit_time=pd.to_datetime(exit_bar['ts']),
                exit_price=exit_price,
                exit_reason=exit_reason,
                stop_loss=ticks_to_price(entry_price, Config.STOP_LOSS_TICKS, tick_size,
                                         'short' if cand.direction == 'long' else 'long'),
                take_profit=ticks_to_price(entry_price, Config.TAKE_PROFIT_TICKS, tick_size, cand.direction),
                pnl=float(pnl),
                pnl_ticks=int(pnl_ticks),
                mfe=float(mfe_price),
                mae=float(mae_price),
                bars_held=int(exit_i - start_i + 1),
                filter_config=Config.FILTERS.to_dict(),
                gpt_score=float(cand.gpt_score) if cand.gpt_score is not None else None
            )
            self.session.add(t)
            self.session.commit()
            created += 1

        return created
