# {
#   責務: [ai: AIの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import random
from typing import Any, Iterable

from kadoka_quest.core.battle_inference import BattleInference
from kadoka_quest.core.battle_learning import BattleLearning


TACTICS = ("balanced", "aggressive", "careful", "variety")
_INFERENCE = BattleInference()
_LEARNING = BattleLearning()


# {
#   責務: [default_ai: AIのdefault・AIを求める]
#   処理: [1: AIのdefault・AIを求める]
#   引数: [
#     profile: プロファイル（str）
#     tactic: tactic（str）
#   ]
#   戻り値: [result: AIのdefault・AIを求めるための結果（dict[str, Any]）]
# }
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


# {
#   責務: [choose_skill: スキルを選択する]
#   処理: [1: スキルを選択する]
#   引数: [
#     ai: AI（dict[str, Any]）
#     skills: スキル一覧（Iterable[dict[str, Any]]）
#     hp_ratio: HP・ratio（float）
#     ally_missing_hp_ratio: 味方・missing・HP・ratio（float）
#     mp_ratio: MP・ratio（float）
#     rng: 乱数供給元（random.Random）
#     context_tags: 判断用コンテキスト・tags（Iterable[str]）
#   ]
#   戻り値: [result: スキルを選択するための結果（dict[str, Any] | None）]
# }
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


# {
#   責務: [learn_from_action: from・actionを学習を反映する]
#   処理: [1: from・actionを学習を反映する]
#   引数: [
#     ai: AI（dict[str, Any]）
#     skill_id: スキル・識別子（str）
#     reward: 報酬（float）
#     context_tags: 判断用コンテキスト・tags（Iterable[str]）
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def learn_from_action(
    ai: dict[str, Any],
    skill_id: str,
    reward: float,
    context_tags: Iterable[str] = (),
) -> None:
    _LEARNING.learn(ai, skill_id, reward, context_tags)


