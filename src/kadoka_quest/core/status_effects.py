# {
#   責務: [status_effects: 状態異常・effectsの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any, Iterable


STATUS_RESISTANCE_CHANCE_MULTIPLIER = {
    "very_weak": 1.5,
    "weak": 1.25,
    "normal": 1.0,
    "resist": 0.75,
    "strong": 0.5,
    "immune": 0.0,
}
VALID_STATUS_RESISTANCE_LEVELS = frozenset(STATUS_RESISTANCE_CHANCE_MULTIPLIER)
FORBIDDEN_STATUS_RESISTANCE_LEVELS = frozenset({"absorb", "reflect"})
KNOWN_STATUS_IDS = frozenset(
    {
        "poison",
        "paralysis",
        "sleep",
        "confusion",
        "bind",
        "curse_bind",
        "curse",
        "bleeding",
    }
)

BLEEDING_ID = "bleeding"
BLEEDING_SPEED_MULTIPLIER = 0.9
BLEEDING_DEFENSE_MULTIPLIER = 0.9
BLEEDING_DAMAGE_RATIO = 0.02


# {
#   責務: [status_effect_id: 状態異常・effectsの状態異常・効果・識別子を求める]
#   処理: [1: 状態異常・effectsの状態異常・効果・識別子を求める]
#   引数: [effect: 効果（dict[str, Any] | str）]
#   戻り値: [result: 状態異常・effectsの状態異常・効果・識別子を求めるための結果（str）]
# }
def status_effect_id(effect: dict[str, Any] | str) -> str:
    if isinstance(effect, dict):
        return str(effect.get("id", ""))
    return str(effect)


# {
#   責務: [has_status: 状態異常を存在を判定する]
#   処理: [1: 状態異常を存在を判定する]
#   引数: [
#     effects: effects（Iterable[dict[str, Any] | str]）
#     status_id: 状態異常・識別子（str）
#   ]
#   戻り値: [result: 状態異常を存在を判定するための結果（bool）]
# }
def has_status(effects: Iterable[dict[str, Any] | str], status_id: str) -> bool:
    return any(status_effect_id(effect) == status_id for effect in effects)


# {
#   責務: [status_apply_chance: Return the final 0..1 chance for a status effect.]
#   処理: [1: Return the final 0..1 chance for a status effect.]
#   引数: [
#     base_chance: base・chance（float）
#     resistance_level: resistance・レベル（str）
#   ]
#   戻り値: [result: Return the final 0..1 chance for a status effect.ための結果（float）]
# }
def status_apply_chance(base_chance: float, resistance_level: str) -> float:
    """Return the final 0..1 chance for a status effect.

    Invalid special damage-only levels fail closed instead of accidentally
    making a malformed status resistance easier to apply at runtime. The
    project validator reports these values as data errors.
    """

    level = str(resistance_level or "normal")
    if level in FORBIDDEN_STATUS_RESISTANCE_LEVELS:
        return 0.0
    multiplier = STATUS_RESISTANCE_CHANCE_MULTIPLIER.get(level, 1.0)
    return min(1.0, max(0.0, float(base_chance)) * multiplier)


# {
#   責務: [status_stat_multiplier: 状態異常・effectsの状態異常・stat・multiplierを求める]
#   処理: [1: 状態異常・effectsの状態異常・stat・multiplierを求める]
#   引数: [
#     effects: effects（Iterable[dict[str, Any] | str]）
#     stat: stat（str）
#   ]
#   戻り値: [result: 状態異常・effectsの状態異常・stat・multiplierを求めるための結果（float）]
# }
def status_stat_multiplier(effects: Iterable[dict[str, Any] | str], stat: str) -> float:
    if not has_status(effects, BLEEDING_ID):
        return 1.0
    if stat == "speed":
        return BLEEDING_SPEED_MULTIPLIER
    if stat == "defense":
        return BLEEDING_DEFENSE_MULTIPLIER
    return 1.0


# {
#   責務: [end_turn_status_damage: 状態異常・effectsのend・ターン・状態異常・ダメージを求める]
#   処理: [1: 状態異常・effectsのend・ターン・状態異常・ダメージを求める]
#   引数: [
#     effect: 効果（dict[str, Any] | str）
#     max_hp: max・HP（int）
#   ]
#   戻り値: [result: 状態異常・effectsのend・ターン・状態異常・ダメージを求めるための結果（int）]
# }
def end_turn_status_damage(effect: dict[str, Any] | str, max_hp: int) -> int:
    if status_effect_id(effect) != BLEEDING_ID:
        return 0
    return max(1, int(max(1, int(max_hp)) * BLEEDING_DAMAGE_RATIO))
