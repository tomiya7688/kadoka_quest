# {
#   責務: [wild_spawn: wild・出現の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import math
import random


# {
#   責務: [relative_spawn_weights: Scale finite relative weights without truncation or sum overflow.]
#   処理: [1: Scale finite relative weights without truncation or sum overflow.]
#   引数: [options: options（list[dict]）]
#   戻り値: [result: Scale finite relative weights without truncation or sum overflow.ための結果（list[float] | None）]
# }
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


# {
#   責務: [pop_allowed: allowedを取り出す]
#   処理: [1: allowedを取り出す]
#   引数: [
#     rng: 乱数供給元（random.Random）
#     rate: rate（object）
#   ]
#   戻り値: [result: allowedを取り出すための結果（bool）]
# }
def pop_allowed(rng: random.Random, rate: object) -> bool:
    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        return False
    if not 0 < rate <= 100:
        return False
    return rate == 100 or rng.random() < rate / 100


# {
#   責務: [draw_wild_spawn: One slot attempt: pop decision, species, then inclusive level roll.]
#   処理: [1: One slot attempt: pop decision, species, then inclusive level roll.]
#   引数: [
#     rng: 乱数供給元（random.Random）
#     options: options（list[dict]）
#     weights: 重み一覧（list[float] | None）
#     rate: rate（object）
#   ]
#   戻り値: [result: One slot attempt: pop decision, species, then inclusive level roll.ための結果（dict | None）]
# }
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
