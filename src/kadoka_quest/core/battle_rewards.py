# {
#   責務: [battle_rewards: 撃破した敵のレベルと任意の種族設定から、戦闘経験値を計算します]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from kadoka_quest.core.combatant import Combatant


NORMAL_VICTORY_BONUS = 8
NORMAL_EXPERIENCE_PER_LEVEL = 3


# {
#   責務: [custom_defeat_experience: 種族の整数係数による撃破経験値を計算します。式の文字列は実行しません]
#   処理: [1: 種族の整数係数による撃破経験値を計算します。式の文字列は実行しません]
#   引数: [
#     level: 撃破した敵個体のレベル（int）
#     rule: base/per_level/squared_divisorを持つ種族の経験値設定（Any）
#   ]
#   戻り値: [result: 設定が正しければbase+level*per_level+level*level//squared_divisor、不正または欠落ならNone（int | None）]
# }
def custom_defeat_experience(level: int, rule: Any) -> int | None:
    """Evaluate editable integer coefficients, never executable expressions.

    Missing or malformed policies fall back to the ordinary reward rules.
    """
    # 数式文字列は実行せず、検証できる整数係数だけを採用する。
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
#   責務: [battle_experience: 倒した敵の経験値を合計し、通常報酬の勝利加算を最大一回適用します]
#   処理: [1: 倒した敵の経験値を合計し、通常報酬の勝利加算を最大一回適用します]
#   引数: [
#     enemies: 戦闘終了時の敵個体一覧。逃走済みと生存中の敵は除外します（Iterable[Combatant]）
#   ]
#   戻り値: [result: 有効な独自報酬または通常レベル報酬と、一回だけの通常勝利加算の合計（int）]
# }
def battle_experience(enemies: Iterable[Combatant]) -> int:
    """Total defeated-enemy rewards; the ordinary bonus is applied at most once."""
    # 生存者と逃走者を除外し、通常報酬の勝利加算は敵の数にかかわらず一回にする。
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
