from __future__ import annotations

import random
from typing import Any, Iterable


class BattleInference:
    """Selects one battle action without mutating learned AI data."""

    @staticmethod
    def _tactic_bonus(tactic: str, kind: str) -> float:
        table = {
            "aggressive": {"physical": 0.65, "magic": 0.65, "random": 0.35, "heal": -0.25, "defend": -0.3},
            "careful": {"heal": 0.75, "defend": 0.55, "evade": 0.5, "physical": -0.1},
            "variety": {"drain_mp": 0.45, "buff": 0.45, "random": 0.45, "evade": 0.3},
            "balanced": {},
        }
        return float(table.get(tactic, {}).get(kind, 0.0))

    def choose(
        self,
        ai: dict[str, Any],
        skills: Iterable[dict[str, Any]],
        hp_ratio: float,
        ally_missing_hp_ratio: float,
        mp_ratio: float,
        rng: random.Random,
        context_tags: Iterable[str] = (),
    ) -> dict[str, Any] | None:
        candidates: list[tuple[float, dict[str, Any]]] = []
        tactic = str(ai.get("tactic", "balanced"))
        profile = str(ai.get("profile", "normal"))
        preferences = ai.get("action_preferences", {})
        kind_preferences = ai.get("kind_preferences", {})
        context_preferences = ai.get("context_preferences", {})
        context_tags = tuple(str(tag) for tag in context_tags)

        for skill in skills:
            if skill.get("field_only"):
                continue
            kind = str(skill.get("kind", "physical"))
            score = 1.0 + self._tactic_bonus(tactic, kind)
            score += float(preferences.get(skill.get("id"), 0.0))
            score += float(kind_preferences.get(kind, 0.0))
            context_bonus = sum(
                float(context_preferences.get(tag, {}).get(skill.get("id"), 0.0))
                for tag in context_tags
            )
            score += max(-1.0, min(1.0, context_bonus))
            mp_cost = int(skill.get("mp_cost", 0))
            if mp_cost and mp_ratio < 0.25:
                score -= 0.8 * float(ai.get("weights", {}).get("mp_care", 0.5))
            if kind == "heal":
                score += ally_missing_hp_ratio * 2.4 - 0.65
            elif kind in {"defend", "evade"}:
                score += max(0.0, 0.55 - hp_ratio) * 2.0
            elif kind in {"physical", "magic", "drain_mp", "random"}:
                score += 0.25
            elif kind == "buff":
                score += 0.12
            score += rng.uniform(-0.12, 0.12)
            if profile == "maru":
                score += rng.uniform(-0.9, 0.9)
            elif profile == "kadoka":
                score += rng.uniform(-0.35, 0.35)
            candidates.append((score, skill))

        if not candidates:
            return None
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        if profile == "maru" and len(candidates) > 1 and rng.random() < 0.38:
            return rng.choice(candidates[1:])[1]
        return candidates[0][1]
