import json
from pathlib import Path

RATE_FILE = Path("data/exchange_rate.json")
CREDITS_PER_DOLLAR = 668.8692534255


def record_observation(cost_usd: float, credits_used: float) -> None:
    RATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = _load()
    data["total_usd"] = data.get("total_usd", 0.0) + cost_usd
    data["total_credits"] = data.get("total_credits", 0.0) + credits_used
    RATE_FILE.write_text(json.dumps(data), encoding="utf-8")


def get_usd_per_credit() -> float:
    data = _load()
    total_credits = data.get("total_credits", 0.0)
    total_usd = data.get("total_usd", 0.0)
    if total_credits > 0:
        return total_usd / total_credits
    return 1 / CREDITS_PER_DOLLAR


def _load() -> dict:
    if not RATE_FILE.exists():
        return {}
    return json.loads(RATE_FILE.read_text(encoding="utf-8"))