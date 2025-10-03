import json
import re
import pandas as pd
from typing import Optional

def rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss.replace(0, pd.NA))
    out = 100 - (100 / (1 + rs))
    return out.fillna(method='bfill').fillna(50.0)

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def vwap_daily(df: pd.DataFrame) -> pd.Series:
    # expects columns: Close, Volume, and DatetimeIndex
    day = df.index.normalize()
    tp = df['Close']  # could use typical price; Close is fine here
    pv = tp * df['Volume']
    vwap = pv.groupby(day).cumsum() / df['Volume'].groupby(day).cumsum()
    return vwap

def extract_json(text: str) -> Optional[dict]:
    # find the first {...} json block
    match = re.search(r'\{.*\}', text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        # try to fix common quotes
        try:
            repaired = re.sub(r"(['\"])score\1\s*:", '"score":', match.group(0))
            return json.loads(repaired)
        except Exception:
            return None

def ticks_to_price(entry: float, ticks: int, tick_size: float, direction: str) -> float:
    if direction == 'long':
        return entry + ticks * tick_size
    else:
        return entry - ticks * tick_size
