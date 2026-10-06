# {
#   責務: [battle_learning: 戦闘・学習の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any, Iterable


# {
#   責務: [BattleLearning: Updates sparse individual AI preferences from one action reward.]
#   フィールド: []
# }
class BattleLearning:
    """Updates sparse individual AI preferences from one action reward."""

    # {
    #   責務: [learn: 戦闘・学習を学習を反映する]
    #   処理: [1: 戦闘・学習を学習を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     ai: AI（dict[str, Any]）
    #     skill_id: スキル・識別子（str）
    #     reward: 報酬（float）
    #     context_tags: 判断用コンテキスト・tags（Iterable[str]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def learn(
        self,
        ai: dict[str, Any],
        skill_id: str,
        reward: float,
        context_tags: Iterable[str] = (),
    ) -> None:
        preferences = ai.setdefault("action_preferences", {})
        current = float(preferences.get(skill_id, 0.0))
        preferences[skill_id] = round(max(-1.0, min(1.0, current + reward * 0.015)), 4)
        context_preferences = ai.setdefault("context_preferences", {})
        context_actions = ai.setdefault("context_actions", {})
        for tag in dict.fromkeys(str(tag) for tag in context_tags):
            tag_preferences = context_preferences.setdefault(tag, {})
            contextual = float(tag_preferences.get(skill_id, 0.0))
            tag_preferences[skill_id] = round(max(-0.6, min(0.6, contextual + reward * 0.01)), 4)
            context_actions[tag] = int(context_actions.get(tag, 0)) + 1
        ai["actions"] = int(ai.get("actions", 0)) + 1
