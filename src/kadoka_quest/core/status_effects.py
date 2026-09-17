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


def status_effect_id(effect: dict[str, Any] | str) -> str:
    if isinstance(effect, dict):
        return str(effect.get("id", ""))
    return str(effect)


def has_status(effects: Iterable[dict[str, Any] | str], status_id: str) -> bool:
    return any(status_effect_id(effect) == status_id for effect in effects)


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


def status_stat_multiplier(effects: Iterable[dict[str, Any] | str], stat: str) -> float:
    if not has_status(effects, BLEEDING_ID):
        return 1.0
    if stat == "speed":
        return BLEEDING_SPEED_MULTIPLIER
    if stat == "defense":
        return BLEEDING_DEFENSE_MULTIPLIER
    return 1.0


def end_turn_status_damage(effect: dict[str, Any] | str, max_hp: int) -> int:
    if status_effect_id(effect) != BLEEDING_ID:
        return 0
    return max(1, int(max(1, int(max_hp)) * BLEEDING_DAMAGE_RATIO))
