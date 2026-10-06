# {
#   責務: [battle_rewards: 戦闘・rewardsの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from kadoka_quest.core.combatant import Combatant


NORMAL_VICTORY_BONUS = 8
NORMAL_EXPERIENCE_PER_LEVEL = 3


# {
#   責務: [custom_defeat_experience: Evaluate editable integer coefficients, never executable expressions.]
#   処理: [1: Evaluate editable integer coefficients, never executable expressions.]
#   引数: [
#     level: レベル（int）
#     rule: rule（Any）
#   ]
#   戻り値: [result: Evaluate editable integer coefficients, never executable expressions.ための結果（int | None）]
# }
def custom_defeat_experience(level: int, rule: Any) -> int | None:
    """Evaluate editable integer coefficients, never executable expressions.

    Missing or malformed policies fall back to the ordinary reward rules.
    """
    if not isinstance(rule, dict):
        return None
    values = [rule.get(key) for key in ("base", "per_level", "squared_divisor")]
    if any(type(value) is not int for value in values):
        return None
    base, per_level, divisor = values
    if base < 0 or per_level < 0 or divisor <= 0:
        return None
    return base + level * per_level + level * level // divisor


# {
#   責務: [battle_experience: Total defeated-enemy rewards; the ordinary bonus is applied at most once.]
#   処理: [1: Total defeated-enemy rewards; the ordinary bonus is applied at most once.]
#   引数: [enemies: 敵（Iterable[Combatant]）]
#   戻り値: [result: Total defeated-enemy rewards; the ordinary bonus is applied at most once.ための結果（int）]
# }
def battle_experience(enemies: Iterable[Combatant]) -> int:
    """Total defeated-enemy rewards; the ordinary bonus is applied at most once."""
    total = 0
    has_ordinary_defeat = False
    for enemy in enemies:
        if enemy.fled or enemy.hp > 0:
            continue
        custom = custom_defeat_experience(enemy.record.level, enemy.experience_reward)
        if custom is None:
            total += enemy.record.level * NORMAL_EXPERIENCE_PER_LEVEL
            has_ordinary_defeat = True
        else:
            total += custom
    return total + (NORMAL_VICTORY_BONUS if has_ordinary_defeat else 0)
