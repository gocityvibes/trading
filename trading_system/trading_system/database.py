import datetime
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, DateTime, Boolean, JSON, Text, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Candle(Base):
    __tablename__ = 'candles_raw'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    timeframe = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

    # indicators
    atr = Column(Float)
    rsi14 = Column(Float)
    rsi5 = Column(Float)
    rsi2 = Column(Float)
    ema_fast = Column(Float)
    ema_slow = Column(Float)
    vwap = Column(Float)

    __table_args__ = (
        Index('uix_candle_unique', 'symbol', 'timeframe', 'timestamp', unique=True),
    )

class Candidate(Base):
    __tablename__ = 'candidates'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    timeframe = Column(String)
    timestamp = Column(DateTime, index=True)
    candle_id = Column(Integer, index=True)

    # snapshot indicators
    atr = Column(Float)
    rsi14 = Column(Float)
    rsi5 = Column(Float)
    rsi2 = Column(Float)
    ema_cross = Column(Boolean)
    volume_surge = Column(Boolean)
    vwap_dev = Column(Float)

    # GPT decision
    gpt_score = Column(Float)
    gpt_reasoning = Column(Text)
    direction = Column(String)  # 'long', 'short', or None

    created_at = Column(DateTime, default=datetime.datetime.now)

class Trade(Base):
    __tablename__ = 'trades'
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, index=True)
    symbol = Column(String, index=True)
    direction = Column(String)
    entry_time = Column(DateTime)
    entry_price = Column(Float)
    position_size = Column(Integer)
    exit_time = Column(DateTime)
    exit_price = Column(Float)
    exit_reason = Column(String)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    pnl = Column(Float)
    pnl_ticks = Column(Integer)
    mfe = Column(Float)
    mae = Column(Float)
    bars_held = Column(Integer)
    filter_config = Column(JSON)
    gpt_score = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.now)

class Label(Base):
    __tablename__ = 'labels'
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, index=True)
    label_type = Column(String)  # 'gold' or 'hard_negative'
    win = Column(Boolean)
    pnl = Column(Float)
    mfe_ratio = Column(Float)
    mae_ratio = Column(Float)
    bars_to_target = Column(Integer)
    bars_to_stop = Column(Integer)
    setup_context = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.now)

class FilterHistory(Base):
    __tablename__ = 'filter_history'
    id = Column(Integer, primary_key=True)
    config = Column(JSON)
    reason = Column(Text)
    is_active = Column(Boolean, default=True)
    trades_count = Column(Integer, default=0)
    win_rate = Column(Float)
    total_pnl = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.now)
    deactivated_at = Column(DateTime)

class OptimizationReport(Base):
    __tablename__ = 'optimization_reports'
    id = Column(Integer, primary_key=True)
    train_start = Column(DateTime)
    train_end = Column(DateTime)
    test_start = Column(DateTime)
    test_end = Column(DateTime)
    old_config = Column(JSON)
    new_config = Column(JSON)
    reasoning = Column(Text)
    old_results = Column(JSON)
    new_results = Column(JSON)
    statistical_significance = Column(Float)
    approved = Column(Boolean)
    approved_by = Column(String)
    rejection_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.now)

def init_database(database_url: str):
    engine = create_engine(database_url, echo=False, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
