from __future__ import annotations

import math
import random


FIELD_AI_TYPES = ("random", "chase", "idle")
DEFAULT_FIELD_AI_WEIGHTS = (70, 25, 5)


def _valid_weights(source: object) -> tuple[float, ...] | None:
    if not isinstance(source, dict) or not source or set(source) - set(FIELD_AI_TYPES):
        return None
    values = tuple(source.get(name, 0) for name in FIELD_AI_TYPES)
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        return None
    try:
        weights = tuple(float(value) for value in values)
    except OverflowError:
        return None
    if any(not math.isfinite(value) or value < 0 for value in weights) or max(weights) <= 0:
        return None
    # Relative weights need not total 100. Scaling also prevents sum overflow.
    largest = max(weights)
    return tuple(value / largest for value in weights)


def is_valid_field_ai_weights(source: object) -> bool:
    """Use the runtime's weight-table rules for editor/data validation."""
    return _valid_weights(source) is not None


def choose_field_ai(rng: random.Random, *sources: object) -> str:
    """Draw from the first valid weight table, falling back to game defaults."""
    for source in sources:
        weights = _valid_weights(source)
        if weights is not None:
            return rng.choices(FIELD_AI_TYPES, weights=weights)[0]
    return rng.choices(FIELD_AI_TYPES, weights=DEFAULT_FIELD_AI_WEIGHTS)[0]
