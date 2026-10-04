"""Explicit-random Godot damage numbers compared with real Python BattleEngine; no real saves."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import subprocess
import unittest
from unittest import mock

import test_gdscript_roster as fixture
from kadoka_quest.core.battle import BattleEngine, NORMAL_ATTACK_CRITICAL_CHANCE
from kadoka_quest.core.combatant import Combatant
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.repository import GameRepository, STAT_KEYS

ROOT = fixture.ROOT


def attack(**changes):
    return {"attack": 100, "defense": 10, "target_hp": 1_000_000, "critical_roll": 0.5,
            "variance": 1.0, **changes}


def case(operation, value, **changes):
    return {"operation": operation, "input": value, **changes}


class AttackBoundaryTests(unittest.TestCase):
    def test_pure_numbers_have_no_random_provider_io_rendering_or_ai_dependencies(self):
        source = (ROOT / "gdscript/engine/attack_numbers.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "OS.", "RandomNumberGenerator", "randf(", "randi(",
                          "Label", "Input.", "res://data/", "res://ui/", "res://application/", ".learn("):
            self.assertNotIn(forbidden, source)
        self.assertIn("extends RefCounted", source)
        self.assertIn("critical_roll", source)
        self.assertIn("variance", source)

    def test_numeric_contract_is_not_wired_as_a_completed_battle_scene(self):
        source = (ROOT / "gdscript/application/field_application.gd").read_text(encoding="utf-8")
        self.assertNotIn("attack_numbers", source)
        self.assertNotIn("run_attack_probe", source)


@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real damage-number probes")
class GDScriptAttackTests(unittest.TestCase):
    seed_state = fixture.GDScriptRosterTests.seed_state
    seed_record = fixture.GDScriptRosterTests.seed_record
    write = fixture.GDScriptRosterTests.write
    saved_files = fixture.GDScriptRosterTests.saved_files

    def setUp(self):
        fixture.GDScriptRosterTests.setUp(self)
        self.repository = GameRepository(self.content / "data")
        self.engine = BattleEngine(self.repository, [], [], learning_enabled=False)
        self.engine.learning.learn = mock.Mock()

    def invoke(self, cases=(), joined=()):
        path = self.content / "attack-probe.json"
        path.write_text(json.dumps({"cases": list(cases), "joined": list(joined)}, ensure_ascii=False), encoding="utf-8")
        environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content), KADOKA_SAVE_DIR=str(self.legacy),
                           KADOKA_GDSCRIPT_SAVE_ROOT=str(self.saves), KADOKA_GDSCRIPT_SAVE_NAME="default")
        actual = subprocess.run(
            [str(fixture.GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
             "res://tests/run_attack_probe.gd", "--", str(path)],
            cwd=self.content, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, check=False,
        )
        self.assertEqual(actual.returncode, 0, actual.stderr + actual.stdout[-1600:])
        self.assertNotIn("SCRIPT ERROR", actual.stderr)
        self.assertNotIn("ERROR:", actual.stderr)
        for line in actual.stdout.splitlines():
            if line.startswith("KADOKA_ATTACK_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]).decode("utf-8"))
        self.fail(actual.stderr + actual.stdout[-1600:])

    def reference(self, parameters, *, kind="physical", final_stage=False):
        actor_record = MonsterRecord({"id": "actor", "name": "こうげき側", "species_id": "slime"}, {"kept": [123]})
        target_record = MonsterRecord({"id": "target", "name": "対象", "species_id": "slime"}, {"kept": [456]})
        before = copy.deepcopy([actor_record, target_record])
        actor_stats = {key: 1 for key in STAT_KEYS}
        actor_stats.update(attack=int(parameters.get("attack", parameters.get("damage", 1))),
                           magic=int(parameters.get("damage", 100)), hp=1_000_000)
        target_stats = {key: 1 for key in STAT_KEYS}
        target_stats.update(defense=int(parameters.get("defense", 0)), hp=max(1, int(parameters["target_hp"])))
        actor = Combatant(actor_record, actor_stats, [], {}, equipment=copy.deepcopy(parameters.get("equipment")))
        target = Combatant(target_record, target_stats, [], {})
        target.hp = int(parameters["target_hp"])
        target.guard = float(parameters.get("guard", 1.0))
        actor.attack_multiplier = float(parameters.get("attack_multiplier", 1.0))
        skill = {**self.repository.get_skills()["attack"], "kind": kind,
                 "power": float(parameters.get("power", 1.0)),
                 "critical_multiplier": float(parameters.get("critical_multiplier", 1.0))}
        if final_stage:
            skill.update(power=1.0, critical_multiplier=0.0)
        self.engine.log.clear()
        self.engine.rng = mock.Mock()
        self.engine.rng.random.return_value = float(parameters.get("critical_roll", 0.5))
        self.engine.rng.uniform.return_value = float(parameters["variance"])
        before_hp = target.hp
        self.engine._attack(actor, target, skill, allow_counter=False)
        self.engine.rng.uniform.assert_called_once_with(0.92, 1.08)
        self.assertEqual(self.engine.rng.random.call_count, 1 if kind == "physical" else 0)
        self.engine.learning.learn.assert_not_called()
        self.assertEqual([actor_record, target_record], before)
        return {"dealt": before_hp - target.hp, "remaining_hp": target.hp,
                "critical": any("会心" in line for line in self.engine.log)}

    def assert_reference(self, result, parameters, **options):
        self.assertTrue(result["ok"], result)
        expected = self.reference(parameters, **options)
        self.assertEqual(result["dealt"], expected["dealt"])
        self.assertEqual(result["remaining_hp"], expected["remaining_hp"])
        if "critical" in result:
            self.assertEqual(result["critical"], expected["critical"])
        if expected["remaining_hp"] > 0:
            self.assertEqual(result["damage"], expected["dealt"])
        return expected

    def byte_snapshot(self):
        return {str(path.relative_to(self.content)): hashlib.sha256(path.read_bytes()).hexdigest()
                for directory in ("data", "assets", "python-saves", "gd-saves")
                for path in (self.content / directory).rglob("*") if path.is_file()}

    def test_normal_guard_critical_low_attack_high_defense_and_variance_match_python(self):
        cases = [case("attack", attack(attack=atk, defense=defense, critical_roll=roll, variance=variance, guard=guard))
                 for atk in (0, 1, 7, 99, 400) for defense in (0, 1, 13, 99, 100_000)
                 for roll in (0, 1 / 16 - 1e-10, 1 / 16, 0.999999999)
                 for variance in (0.92, 1.0, 1.08) for guard in (1.0, 0.5)]
        result = self.invoke(cases)
        for item, actual in zip(cases, result["results"]):
            with self.subTest(**item["input"]):
                self.assert_reference(actual, item["input"])
                self.assertEqual(actual["critical_chance"], NORMAL_ATTACK_CRITICAL_CHANCE)
        self.assertEqual(len(result["results"]), 600)
        self.assertTrue(all(result["input_preserved"]))
        self.assertFalse(self.profile.exists())

    def test_uniform_16_bucket_contract_and_exact_critical_threshold(self):
        cases = [case("attack", attack(critical_roll=index / 16)) for index in range(16)]
        for roll in (1 / 16 - 1e-12, 1 / 16, 1 / 16 + 1e-12):
            cases.append(case("attack", attack(critical_roll=roll)))
        result = self.invoke(cases)["results"]
        self.assertEqual(sum(item["critical"] for item in result[:16]), 1)
        self.assertEqual([item["critical"] for item in result[-3:]], [True, False, False])

    def test_critical_ignores_defense_but_not_physical_guard_or_variance(self):
        cases = [case("attack", attack(defense=defense, critical_roll=0, guard=guard, variance=variance))
                 for guard in (1.0, 0.5) for variance in (0.92, 1.0, 1.08) for defense in (0, 100_000)]
        result = self.invoke(cases)["results"]
        for index in range(0, len(result), 2):
            self.assertEqual(result[index]["damage"], result[index + 1]["damage"])
        for item, actual in zip(cases, result):
            with self.subTest(**item["input"]):
                self.assert_reference(actual, item["input"])
        self.assertEqual(result[2]["damage"], 100)
        self.assertEqual(result[8]["damage"], 50)

    def test_defend_definition_default_custom_and_invalid_multiplier(self):
        definition = self.repository.get_skills()["defend"]
        values = ({}, definition, {"damage_multiplier": "0.25"}, {"damage_multiplier": 0}, {"damage_multiplier": -1})
        cases = [case("defend", value) for value in values]
        result = self.invoke(cases)
        self.assertEqual([item["guard"] for item in result["results"]], [0.5, 0.5, 0.25, 0, -1])
        self.assertTrue(all(result["input_preserved"]))
        result = self.invoke([case("defend", value) for value in (
            None, [], {"kind": "magic"}, {"damage_multiplier": True}, {"damage_multiplier": "nan"})])["results"]
        self.assertTrue(all(not item["ok"] for item in result))

    def test_physical_guard_does_not_leak_to_magic_or_drain_finalization(self):
        cases = [case("finish", {"kind": kind, "damage": damage, "guard": guard,
                                 "variance": variance, "target_hp": 1_000_000})
                 for kind in ("physical", "magic", "drain_mp") for damage in (-2, 0, 1, 79)
                 for guard in (1, 0.5, 0) for variance in (0.92, 1.08)]
        result = self.invoke(cases)["results"]
        for item, actual in zip(cases, result):
            with self.subTest(**item["input"]):
                self.assert_reference(actual, item["input"], kind=item["input"]["kind"], final_stage=True)
                self.assertEqual(actual["applied_guard"], item["input"]["guard"]
                                 if item["input"]["kind"] == "physical" else 1)

    def test_truncate_each_stage_instead_of_round_and_guard_before_variance(self):
        parameters = [attack(attack=5, defense=1, variance=1.08, guard=0.5),
                      attack(attack=5, attack_multiplier=0.5, power=1.9, defense=1, variance=1.08),
                      attack(attack=5, attack_multiplier=0.5, power=1.9, critical_roll=0, variance=1.08),
                      attack(attack=-5, attack_multiplier=0.5, defense=0),
                      attack(attack=10, defense=-100), attack(guard=-1)]
        result = self.invoke([case("attack", value) for value in parameters])["results"]
        for parameters, actual in zip(parameters, result):
            self.assert_reference(actual, parameters)
        self.assertEqual(result[0]["raw_damage"], 4)
        self.assertEqual(result[0]["damage"], 2)
        self.assertEqual(result[1]["effective_attack"], 2)
        self.assertEqual(result[1]["raw_damage"], 3)
        self.assertEqual(result[3]["effective_attack"], -2)
        self.assertEqual(result[4]["raw_damage"], 10)

    def test_equipment_normal_attack_power_and_fixed_bonus_order_match_python(self):
        cases = [case("attack", attack(equipment=equipment, guard=0.5, variance=1.08,
                                       critical_roll=roll, attack_multiplier=0.77))
                 for equipment in (None, {}, {"fixed_bonus_damage": 3},
                                   {"skill_modifiers": {"attack": {"power_multiplier": 1.5}}},
                                   {"fixed_bonus_damage": " -5 ",
                                    "skill_modifiers": {"attack": {"power_multiplier": "0.25"}}})
                 for roll in (0, 0.5)]
        result = self.invoke(cases)["results"]
        for item, actual in zip(cases, result):
            with self.subTest(**item["input"]):
                self.assert_reference(actual, item["input"])

    def test_critical_multiplier_matches_python_without_silent_lower_clamp(self):
        cases = [case("attack", attack(critical_multiplier=multiplier, critical_roll=roll))
                 for multiplier in (-2, 0, 0.5, 2, 16, 32) for roll in (0, 1 / 16, 0.999999999)]
        result = self.invoke(cases)["results"]
        for item, actual in zip(cases, result):
            with self.subTest(**item["input"]):
                self.assert_reference(actual, item["input"])
                chance = min(1, NORMAL_ATTACK_CRITICAL_CHANCE * item["input"]["critical_multiplier"])
                self.assertEqual(actual["critical_chance"], chance)

    def test_normal_entry_refuses_unported_skill_ids_and_kinds(self):
        values = [attack(kind="magic"), attack(kind="random"), attack(skill_id="body_bash"),
                  attack(skill_id="weaken"), attack(kind="drain_mp")]
        result = self.invoke([case("attack", value) for value in values])["results"]
        self.assertTrue(all(not item["ok"] and "未移植" in item["message"] for item in result))

    def test_zero_hp_overkill_and_minimum_damage_return_actual_dealt_separately(self):
        cases = [case("attack", attack(target_hp=hp, attack=atk, defense=100_000, critical_roll=roll))
                 for hp in (0, 1, 3, 12) for atk in (0, 100) for roll in (0, 0.5)]
        result = self.invoke(cases)["results"]
        for item, actual in zip(cases, result):
            with self.subTest(**item["input"]):
                self.assert_reference(actual, item["input"])
                self.assertGreaterEqual(actual["damage"], 1)
                self.assertLessEqual(actual["dealt"], item["input"]["target_hp"])

    def test_finite_numeric_strings_match_python_conversion(self):
        parameters = attack(attack="  +101 ", defense="13", attack_multiplier="1.25", power="1.1",
                            critical_multiplier="2", critical_roll="0.125", guard="0.5", variance="1.08",
                            target_hp="1000000", equipment={"fixed_bonus_damage": "3"})
        actual = self.invoke([case("attack", parameters)])["results"][0]
        self.assert_reference(actual, parameters)

    def test_invalid_missing_random_bounds_types_and_precision_return_reasons(self):
        cases = [case("attack", value) for value in (None, [], {})]
        for key in ("attack", "defense", "attack_multiplier", "power", "critical_multiplier", "critical_roll",
                    "guard", "variance", "target_hp"):
            for value in (True, None, [], "not_a_number", "nan", "inf", 10**20):
                cases.append(case("attack", attack(**{key: value})))
        for key, values in (("critical_roll", [-1e-10, 1.0]), ("variance", [0.92 - 1e-10, 1.08 + 1e-10]),
                            ("target_hp", [-1])):
            cases.extend(case("attack", attack(**{key: value})) for value in values)
        for equipment in ([], {"skill_modifiers": []}, {"skill_modifiers": {"attack": []}},
                          {"fixed_bonus_damage": True}, {"skill_modifiers": {"attack": {"power_multiplier": "nan"}}}):
            cases.append(case("attack", attack(equipment=equipment)))
        cases.extend([case("attack", attack(attack=10**12, attack_multiplier=10**12)),
                      case("attack", attack(attack=10**12, power=10**12)),
                      case("attack", attack(attack=10**12, guard=10**12))])
        actual = self.invoke(cases)
        for item, result in zip(cases, actual["results"]):
            with self.subTest(input=item["input"]):
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"], "invalid_attack_numbers")
                self.assertTrue(result["message"])
                self.assertNotIn("damage", result)
        self.assertTrue(all(actual["input_preserved"]))

    def test_actual_nonfinite_inputs_are_rejected(self):
        cases = [case("attack", attack(), special={key: special})
                 for key in ("critical_roll", "variance", "attack", "guard") for special in ("inf", "nan")]
        self.assertTrue(all(not item["ok"] for item in self.invoke(cases)["results"]))

    def test_finalizer_rejects_unsupported_kinds_missing_values_and_unsafe_products(self):
        valid = {"kind": "physical", "damage": 10, "guard": 0.5, "variance": 1, "target_hp": 100}
        values = [None, [], {}, {**valid, "kind": "immune"}, {**valid, "kind": "absorb"},
                  {**valid, "kind": "random"}, {**valid, "damage": True}, {**valid, "guard": None},
                  {**valid, "variance": 0.91}, {**valid, "target_hp": -1},
                  {**valid, "damage": 10**12, "guard": 10**12}]
        result = self.invoke([case("finish", value) for value in values])["results"]
        self.assertTrue(all(not item["ok"] and item["message"] for item in result))

    def test_result_changes_do_not_mutate_inputs_or_affect_repeated_calculations(self):
        parameters = attack(equipment={"fixed_bonus_damage": 3}, future={"keep": [123]})
        result = self.invoke([case("attack", parameters, mutate_result=True), case("attack", parameters)])
        self.assertEqual(result["results"][0], result["results"][1])
        self.assertEqual(result["input_preserved"], [True, True])

    def test_plus_equipment_reconstruction_feeds_normal_numbers_without_repair_or_ai_writes(self):
        actor = self.seed_record("actor", "slime", level=100, plus_choices=["slime_plus_1_hp"], equipment_id="ken")
        target = self.seed_record("target", "hero", level=100, plus_choices=[], equipment_id=None)
        self.seed_state(current_party=["actor", "target"])
        ai = {"battles": 99, "action_preferences": {"attack": 0.8}, "private_ai": {"keep": "値"}}
        self.write("monsters/actor/ai.json", ai)
        joined = [{"actor": {**actor, "equipment_id": equipment}, "target": target,
                   "input": {"critical_roll": roll, "variance": variance, "guard": guard}}
                  for equipment in (None, "ken", "metal_claw", "heavy_weight", "unknown", "wood_staff")
                  for roll in (0, 1 / 16) for variance in (0.92, 1.08) for guard in (1, 0.5)]
        before = self.byte_snapshot()
        result = self.invoke(joined=joined)["joined"]
        for item, actual in zip(joined, result):
            with self.subTest(equipment=item["actor"]["equipment_id"], input=item["input"]):
                actual_actor = self.engine.data_loader.build_combatant(MonsterRecord(copy.deepcopy(item["actor"]), ai))
                actual_target = self.engine.data_loader.build_combatant(MonsterRecord(copy.deepcopy(target), {}))
                self.assertEqual(actual["actor"]["modifiers"]["stats"], actual_actor.stats)
                self.assertEqual(actual["target"]["modifiers"]["stats"], actual_target.stats)
                self.assertEqual(actual["input"]["equipment"], actual_actor.equipment or {})
                self.assert_reference(actual["value"], actual["input"])
        self.assertEqual(self.byte_snapshot(), before)
        self.engine.learning.learn.assert_not_called()
        broken = self.content / "data/species/slime/plus.json"
        broken.write_text("{broken", encoding="utf-8")
        before = self.byte_snapshot()
        self.assertEqual(self.invoke(joined=joined[:1])["joined"][0]["value"],
                         {"ok": False, "error": "reconstruction_failed"})
        self.assertEqual(self.byte_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
