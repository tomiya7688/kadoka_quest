from __future__ import annotations

from typing import Any

from kadoka_quest.core.ai_tendencies import summarize_tendencies


class AiInspector:
    """Build a compact, plain-data view of one individual's learned AI."""

    @staticmethod
    def summarize_tendencies(ai: dict[str, Any], skills: dict[str, dict]) -> list[dict[str, Any]]:
        return summarize_tendencies(ai, skills)

    @staticmethod
    def summarize(ai: dict[str, Any], limit: int = 3) -> dict[str, Any]:
        count = max(1, int(limit))
        actions = ai.get("action_preferences", {})
        action_rows = [
            {"skill_id": str(skill_id), "score": float(score)}
            for skill_id, score in actions.items()
            if isinstance(score, (int, float)) and float(score) != 0.0
        ]
        contexts = ai.get("context_preferences", {})
        context_rows = []
        for tag, preferences in contexts.items():
            if not isinstance(preferences, dict):
                continue
            for skill_id, score in preferences.items():
                if isinstance(score, (int, float)) and float(score) != 0.0:
                    context_rows.append(
                        {
                            "tag": str(tag),
                            "skill_id": str(skill_id),
                            "score": float(score),
                            "actions": int(ai.get("context_actions", {}).get(tag, 0)),
                        }
                    )
        key = lambda row: (-abs(float(row["score"])), str(row.get("tag", "")), row["skill_id"])
        return {
            "profile": str(ai.get("profile", "normal")),
            "tactic": str(ai.get("tactic", "balanced")),
            "battles": max(0, int(ai.get("battles", 0))),
            "actions": max(0, int(ai.get("actions", 0))),
            "action_preferences": sorted(action_rows, key=key)[:count],
            "context_preferences": sorted(context_rows, key=key)[:count],
        }
