import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class FilterConfig:
    """Filter thresholds and windows used by Stage 2."""
    atr_min: float = 1.0
    atr_max: float = 15.0
    rsi14_buy: float = 30.0
    rsi14_sell: float = 70.0
    rsi5_cross_buffer: float = 0.0
    rsi2_buy_cross: float = 10.0
    rsi2_sell_cross: float = 90.0
    volume_ma_window: int = 20
    ema_fast: int = 9
    ema_slow: int = 21
    vwap_dev_atr: float = 0.0  # optional VWAP deviation in ATRs (0=off)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterConfig':
        return cls(**data)

class Config:
    # --- database ---
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///trading.db')

    # --- symbols & timeframes ---
    SYMBOLS = ['ES', 'NQ', 'YM']
    TIMEFRAMES = ['1m', '5m', '15m']
    TICK_SIZE = {'ES': 0.25, 'NQ': 0.25, 'YM': 1.0}

    # --- risk ---
    MAX_POSITION_SIZE = 2
    MAX_DAILY_LOSS = 1000
    STOP_LOSS_TICKS = 8
    TAKE_PROFIT_TICKS = 16

    # --- GPT selection ---
    # you can flip models at runtime via CLI: main.py set-model ...
    GPT_PROVIDER = os.getenv('GPT_PROVIDER', 'openai')  # 'openai' or 'anthropic'
    GPT_MODEL_KEY = os.getenv('GPT_MODEL_KEY', 'gpt-3.5')  # 'gpt-3.5' or 'gpt-4.0'

    # map “3.5 / 4.0” to real provider model names
    MODEL_MAP = {
        'openai': {
            'gpt-3.5': 'gpt-3.5-turbo-0125',
            'gpt-4.0': 'gpt-4o-mini-2024-07-18'  # cheap fast 4.x; change to 'gpt-4o' if you prefer
        },
        'anthropic': {
            'gpt-3.5': 'claude-3-haiku-20240307',
            'gpt-4.0': 'claude-3-5-sonnet-20240620'
        }
    }

    @classmethod
    def resolve_model(cls, provider: str = None, key: str = None) -> str:
        provider = provider or cls.GPT_PROVIDER
        key = key or cls.GPT_MODEL_KEY
        try:
            return cls.MODEL_MAP[provider][key]
        except KeyError:
            raise ValueError(f"Unknown provider/key combo: {provider}/{key}")

    # --- runtime feature toggles ---
    PIPELINE_ENABLED = True
    GPT_ENABLED = True  # set False to skip GPT scoring in orchestrator

    # --- GPT thresholds ---
    GPT_SCORE_THRESHOLD = 7.0
    GPT_MAX_RETRIES = 3

    # --- backtest windows ---
    WALK_FORWARD_TRAIN_DAYS = 21
    WALK_FORWARD_TEST_DAYS = 7

    # --- stage 6 optimization ---
    MIN_TRADES_FOR_OPTIMIZATION = 50
    STATISTICAL_CONFIDENCE_THRESHOLD = 0.85

    # active filters (can be replaced from DB)
    FILTERS = FilterConfig()

    # TRIPLE RSI default gates (used by Stage 2 logic)
    TRIPLE_RSI_USE = True
    TRIPLE_RSI_BUY = dict(rsi14_lt=30, rsi2_cross_up=10)      # RSI(14)<30 and RSI(2) cross >10
    TRIPLE_RSI_SELL = dict(rsi14_gt=70, rsi2_cross_down=90)   # RSI(14)>70 and RSI(2) cross <90

    # api keys (read from env)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

    @classmethod
    def load_filters_from_db(cls, session):
        from database import FilterHistory
        latest = session.query(FilterHistory).order_by(FilterHistory.created_at.desc()).first()
        if latest and latest.is_active:
            cls.FILTERS = FilterConfig.from_dict(latest.config)
        return cls.FILTERS

    @classmethod
    def save_filters_to_db(cls, session, filters: FilterConfig, reason: str):
        from database import FilterHistory
        import datetime
        session.query(FilterHistory).update({'is_active': False})
        new_filter = FilterHistory(
            config=filters.to_dict(),
            reason=reason,
            is_active=True,
            created_at=datetime.datetime.now()
        )
        session.add(new_filter)
        session.commit()
        cls.FILTERS = filters
