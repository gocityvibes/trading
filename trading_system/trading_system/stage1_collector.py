import time
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

from config import Config
from database import Candle
from utils import rsi, ema, atr, vwap_daily

class CandleCollector:
    """Stage 1: Fetch OHLCV + compute indicators; store Candles."""

    def __init__(self, session, config=Config):
        self.session = session
        self.config = config

    def _convert_symbol(self, symbol: str) -> str:
        mapping = {'ES': 'ES=F', 'NQ': 'NQ=F', 'YM': 'YM=F'}
        return mapping.get(symbol, symbol)

    def fetch_yahoo(self, symbol: str, timeframe: str, days: int = 5) -> pd.DataFrame:
        interval_map = {'1m': '1m', '5m': '5m', '15m': '15m'}
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        tk = yf.Ticker(self._convert_symbol(symbol))
        df = tk.history(start=start_date, end=end_date, interval=interval_map[timeframe])
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.rename(columns=str.title)  # ensure Open/High/Low/Close/Volume
        df.index = pd.to_datetime(df.index)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]

    def compute_indicators(self, df: pd.DataFrame, tf: str) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        df['atr'] = atr(df['High'], df['Low'], df['Close'], 14)
        df['rsi14'] = rsi(df['Close'], 14)
        df['rsi5'] = rsi(df['Close'], 5)
        df['rsi2'] = rsi(df['Close'], 2)
        df['ema_fast'] = ema(df['Close'], Config.FILTERS.ema_fast)
        df['ema_slow'] = ema(df['Close'], Config.FILTERS.ema_slow)
        df['vwap'] = vwap_daily(df)
        return df

    def save(self, symbol: str, timeframe: str, df: pd.DataFrame) -> int:
        count = 0
        for ts, row in df.iterrows():
            exists = self.session.query(Candle).filter_by(
                symbol=symbol, timeframe=timeframe, timestamp=ts
            ).first()
            if exists:
                continue
            c = Candle(
                symbol=symbol, timeframe=timeframe, timestamp=ts,
                open=float(row['Open']), high=float(row['High']),
                low=float(row['Low']), close=float(row['Close']),
                volume=float(row['Volume']),
                atr=float(row['atr']) if pd.notna(row['atr']) else None,
                rsi14=float(row['rsi14']) if pd.notna(row['rsi14']) else None,
                rsi5=float(row['rsi5']) if pd.notna(row['rsi5']) else None,
                rsi2=float(row['rsi2']) if pd.notna(row['rsi2']) else None,
                ema_fast=float(row['ema_fast']) if pd.notna(row['ema_fast']) else None,
                ema_slow=float(row['ema_slow']) if pd.notna(row['ema_slow']) else None,
                vwap=float(row['vwap']) if pd.notna(row['vwap']) else None,
            )
            self.session.add(c)
            count += 1
        self.session.commit()
        return count

    def collect_historical(self, days: int = 5, symbols=None, timeframes=None, sleep_sec=0.8):
        symbols = symbols or Config.SYMBOLS
        timeframes = timeframes or Config.TIMEFRAMES
        total = 0
        for sym in symbols:
            for tf in timeframes:
                df = self.fetch_yahoo(sym, tf, days)
                df = self.compute_indicators(df, tf)
                saved = self.save(sym, tf, df)
                total += saved
                time.sleep(sleep_sec)
        return total
