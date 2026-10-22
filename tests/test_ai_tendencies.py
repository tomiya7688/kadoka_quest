# {
#   責務: [test_ai_tendencies: test・AI・tendenciesの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kadoka_quest.apps.ai_inspector import AiInspector
from kadoka_quest.core.ai import default_ai, learn_from_action
from kadoka_quest.core.ai_tendencies import summarize_tendencies
from kadoka_quest.data.monsters import MonsterStore


SKILLS = {
    "attack": {"kind": "physical", "mp_cost": 0},
    "heal": {"kind": "heal", "mp_cost": 6},
    "guard": {"kind": "defend", "mp_cost": 0},
    "zap": {"kind": "magic", "mp_cost": 4},
}
TAGS = ("mp:low", "self:critical", "threat:stronger")


# {
#   責務: [rows: test・AI・tendenciesのrowsを求める]
#   処理: [1: test・AI・tendenciesのrowsを求める]
#   引数: [
#     ai: AI
#     skills: スキル一覧
#   ]
#   戻り値: [result: test・AI・tendenciesのrowsを求めるための結果（型注釈なし）]
# }
def rows(ai, skills=SKILLS):
    return {row["id"]: row for row in summarize_tendencies(ai, skills)}


# {
#   責務: [test_initial_personality_and_tactic_are_not_learning: 検証: initial personality and tactic are not learning]
#   処理: [1: 検証: initial personality and tactic are not learning]
#   引数: [profile: プロファイル]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("profile", ["normal", "support", "trickster", "dice", "maru", "kadoka"])
def test_initial_personality_and_tactic_are_not_learning(profile):
    result = rows(default_ai(profile, "aggressive"))
    assert len(result) == 5
    assert all(row["state"] == "unlearned" and row["value"] is None for row in result.values())


# {
#   責務: [test_real_learning_changes_tendencies_without_changing_learning_algorithm: 検証: real learning changes tendencies without changing learning algorithm]
#   処理: [1: 検証: real learning changes tendencies without changing learning algorithm]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_real_learning_changes_tendencies_without_changing_learning_algorithm():
    attacker, healer = default_ai(), default_ai()
    for _ in range(20):
        learn_from_action(attacker, "attack", 1, TAGS)
        learn_from_action(healer, "heal", 1, TAGS)
    attack_rows, heal_rows = rows(attacker), rows(healer)
    for key in ("aggression", "mp_economy", "stronger_aggression"):
        assert attack_rows[key]["value"] > heal_rows[key]["value"]
    assert attack_rows["healing"]["value"] < heal_rows["healing"]["value"]
    initial = attack_rows["aggression"]["value"]
    for _ in range(40):
        learn_from_action(attacker, "attack", 1, TAGS)
    assert rows(attacker)["aggression"]["value"] > initial
    assert attacker["actions"] == 60


# {
#   責務: [test_contexts_use_their_own_scores_and_observation_counts: 検証: contexts use their own scores and observation counts]
#   処理: [1: 検証: contexts use their own scores and observation counts]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_contexts_use_their_own_scores_and_observation_counts():
    ai = default_ai()
    for _ in range(20):
        learn_from_action(ai, "guard", 1, ("self:critical",))
    result = rows(ai)
    assert result["critical_defense"]["value"] > 50
    assert result["critical_defense"]["observations"] == 20
    assert result["mp_economy"]["state"] == "unlearned"
    ai["context_actions"]["self:critical"] = 4
    assert rows(ai)["critical_defense"]["state"] == "insufficient"
    del ai["context_actions"]
    assert rows(ai)["critical_defense"]["value"] is None


# {
#   責務: [test_five_records_is_a_display_threshold_not_confidence: 検証: five records is a display threshold not confidence]
#   処理: [1: 検証: five records is a display threshold not confidence]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_five_records_is_a_display_threshold_not_confidence():
    ai = default_ai()
    for _ in range(4):
        learn_from_action(ai, "attack", 0)
    assert rows(ai)["aggression"]["state"] == "insufficient"
    learn_from_action(ai, "attack", 0)
    assert rows(ai)["aggression"]["value"] == 50
    assert rows(ai)["aggression"]["stage"] == "neutral"


# {
#   責務: [test_summary_is_read_only_deterministic_and_plain_data: 検証: summary is read only deterministic and plain data]
#   処理: [1: 検証: summary is read only deterministic and plain data]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_summary_is_read_only_deterministic_and_plain_data():
    import json

    ai = default_ai()
    for skill_id in ("attack", "heal", "zap", "guard", "attack"):
        learn_from_action(ai, skill_id, 1, TAGS)
    original_ai, original_skills = deepcopy(ai), deepcopy(SKILLS)
    result = AiInspector.summarize_tendencies(ai, SKILLS)
    assert result == summarize_tendencies(ai, dict(reversed(list(SKILLS.items()))))
    assert json.loads(json.dumps(result, allow_nan=False)) == result
    assert ai == original_ai and SKILLS == original_skills


