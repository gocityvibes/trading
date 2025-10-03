import time
from typing import Optional, Tuple
from config import Config
from database import Candidate
from utils import extract_json

# lazy providers to avoid import errors if one lib isn't installed
def _call_openai(prompt: str, model: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=Config.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": "You are a precise trading scorer. Reply ONLY with compact JSON."},
            {"role": "user", "content": prompt}
        ]
    )
    return resp.choices[0].message.content

def _call_anthropic(prompt: str, model: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=model, max_tokens=300, temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    # anthropic returns parts; join text
    return "".join(part.text for part in msg.content)

class GPTDecision:
    """
    Stage 3: Score Candidates with GPT (provider & model toggle).
    Use CLI: main.py gpt-score --model gpt-3.5  (or gpt-4.0)
    """

    def __init__(self, session):
        self.session = session

    def _prompt_for(self, cand: Candidate) -> str:
        context = {
            "symbol": cand.symbol,
            "timeframe": cand.timeframe,
            "atr": cand.atr,
            "rsi14": cand.rsi14,
            "rsi5": cand.rsi5,
            "rsi2": cand.rsi2,
            "ema_cross": cand.ema_cross,
            "volume_surge": cand.volume_surge,
            "vwap_dev": cand.vwap_dev,
        }
        return (
            "Score this trade setup 1-10 and pick direction long/short/none.\n"
            "Consider RSI(14/5/2), ATR regime, EMA alignment, volume surge, and VWAP deviation.\n"
            "Respond with strict JSON only, keys: score (number), direction ('long'|'short'|'none'), reason (short string).\n"
            f"Context: {context}"
        )

    def _call_gpt(self, prompt: str, provider: str, model_key: str) -> str:
        model = Config.resolve_model(provider, model_key)
        if provider == 'openai':
            return _call_openai(prompt, model)
        elif provider == 'anthropic':
            return _call_anthropic(prompt, model)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def score_candidate(self, cand: Candidate, provider: Optional[str] = None, model_key: Optional[str] = None) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        provider = provider or Config.GPT_PROVIDER
        model_key = model_key or Config.GPT_MODEL_KEY

        prompt = self._prompt_for(cand)
        last_err = None
        for _ in range(Config.GPT_MAX_RETRIES):
            try:
                raw = self._call_gpt(prompt, provider, model_key)
                data = extract_json(raw)
                if not data or 'score' not in data or 'direction' not in data:
                    last_err = f"Bad JSON: {raw[:120]}"
                    time.sleep(0.4)
                    continue
                score = float(data['score'])
                direction = str(data['direction']).lower()
                reason = str(data.get('reason', '')).strip()[:1000]
                cand.gpt_score = score
                cand.direction = direction
                cand.gpt_reasoning = reason
                self.session.commit()
                return score, direction, reason
            except Exception as e:
                last_err = str(e)
                time.sleep(0.4)
        print("GPT scoring failed:", last_err)
        return None, None, None

    def score_all_unscored(self, provider: Optional[str] = None, model_key: Optional[str] = None) -> int:
        q = self.session.query(Candidate).filter(Candidate.gpt_score.is_(None))
        count = 0
        for cand in q.all():
            s, d, _ = self.score_candidate(cand, provider, model_key)
            if s is not None:
                count += 1
        return count
