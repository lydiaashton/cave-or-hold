"""Cost estimates from token counts (handoff sections 4 and 9).

Prices live in harness/prices.toml, per million tokens, keyed by the model
string as logged. A model without a price is reported as "price not set",
never as zero.

Inspect reports cache reads and writes separately from input_tokens (they are
not included in it), so each is priced on its own. Without a cache_read price,
cache reads are priced as input (an upper bound: reads are discounted). Cache
writes can cost more than input (Anthropic), so a run with cache writes and no
cache_write price is reported as "price not set" rather than understated.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

from caveharness.config import HARNESS_DIR

PRICES_FILE = HARNESS_DIR / "prices.toml"


def load_prices(path: Path = PRICES_FILE) -> dict[str, dict]:
    if not path.is_file():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8")).get("models", {})


def cost(prices: dict[str, dict], model: str, usage: dict) -> tuple[float, str] | None:
    """(cost, unit) for one usage record, or None when the model has no price."""
    p = prices.get(model)
    if not p or (usage.get("input_tokens_cache_write") and "cache_write" not in p):
        return None
    rate = {"input_tokens": p["input"],
            "input_tokens_cache_read": p.get("cache_read", p["input"]),
            "input_tokens_cache_write": p.get("cache_write", 0.0),
            "output_tokens": p["output"]}
    return sum((usage.get(k) or 0) * r for k, r in rate.items()) / 1e6, p.get("unit", "USD")


def fmt(c: tuple[float, str] | None) -> str:
    return f"{c[0]:,.4f} {c[1]}" if c else "price not set"
