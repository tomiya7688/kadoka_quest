# {
#   責務: [battle_decision_explanation: 戦闘・decision・explanationの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any, Iterable


# {
#   責務: [BattleDecisionExplanation: Describe an already selected AI action without changing its choice.]
#   フィールド: []
# }
class BattleDecisionExplanation:
    """Describe an already selected AI action without changing its choice."""

    # {
    #   責務: [describe: 戦闘・decision・explanationを説明用の値を構成する]
    #   処理: [1: 戦闘・decision・explanationを説明用の値を構成する]
    #   引数: [
    #     ai: AI（dict[str, Any]）
    #     skill: スキル（dict[str, Any]）
    #     context_tags: 判断用コンテキスト・tags（Iterable[str]）
    #   ]
    #   戻り値: [result: 戦闘・decision・explanationを説明用の値を構成するための結果（str）]
    # }
    @staticmethod
    def describe(
        ai: dict[str, Any],
        skill: dict[str, Any],
        context_tags: Iterable[str],
    ) -> str:
        skill_id = str(skill.get("id", "?"))
        parts = [f"戦術:{ai.get('tactic', 'balanced')}"]
        action_preferences = ai.get("action_preferences", {})
        learned = float(action_preferences.get(skill_id, 0.0)) if isinstance(action_preferences, dict) else 0.0
        if learned:
            parts.append(f"習熟:{learned:+.2f}")
        context_total = 0.0
        active_tags = []
        preferences = ai.get("context_preferences", {})
        for tag in context_tags:
            entry = preferences.get(tag, {}) if isinstance(preferences, dict) else {}
            score = float(entry.get(skill_id, 0.0)) if isinstance(entry, dict) else 0.0
            if score:
                context_total += score
                active_tags.append(str(tag))
        if context_total:
            parts.append(f"状況:{','.join(active_tags)} {context_total:+.2f}")
        return "AI判断 " + " / ".join(parts)
