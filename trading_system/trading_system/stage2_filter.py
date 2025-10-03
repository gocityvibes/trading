import pandas as pd
from sqlalchemy import asc
from config import Config
from database import Candle, Candidate

class TripleRSIFilter:
    """
    Stage 2: Build candidates using triple-RSI + supportive filters.
    Conditions (defaults; tweak in Config.FILTERS and Config.TRIPLE_RSI_*):
      - ATR within [atr_min, atr_max]
      - Triple RSI:
          Long: RSI14 < 30 and RSI2 crossing up through 10 (with RSI5 supportive)
          Short: RSI14 > 70 and RSI2 crossing down through 90 (with RSI5 supportive)
      - Volume surge (current volume > MA(volume, N) * 1.2) if volume_ma_window > 0
      - Optional EMA cross/VWAP deviation can be enforced if desired
    """

    def __init__(self, session):
        self.session = session

    def _load_frame(self, symbol: str, timeframe: str, limit: int = 2000) -> pd.DataFrame:
        q = (self.session.query(Candle)
             .filter(Candle.symbol == symbol, Candle.timeframe == timeframe)
             .order_by(asc(Candle.timestamp))
             .limit(limit))
        rows = q.all()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([{
            'id': r.id, 'ts': r.timestamp, 'open': r.open, 'high': r.high, 'low': r.low, 'close': r.close,
            'volume': r.volume, 'atr': r.atr, 'rsi14': r.rsi14, 'rsi5': r.rsi5, 'rsi2': r.rsi2,
            'ema_fast': r.ema_fast, 'ema_slow': r.ema_slow, 'vwap': r.vwap
        } for r in rows])
        return df

    def _volume_surge(self, vol_series: pd.Series, window: int, idx: int) -> bool:
        if window <= 0 or idx < window:
            return False
        ma = vol_series.iloc[idx-window:idx].mean()
        return vol_series.iloc[idx] > ma * 1.2

    def _vwap_dev_atrs(self, close: float, vwap: float, atr_val: float) -> float:
        if atr_val is None or atr_val == 0 or vwap is None:
            return 0.0
        return abs(close - vwap) / atr_val

    def _triple_rsi_long(self, rsi14: float, rsi5_prev: float, rsi5_now: float, rsi2_prev: float, rsi2_now: float) -> bool:
        gates = Config.TRIPLE_RSI_BUY
        return (
            rsi14 is not None and rsi2_prev is not None and rsi2_now is not None and
            rsi14 < gates['rsi14_lt'] and
            (rsi2_prev <= gates['rsi2_cross_up'] < rsi2_now) and
            (rsi5_now >= rsi5_prev)  # rising RSI5 confirmation
        )

    def _triple_rsi_short(self, rsi14: float, rsi5_prev: float, rsi5_now: float, rsi2_prev: float, rsi2_now: float) -> bool:
        gates = Config.TRIPLE_RSI_SELL
        return (
            rsi14 is not None and rsi2_prev is not None and rsi2_now is not None and
            rsi14 > gates['rsi14_gt'] and
            (rsi2_prev >= gates['rsi2_cross_down'] > rsi2_now) and
            (rsi5_now <= rsi5_prev)  # falling RSI5 confirmation
        )

    def scan(self, symbol: str, timeframe: str, lookback_limit: int = 3000) -> int:
        df = self._load_frame(symbol, timeframe, lookback_limit)
        if df.empty:
            return 0

        # make calculations needing rolling windows
        vol_window = Config.FILTERS.volume_ma_window
        created = 0

        for i in range(2, len(df)):  # need i-1 for cross calc
            row = df.iloc[i]
            prev = df.iloc[i-1]
            atr_ok = (row['atr'] is not None and
                      row['atr'] >= Config.FILTERS.atr_min and
                      row['atr'] <= Config.FILTERS.atr_max)

            if not atr_ok:
                continue

            # triple rsi gates
            long_ok = self._triple_rsi_long(row['rsi14'], prev['rsi5'], row['rsi5'], prev['rsi2'], row['rsi2'])
            short_ok = self._triple_rsi_short(row['rsi14'], prev['rsi5'], row['rsi5'], prev['rsi2'], row['rsi2'])

            if not (long_ok or short_ok):
                continue

            vol_surge = self._volume_surge(df['volume'], vol_window, i) if vol_window else False
            vwap_dev = self._vwap_dev_atrs(row['close'], row['vwap'], row['atr'])
            if Config.FILTERS.vwap_dev_atr > 0 and vwap_dev < Config.FILTERS.vwap_dev_atr:
                continue

            ema_cross = (row['ema_fast'] is not None and row['ema_slow'] is not None and
                         ((long_ok and row['ema_fast'] >= row['ema_slow']) or
                          (short_ok and row['ema_fast'] <= row['ema_slow'])))

            # create candidate if everything aligns
            cand = Candidate(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=pd.to_datetime(row['ts']),
                candle_id=int(row['id']),
                atr=float(row['atr']) if pd.notna(row['atr']) else None,
                rsi14=float(row['rsi14']) if pd.notna(row['rsi14']) else None,
                rsi5=float(row['rsi5']) if pd.notna(row['rsi5']) else None,
                rsi2=float(row['rsi2']) if pd.notna(row['rsi2']) else None,
                ema_cross=bool(ema_cross),
                volume_surge=bool(vol_surge),
                vwap_dev=float(vwap_dev)
            )
            self.session.add(cand)
            self.session.commit()
            created += 1

        return created
