from typing import Optional
from sqlalchemy import asc
from database import Trade, Label, Candidate, Candle
from config import Config

class Labeler:
    """
    Stage 5: Convert executed trades into labels for GPT training.
    Rules (simple & effective):
      - If exit_reason == 'target' -> label = 'gold'
      - If exit_reason == 'stop'   -> label = 'hard_negative'
      - If 'eod': label by outcome (pnl_ticks >= 0 => 'gold' else 'hard_negative')
    Also records:
      - mfe_ratio / mae_ratio measured vs ATR at entry candle (if available)
      - bars_to_target / bars_to_stop when applicable (else None)
    """

    def __init__(self, session):
        self.session = session

    def _atr_at_entry(self, trade: Trade) -> Optional[float]:
        # try to grab ATR snapshot from the entry candle (via candidate.candle_id)
        cand = self.session.query(Candidate).filter(Candidate.id == trade.candidate_id).first()
        if not cand:
            return None
        candle = self.session.query(Candle).filter(Candle.id == cand.candle_id).first()
        if not candle or candle.atr is None:
            return None
        return float(candle.atr)

    def _bars_to_exit_type(self, trade: Trade, target: bool) -> Optional[int]:
        # requires candidate timestamp + bar positions; we stored bars_held already.
        if target and trade.exit_reason == 'target':
            return trade.bars_held
        if (not target) and trade.exit_reason == 'stop':
            return trade.bars_held
        return None

    def label_unlabeled(self) -> int:
        existing = {lbl.trade_id for lbl in self.session.query(Label.trade_id)}
        q = (self.session.query(Trade)
             .filter(~Trade.id.in_(existing))
             .order_by(asc(Trade.entry_time)))
        made = 0

        for tr in q.all():
            # decide label type
            if tr.exit_reason == 'target':
                label_type = 'gold'
                win = True
            elif tr.exit_reason == 'stop':
                label_type = 'hard_negative'
                win = False
            else:  # 'eod' or manual
                win = tr.pnl_ticks >= 0
                label_type = 'gold' if win else 'hard_negative'

            atr_val = self._atr_at_entry(tr)
            mfe_ratio = (tr.mfe / atr_val) if (atr_val and atr_val != 0) else None
            mae_ratio = (tr.mae / atr_val) if (atr_val and atr_val != 0) else None

            bars_to_target = self._bars_to_exit_type(tr, target=True)
            bars_to_stop = self._bars_to_exit_type(tr, target=False)

            # snapshot some setup context for future GPT training
            cand = self.session.query(Candidate).filter(Candidate.id == tr.candidate_id).first()
            setup_ctx = None
            if cand:
                setup_ctx = dict(
                    symbol=cand.symbol, timeframe=cand.timeframe,
                    atr=cand.atr, rsi14=cand.rsi14, rsi5=cand.rsi5, rsi2=cand.rsi2,
                    ema_cross=bool(cand.ema_cross), volume_surge=bool(cand.volume_surge),
                    vwap_dev=cand.vwap_dev, gpt_score=cand.gpt_score, direction=cand.direction
                )

            lbl = Label(
                trade_id=tr.id,
                label_type=label_type,
                win=bool(win),
                pnl=float(tr.pnl),
                mfe_ratio=float(mfe_ratio) if mfe_ratio is not None else None,
                mae_ratio=float(mae_ratio) if mae_ratio is not None else None,
                bars_to_target=int(bars_to_target) if bars_to_target is not None else None,
                bars_to_stop=int(bars_to_stop) if bars_to_stop is not None else None,
                setup_context=setup_ctx
            )
            self.session.add(lbl)
            self.session.commit()
            made += 1

        return made
