from datetime import datetime, timedelta

from config import Config
from database import init_database
from stage1_collector import CandleCollector
from stage2_filter import TripleRSIFilter
from stage3_gpt_decision import GPTDecision
from stage4_execution import PaperExecutor
from stage5_labeling import Labeler

class Orchestrator:
    """
    Stage 8: One-shot pipeline runner (no daemon).
    Steps:
      1) Collect (historical N days or skip)
      2) Filter (triple-RSI)
      3) GPT score (with current provider/model)
      4) Execute (paper)
      5) Label
    """

    def __init__(self, session):
        self.session = session

    def run_once(self, days: int = 0, symbols=None, timeframes=None, provider=None, model_key=None):
        symbols = symbols or Config.SYMBOLS
        timeframes = timeframes or Config.TIMEFRAMES
        if provider:
            Config.GPT_PROVIDER = provider
        if model_key:
            Config.GPT_MODEL_KEY = model_key

        if days and days > 0:
            print(f"[Orchestrator] Collecting last {days} days...")
            c = CandleCollector(self.session)
            saved = c.collect_historical(days=days, symbols=symbols, timeframes=timeframes)
            print(f"[Orchestrator] Saved {saved} candles.")

        print("[Orchestrator] Filtering candidates...")
        f = TripleRSIFilter(self.session)
        total = 0
        for s in symbols:
            for tf in timeframes:
                total += f.scan(s, tf, lookback_limit=50000)
        print(f"[Orchestrator] Candidates created: {total}")

        if Config.GPT_ENABLED:
            print(f"[Orchestrator] GPT scoring with {Config.GPT_PROVIDER}/{Config.resolve_model()} ...")
            g = GPTDecision(self.session)
            scored = g.score_all_unscored(provider=Config.GPT_PROVIDER, model_key=Config.GPT_MODEL_KEY)
            print(f"[Orchestrator] Scored: {scored}")
        else:
            print("[Orchestrator] GPT is disabled (Config.GPT_ENABLED=False); skipping scoring stage.")

        print("[Orchestrator] Executing paper trades...")
        ex = PaperExecutor(self.session)
        executed = ex.execute_new_trades(symbols=symbols, timeframes=timeframes)
        print(f"[Orchestrator] Executed trades: {executed}")

        print("[Orchestrator] Labeling trades...")
        lab = Labeler(self.session)
        labeled = lab.label_unlabeled()
        print(f"[Orchestrator] Labels created: {labeled}")

        print("[Orchestrator] Done.")
