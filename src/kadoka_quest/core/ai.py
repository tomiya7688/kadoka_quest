from __future__ import annotations

import random
from typing import Any, Iterable

from kadoka_quest.core.battle_inference import BattleInference
from kadoka_quest.core.battle_learning import BattleLearning


TACTICS = ("balanced", "aggressive", "careful", "variety")
_INFERENCE = BattleInference()
_LEARNING = BattleLearning()


def default_ai(profile: str = "normal", tactic: str = "balanced") -> dict[str, Any]:
    profile_bias = {
        "normal": {},
        "support": {"heal": 0.2, "buff": 0.15},
        "trickster": {"drain_mp": 0.2, "evade": 0.15},
        "dice": {"random": 0.25},
        "maru": {"field": 0.4, "random": 0.3},
        "kadoka": {"field": 0.25, "defend": 0.1},
    }.get(profile, {})
    return {
        "schema_version": 1,
        "profile": profile,
        "tactic": tactic if tactic in TACTICS else "balanced",
        "weights": {
            "damage": 0.5,
            "survival": 0.5,
            "support": 0.5,
            "mp_care": 0.5,
        },
        "kind_preferences": profile_bias,
        "action_preferences": {},
        "context_preferences": {},
        "context_actions": {},
        "battles": 0,
        "actions": 0,
    }


def choose_skill(
    ai: dict[str, Any],
    skills: Iterable[dict[str, Any]],
    hp_ratio: float,
    ally_missing_hp_ratio: float,
    mp_ratio: float,
    rng: random.Random,
    context_tags: Iterable[str] = (),
) -> dict[str, Any] | None:
    return _INFERENCE.choose(ai, skills, hp_ratio, ally_missing_hp_ratio, mp_ratio, rng, context_tags)


def learn_from_action(
    ai: dict[str, Any],
    skill_id: str,
    reward: float,
    context_tags: Iterable[str] = (),
) -> None:
    _LEARNING.learn(ai, skill_id, reward, context_tags)


