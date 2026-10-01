"""Read-only summaries of learned preferences, not action probabilities."""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any


MIN_OBSERVATIONS = 5
_ATTACK_KINDS = frozenset({"physical", "magic", "drain_mp", "random"})
_BATTLE_KINDS = _ATTACK_KINDS | {"heal", "defend", "evade", "buff"}
_SPECS = (
    ("aggression", None, _ATTACK_KINDS),
    ("healing", None, frozenset({"heal"})),
    ("mp_economy", "mp:low", None),
    ("critical_defense", "self:critical", frozenset({"defend", "evade"})),
    ("stronger_aggression", "threat:stronger", _ATTACK_KINDS),
)
_STAGES = ("very_low", "low", "neutral", "high", "very_high")


def _mapping(value: Any) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        result = float(value)
    except OverflowError:
        return None
    return result if isfinite(result) else None


def _observations(value: Any) -> int:
    number = _number(value)
    return int(number) if number is not None and number >= 0 and number.is_integer() else 0


def _skill_groups(skills: Mapping, kinds: frozenset | None) -> tuple[set[str], set[str]]:
    positive, negative = set(), set()
    for skill_id, definition in skills.items():
        skill = _mapping(definition)
        kind = skill.get("kind")
        if not isinstance(skill_id, str) or not isinstance(kind, str):
            continue
        if kind not in _BATTLE_KINDS or skill.get("field_only"):
            continue
        if kinds is None:
            cost = _number(skill.get("mp_cost", 0))
            if cost is None or cost < 0:
                continue
            matches = cost == 0
        else:
            matches = kind in kinds
        (positive if matches else negative).add(skill_id)
    return positive, negative


def _scores(preferences: Mapping, skills: set[str], bound: float) -> list[float]:
    values = []
    for skill_id in sorted(skills):
        value = _number(preferences.get(skill_id))
        if value is not None:
            values.append(max(-bound, min(bound, value)))
    return values


def _summarize_one(ai: Mapping, skills: Mapping, spec: tuple) -> dict[str, Any]:
    tendency_id, tag, kinds = spec
    if tag is None:
        preferences = _mapping(ai.get("action_preferences"))
        observations = _observations(ai.get("actions"))
        bound = 1.0
    else:
        preferences = _mapping(_mapping(ai.get("context_preferences")).get(tag))
        observations = _observations(_mapping(ai.get("context_actions")).get(tag))
        bound = 0.6
    row = {
        "id": tendency_id, "context": tag, "state": "insufficient",
        "observations": observations, "value": None, "stage": None,
        "reason": "few_observations",
    }
    if not preferences and observations == 0:
        row.update(state="unlearned", reason="no_records")
        return row
    if observations < MIN_OBSERVATIONS:
        return row
    positive, negative = _skill_groups(skills, kinds)
    if not positive or not negative:
        row["reason"] = "no_comparison"
        return row
    positive_scores = _scores(preferences, positive, bound)
    negative_scores = _scores(preferences, negative, bound)
    if not positive_scores and not negative_scores:
        row["reason"] = "no_known_preferences"
        return row
    positive_mean = sum(positive_scores) / len(positive_scores) if positive_scores else 0.0
    negative_mean = sum(negative_scores) / len(negative_scores) if negative_scores else 0.0
    value = round(50 + 50 * (positive_mean - negative_mean) / (2 * bound))
    row.update(state="ready", reason=None, value=value, stage=_STAGES[min(4, value // 20)])
    return row


def summarize_tendencies(ai: Mapping, skills: Mapping) -> list[dict[str, Any]]:
    """Return five stable rows from AI and a skill-id -> definition catalog.

    Only recorded, finite learned scores contribute. Unrecorded comparison
    groups have a zero prior. Observation counts are aggregate/context counts,
    not per-skill evidence or statistical confidence. Inputs are never changed.
    """
    return [_summarize_one(_mapping(ai), _mapping(skills), spec) for spec in _SPECS]
