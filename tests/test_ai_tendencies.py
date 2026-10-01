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


def rows(ai, skills=SKILLS):
    return {row["id"]: row for row in summarize_tendencies(ai, skills)}


@pytest.mark.parametrize("profile", ["normal", "support", "trickster", "dice", "maru", "kadoka"])
def test_initial_personality_and_tactic_are_not_learning(profile):
    result = rows(default_ai(profile, "aggressive"))
    assert len(result) == 5
    assert all(row["state"] == "unlearned" and row["value"] is None for row in result.values())


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


def test_five_records_is_a_display_threshold_not_confidence():
    ai = default_ai()
    for _ in range(4):
        learn_from_action(ai, "attack", 0)
    assert rows(ai)["aggression"]["state"] == "insufficient"
    learn_from_action(ai, "attack", 0)
    assert rows(ai)["aggression"]["value"] == 50
    assert rows(ai)["aggression"]["stage"] == "neutral"


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


@pytest.mark.parametrize("value", [True, "0.5", None, [], float("nan"), float("inf"), 10**400])
def test_invalid_scores_are_not_learned_signals(value):
    result = rows({"actions": 10, "action_preferences": {"attack": value}})
    assert result["aggression"]["reason"] == "no_known_preferences"


@pytest.mark.parametrize("value", [True, -1, 1.5, "10", None, [], float("inf")])
def test_invalid_counters_do_not_claim_sufficient_data(value):
    result = rows({"actions": value, "action_preferences": {"attack": 1}})
    assert result["aggression"]["state"] == "insufficient"


def test_unknown_field_only_and_uncomparable_skills_are_not_summarized():
    ai = {"actions": 10, "action_preferences": {"unknown": 1, "field": 1}}
    skills = dict(SKILLS, field={"kind": "physical", "field_only": True})
    assert rows(ai, skills)["aggression"]["reason"] == "no_known_preferences"
    ai["action_preferences"]["attack"] = 1
    assert rows(ai, {"attack": SKILLS["attack"]})["aggression"]["reason"] == "no_comparison"


def test_out_of_bounds_scores_are_clamped_to_learning_bounds():
    ai = {"actions": 10, "action_preferences": {"attack": 100, "heal": -100},
          "context_actions": {"self:critical": 10},
          "context_preferences": {"self:critical": {"guard": 100, "attack": -100}}}
    result = rows(ai)
    assert result["aggression"]["value"] == 100
    assert result["critical_defense"]["value"] == 100


@pytest.mark.parametrize("bad", [None, [], "broken"])
def test_malformed_containers_do_not_crash(bad):
    assert len(summarize_tendencies(bad, bad)) == 5
    ai = {"actions": 10, "action_preferences": bad, "context_preferences": bad, "context_actions": bad}
    assert all(row["value"] is None for row in summarize_tendencies(ai, SKILLS))


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