# {
#   責務: [test_mod_metadata_not_skill_names_drives_classification: 検証: mod metadata not skill names drives classification]
#   処理: [1: 検証: mod metadata not skill names drives classification]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_mod_metadata_not_skill_names_drives_classification():
    skills = {"a": {"kind": "heal", "mp_cost": 2}, "b": {"kind": "physical"}}
    ai = {"actions": 10, "action_preferences": {"a": 1, "b": -1}}
    result = rows(ai, skills)
    assert result["healing"]["value"] == 100
    assert result["aggression"]["value"] == 0
    assert result["healing"]["stage"] == "very_high"
    assert result["aggression"]["stage"] == "very_low"
    skills["unused"] = {"kind": "physical"}
    assert rows(ai, skills) == result


# {
#   責務: [test_invalid_scores_are_not_learned_signals: 検証: invalid scores are not learned signals]
#   処理: [1: 検証: invalid scores are not learned signals]
#   引数: [value: 値]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("value", [True, "0.5", None, [], float("nan"), float("inf"), 10**400])
def test_invalid_scores_are_not_learned_signals(value):
    result = rows({"actions": 10, "action_preferences": {"attack": value}})
    assert result["aggression"]["reason"] == "no_known_preferences"


# {
#   責務: [test_invalid_counters_do_not_claim_sufficient_data: 検証: invalid counters do not claim sufficient data]
#   処理: [1: 検証: invalid counters do not claim sufficient data]
#   引数: [value: 値]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("value", [True, -1, 1.5, "10", None, [], float("inf")])
def test_invalid_counters_do_not_claim_sufficient_data(value):
    result = rows({"actions": value, "action_preferences": {"attack": 1}})
    assert result["aggression"]["state"] == "insufficient"


# {
#   責務: [test_unknown_field_only_and_uncomparable_skills_are_not_summarized: 検証: unknown field only and uncomparable skills are not summarized]
#   処理: [1: 検証: unknown field only and uncomparable skills are not summarized]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_unknown_field_only_and_uncomparable_skills_are_not_summarized():
    ai = {"actions": 10, "action_preferences": {"unknown": 1, "field": 1}}
    skills = dict(SKILLS, field={"kind": "physical", "field_only": True})
    assert rows(ai, skills)["aggression"]["reason"] == "no_known_preferences"
    ai["action_preferences"]["attack"] = 1
    assert rows(ai, {"attack": SKILLS["attack"]})["aggression"]["reason"] == "no_comparison"


# {
#   責務: [test_out_of_bounds_scores_are_clamped_to_learning_bounds: 検証: out of bounds scores are clamped to learning bounds]
#   処理: [1: 検証: out of bounds scores are clamped to learning bounds]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_out_of_bounds_scores_are_clamped_to_learning_bounds():
    ai = {"actions": 10, "action_preferences": {"attack": 100, "heal": -100},
          "context_actions": {"self:critical": 10},
          "context_preferences": {"self:critical": {"guard": 100, "attack": -100}}}
    result = rows(ai)
    assert result["aggression"]["value"] == 100
    assert result["critical_defense"]["value"] == 100


# {
#   責務: [test_malformed_containers_do_not_crash: 検証: malformed containers do not crash]
#   処理: [1: 検証: malformed containers do not crash]
#   引数: [bad: bad]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("bad", [None, [], "broken"])
def test_malformed_containers_do_not_crash(bad):
    assert len(summarize_tendencies(bad, bad)) == 5
    ai = {"actions": 10, "action_preferences": bad, "context_preferences": bad, "context_actions": bad}
    assert all(row["value"] is None for row in summarize_tendencies(ai, SKILLS))


# {
#   責務: [test_saved_individual_reset_returns_to_unlearned: 検証: saved individual reset returns to unlearned]
#   処理: [1: 検証: saved individual reset returns to unlearned]
#   引数: [tmp_path: tmp・パス]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_saved_individual_reset_returns_to_unlearned(tmp_path):
    store = MonsterStore(tmp_path / "monsters")
    attacker = store.create("slime", monster_id="attacker")
    healer = store.create("slime", monster_id="healer")
    for _ in range(20):
        learn_from_action(attacker.ai, "attack", 1, TAGS)
        learn_from_action(healer.ai, "heal", 1, TAGS)
    store.save(attacker)
    store.save(healer)
    assert rows(store.get("attacker").ai)["aggression"]["value"] > rows(store.get("healer").ai)["aggression"]["value"]
    store.reset_ai("attacker")
    assert all(row["state"] == "unlearned" for row in rows(store.get("attacker").ai).values())
    assert rows(store.get("healer").ai)["healing"]["state"] == "ready"
