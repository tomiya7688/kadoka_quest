from __future__ import annotations

import math
import random


def relative_spawn_weights(options: list[dict]) -> list[float] | None:
    """Scale finite relative weights without truncation or sum overflow."""
    values = [entry.get("weight", 1) for entry in options]
    if not values or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        return None
    try:
        weights = [float(value) for value in values]
    except OverflowError:
        return None
    if any(not math.isfinite(value) or value < 0 for value in weights) or max(weights) <= 0:
        return None
    largest = max(weights)
    return [value / largest for value in weights]


def pop_allowed(rng: random.Random, rate: object) -> bool:
    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        return False
    if not 0 < rate <= 100:
        return False
    return rate == 100 or rng.random() < rate / 100


def draw_wild_spawn(
    rng: random.Random, options: list[dict], weights: list[float] | None, rate: object = 100,
) -> dict | None:
    """One slot attempt: pop decision, species, then inclusive level roll."""
    if not weights or not pop_allowed(rng, rate):
        return None
    entry = rng.choices(options, weights=weights)[0]
    low, high = entry.get("min_level", 1), entry.get("max_level", 1)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (low, high)):
        return None
    if not 1 <= low <= high <= 100:
        return None
    return dict(entry, rolled_level=rng.randint(low, high))
