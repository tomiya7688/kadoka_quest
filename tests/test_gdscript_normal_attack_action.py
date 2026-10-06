"""Real Godot explicit normal attacks vs real Python _attack/run_round, with private fixtures."""
from __future__ import annotations

import base64
import itertools
import json
import os
import random
import subprocess
import unittest
from unittest import mock

import test_gdscript_attack_numbers as numbers
import test_gdscript_combatant as combatant
import test_gdscript_roster as fixture
import test_gdscript_turn_order as turn
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.battle_data import BattleDataLoader

ROOT = fixture.ROOT
key = turn.key


def member(identifier, speed=10, *, hp=30):
    snapshot = turn.member(identifier, speed, hp=hp)
    snapshot["stats"]["hp"] = hp
    return snapshot


def parameters(*, attack=100, defense=10, hp=1000, equipment=None, **changes):
    ally, enemy = member("ally", speed=20), member("enemy", hp=hp)
    ally["stats"]["attack"], enemy["stats"]["defense"] = attack, defense
    return {**turn.request([ally], [enemy]),
            "equipment": {"allies": {"ally": equipment or {}}}, **changes}


def hit(target=None, **changes):
    return {"kind": "attack", "target": key("enemies", "enemy") if target is None else target, **changes}


def case(input=None, actions=None, **changes):
    return {"input": parameters() if input is None else input,
            "actions": [{"kind": "next"}, hit()] if actions is None else actions, **changes}


class NormalActionBoundaryTests(unittest.TestCase):
    def test_pure_resolution_is_separate_from_routing_and_has_no_io_ai_or_random(self):
        for name in ("normal_attack_action", "normal_attack_contract"):
            source = (ROOT / f"gdscript/engine/{name}.gd").read_text(encoding="utf-8")
            for forbidden in ("FileAccess", "DirAccess", "OS.", "randf(", "randi(", "RandomNumberGenerator",
                              "Input.", "res://data/", "res://ui/", "res://application/", ".learn("):
                self.assertNotIn(forbidden, source)
        source = (ROOT / "gdscript/application/battle_session_application.gd").read_text(encoding="utf-8")
        for forbidden in ("Numbers.", ".take_damage(", "critical_chance", "FileAccess", ".learn("):
            self.assertNotIn(forbidden, source)
        self.assertIn("_attack.resolve(request)", source)
        source = (ROOT / "gdscript/application/field_application.gd").read_text(encoding="utf-8")
        self.assertNotIn("normal_attack_action", source)

    def test_action_benchmark_stays_outside_player_runtime(self):
        source = (ROOT / "tools/performance-check/script/check_gdscript_normal_attack.py").read_text(encoding="utf-8")
        self.assertIn('result["microseconds"] <= 3000', source)
        for directory in (ROOT / "src/kadoka_quest", ROOT / "gdscript/application", ROOT / "gdscript/ui"):
            for path in directory.rglob("*"):
                if path.suffix in (".py", ".gd"):
                    self.assertNotIn("check_gdscript_normal_attack", path.read_text(encoding="utf-8"))


@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real normal-action probes")
class GDScriptNormalActionTests(unittest.TestCase):
    setUp = numbers.GDScriptAttackTests.setUp
    reference = numbers.GDScriptAttackTests.reference
    byte_snapshot = combatant.GDScriptCombatantTests.byte_snapshot
    seed_state = fixture.GDScriptRosterTests.seed_state
    seed_record = fixture.GDScriptRosterTests.seed_record
    write = fixture.GDScriptRosterTests.write

    def invoke(self, cases=(), joined=()):
        path = self.content / "normal-action-probe.json"
        path.write_text(json.dumps({"cases": list(cases), "joined": list(joined)}), encoding="utf-8")
        environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content), KADOKA_SAVE_DIR=str(self.legacy),
                           KADOKA_GDSCRIPT_SAVE_ROOT=str(self.saves), KADOKA_GDSCRIPT_SAVE_NAME="default")
        result = subprocess.run([str(fixture.GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
                                 "res://tests/run_normal_attack_probe.gd", "--", str(path)],
                                cwd=self.content, env=environment, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=60, check=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout[-1600:])
        self.assertNotIn("SCRIPT ERROR", result.stderr)
        self.assertNotIn("ERROR:", result.stderr)
        for line in result.stdout.splitlines():
            if line.startswith("KADOKA_NORMAL_ACTION_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(result.stderr + result.stdout[-1600:])

    def test_normal_critical_equipment_rounding_minimum_and_overkill_match_python_attack(self):
        cases = []
        for atk, defense, roll, variance, hp, gear in itertools.product(
                (0, 7, 100), (0, 13, 100_000), (0, 1 / 16, 0.999), (0.92, 1.0, 1.08), (1, 1000),
                ({}, {"fixed_bonus_damage": 3}, {"skill_modifiers": {"attack": {"power_multiplier": 1.5}}})):
            cases.append(case(parameters(attack=atk, defense=defense, hp=hp, equipment=gear),
                              [{"kind": "next"}, hit(overrides={"critical_roll": roll, "variance": variance})]))
        for item, actual in zip(cases, self.invoke(cases)["cases"]):
            source = item["input"]
            randoms = item["actions"][1]["overrides"]
            with self.subTest(input=source, randoms=randoms):
                action = actual["observations"][1]["value"]
                self.assertTrue(action["executed"], actual)
                result = action["numbers"]
                expected = self.reference({"attack": source["allies"][0]["stats"]["attack"],
                                           "defense": source["enemies"][0]["stats"]["defense"],
                                           "target_hp": source["enemies"][0]["hp"],
                                           "equipment": source["equipment"]["allies"]["ally"], **randoms})
                for field in ("dealt", "remaining_hp", "critical"):
                    self.assertEqual(result[field], expected[field])
                self.assertEqual(actual["session"]["teams"]["enemies"][0]["hp"], expected["remaining_hp"])
                self.assertEqual(actual["session"]["cursor"], 1)
                self.assertIsNone(actual["session"]["pending"])
                self.assertEqual(actual["session"]["teams"]["allies"][0]["mp"], 7)
                self.assertTrue(actual["input_preserved"])

    def test_context_requires_fresh_matching_session_and_cannot_be_replaced(self):
        cases = [case(start_session=False), case(context={"allies": [], "enemies": []}),
                 case(actions=[{"kind": "configure"}, {"kind": "next"}, hit()])]
        uninitialized, mismatch, reused = self.invoke(cases)["cases"]
        self.assertEqual(uninitialized["initialized"]["reason"], "session_not_fresh")
        self.assertEqual(uninitialized["session"]["phase"], "not_started")
        self.assertEqual(mismatch["initialized"]["reason"], "attack_context_mismatch")
        self.assertEqual(mismatch["session"]["cursor"], 0)
        self.assertEqual(mismatch["session"]["teams"]["enemies"][0]["hp"], 1000)
        self.assertEqual(reused["observations"][0]["value"]["reason"], "already_initialized")
        self.assertEqual(reused["observations"][2]["value"]["numbers"]["dealt"], 95)

    def test_repeated_stale_claimed_and_invalid_tickets_cannot_apply_twice(self):
        invalid = [None, {}, {"round": 1, "slot": 0},
                   {"round": 2, "slot": 0, "actor": key("allies", "ally")},
                   {"round": 1, "slot": 0.5, "actor": key("allies", "ally")},
                   {"round": True, "slot": 0, "actor": key("allies", "ally")},
                   {"round": "1", "slot": 0, "actor": key("allies", "ally")},
                   {"round": 1, "slot": 0, "actor": key("enemies", "enemy")},
                   {"round": 1, "slot": 0, "actor": key("allies", "ally"), "extra": 1}]
        cases = [case(actions=[{"kind": "next"}, hit(overrides={"ticket": value}), hit()]) for value in invalid]
        cases += [case(actions=[{"kind": "next"}, hit(), hit()]),
                  case(actions=[{"kind": "next"}, {"kind": "claim"}, hit()]), case(actions=[hit()])]
        actuals = self.invoke(cases)["cases"]
        for actual in actuals[:len(invalid)]:
            with self.subTest(actual=actual):
                self.assertFalse(actual["observations"][1]["value"]["ok"])
                self.assertEqual(actual["observations"][0]["session"], actual["observations"][1]["session"])
                self.assertTrue(actual["observations"][2]["value"]["executed"])
        for actual, index in ((actuals[-3], 2), (actuals[-2], 2), (actuals[-1], 0)):
            self.assertFalse(actual["observations"][index]["value"]["ok"])
        self.assertEqual(actuals[-3]["session"]["cursor"], 1)
        self.assertEqual(actuals[-2]["session"]["cursor"], 0)
        self.assertEqual(actuals[-2]["session"]["teams"]["enemies"][0]["hp"], 1000)

    def test_bad_targets_and_unsupported_inputs_refuse_before_consuming_candidate(self):
        overrides = [{"target": value} for value in (None, {}, key("allies", "ally"), key("enemies", "missing"),
                     {"side": "enemies", "id": "enemy", "extra": True})]
        overrides += [{field: value} for field, value in (("skill_id", "defend"), ("skill_id", "heal"),
                      ("guard", 0.5), ("equipment", {"fixed_bonus_damage": 99}), ("attack", 999),
                      ("status", {}), ("critical_roll", True), ("critical_roll", -0.1), ("critical_roll", 1),
                      ("critical_roll", "nan"), ("variance", None), ("variance", 0.91), ("variance", 1.09))]
        overrides += [{"skill_id": value} for value in (None, True, 1, [])]
        cases = [case(actions=[{"kind": "next"}, hit(overrides=value), hit()]) for value in overrides]
        cases += [case(actions=[{"kind": "next"}, hit(request=value), hit()]) for value in (None, [], {}, "attack")]
        cases += [case(actions=[{"kind": "next"}, hit(special={field: special}), hit()])
                  for field in ("critical_roll", "variance") for special in ("inf", "nan")]
        for actual in self.invoke(cases)["cases"]:
            with self.subTest(actual=actual):
                self.assertFalse(actual["observations"][1]["value"]["ok"])
                self.assertEqual(actual["observations"][0]["session"], actual["observations"][1]["session"])
                self.assertTrue(actual["observations"][2]["value"]["executed"])

    def test_old_ticket_in_next_round_and_bad_random_on_dead_actor_do_not_consume_new_candidate(self):
        old = {"round": 1, "slot": 0, "actor": key("allies", "ally")}
        steps = [{"kind": "next"}, hit(), {"kind": "next"}, hit(key("allies", "ally")),
                 {"kind": "begin"}, {"kind": "next"}, hit(overrides={"ticket": old}), hit()]
        cancelled = [{"kind": "next"}, {"kind": "damage", "actor": key("allies", "ally"), "amount": 30},
                     hit(special={"variance": "nan"}), hit()]
        ordinary, dead = self.invoke([case(actions=steps), case(actions=cancelled)])["cases"]
        self.assertFalse(ordinary["observations"][6]["value"]["ok"])
        self.assertEqual(ordinary["observations"][5]["session"], ordinary["observations"][6]["session"])
        self.assertTrue(ordinary["observations"][7]["value"]["executed"])
        self.assertEqual((ordinary["session"]["round"], ordinary["session"]["cursor"]), (2, 1))
        self.assertEqual(ordinary["session"]["teams"]["enemies"][0]["hp"], 810)
        self.assertFalse(dead["observations"][2]["value"]["ok"])
        self.assertEqual(dead["observations"][1]["session"], dead["observations"][2]["session"])
        self.assertFalse(dead["observations"][3]["value"]["executed"])
        self.assertEqual(dead["session"]["teams"]["enemies"][0]["hp"], 1000)

    def test_dead_and_fled_targets_refuse_but_dead_actor_or_no_foes_cancel_without_damage(self):
        input = parameters()
        input["enemies"].append(member("other"))
        input["shuffle_order"].append(key("enemies", "other"))
        cases = [case(input, [{"kind": "next"}, effect, hit()]) for effect in (
                 {"kind": "damage", "actor": key("enemies", "enemy"), "amount": 1000},
                 {"kind": "flee", "actor": key("enemies", "enemy")})]
        cases += [case(actions=[{"kind": "next"}, effect, hit()]) for effect in (
                  {"kind": "damage", "actor": key("allies", "ally"), "amount": 30},
                  {"kind": "flee", "actor": key("allies", "ally")},
                  {"kind": "damage", "actor": key("enemies", "enemy"), "amount": 1000})]
        results = self.invoke(cases)["cases"]
        for actual in results[:2]:
            self.assertEqual(actual["observations"][2]["value"]["reason"], "target_not_alive")
            self.assertEqual(actual["session"]["cursor"], 0)
        for actual in results[2:]:
            self.assertFalse(actual["observations"][2]["value"]["executed"])
            self.assertEqual(actual["session"]["cursor"], 1)
            self.assertEqual(actual["session"]["phase"], "stopped")
            self.assertIsNone(actual["session"]["pending"])

    def test_damage_overflow_and_unknown_definition_effects_fail_closed(self):
        bad_skills = [{"id": "attack", "kind": kind} for kind in ("magic", "random", None, True, 1)]
        bad_skills += [{"id": "attack", "kind": "physical", field: value} for field, value in (
                       ("status_effect", {}), ("self_damage_ratio", 0.1), ("element", "fire"),
                       ("mp_cost", 1), ("mp_cost", 0.5), ("power", "nan"), ("critical_multiplier", True))]
        cases = [case(parameters(skills={"schema_version": 1, "skills": [skill]})) for skill in bad_skills]
        cases += [case(parameters(equipment=gear)) for gear in (
                  {"counter": True}, {"skill_modifiers": {"attack": {"status": True}}},
                  {"fixed_bonus_damage": "nan"}, {"skill_modifiers": []})]
        for actual in self.invoke(cases)["cases"]:
            self.assertFalse(actual["initialized"]["ok"], actual)
            self.assertEqual(actual["session"]["phase"], "between_rounds")
            self.assertFalse(actual["observations"][1]["value"]["ok"])
        huge = parameters(attack=10_000_000_000,
                          skills={"schema_version": 1, "skills": [{"id": "attack", "kind": "physical", "power": 1e9}]})
        actual = self.invoke([case(huge)])["cases"][0]
        self.assertFalse(actual["observations"][1]["value"]["ok"])
        self.assertEqual(actual["session"], actual["observations"][0]["session"])

    def test_copied_context_input_output_and_same_id_on_both_sides_remain_independent(self):
        input = parameters(equipment={"fixed_bonus_damage": 3})
        for side in ("allies", "enemies"):
            input[side][0]["identity"]["id"] = "shared"
        input["equipment"] = {"allies": {"shared": {"fixed_bonus_damage": 3}}}
        input["shuffle_order"] = [key("allies", "shared"), key("enemies", "shared")]
        steps = [{"kind": "input_mutation"}, {"kind": "next", "mutate_result": True},
                 hit(key("enemies", "shared"), mutate_result=True), {"kind": "next"}, hit(key("allies", "shared"))]
        actual = self.invoke([case(input, steps, mutate_initial=True)])["cases"][0]
        self.assertEqual(actual["observations"][2]["value"]["numbers"]["dealt"], 98)
        self.assertEqual(actual["session"]["teams"]["enemies"][0]["hp"], 902)
        self.assertEqual(actual["session"]["teams"]["allies"][0]["hp"], 25)
        self.assertEqual(actual["session"]["phase"], "round_finished")
        self.assertEqual(actual["session"]["teams"]["allies"][0]["stats"]["attack"], 100)

    def test_eight_actors_ties_death_skips_and_three_rounds_match_real_python_resolution(self):
        cases, expected = [], []
        for seed in range(12):
            generator = random.Random(seed)
            teams = [[member(str(index), speed=generator.choice((0, 1, 5)), hp=200 if seed % 2 else 10)
                      for index in range(4)] for _ in range(2)]
            input = turn.request(*teams)
            engine = turn.GDScriptTurnTests.engine(self, *teams)
            engine.rng = mock.Mock()
            engine.rng.random.return_value, engine.rng.uniform.return_value = 0.5, 1.0
            engine.learning.learn = mock.Mock()
            engine._check_end = mock.Mock()  # Outcomes are expressly not ported here.
            steps, events = [], []
            rounds = [0]

            def shuffled(actors):
                generator.shuffle(actors)
                order = [key("allies" if any(entry is actor for entry in engine.allies) else "enemies",
                             actor.record.monster_id) for actor, _, _ in actors]
                if rounds[0] == 0:
                    input["shuffle_order"] = order
                else:
                    steps.append({"kind": "begin", "order": order})
                rounds[0] += 1

            def perform(actor, foes, friends):
                side = "allies" if any(entry is actor for entry in engine.allies) else "enemies"
                target = foes[0]
                target_key = key("enemies" if side == "allies" else "allies", target.record.monster_id)
                before = target.hp
                engine._attack(actor, target, self.repository.get_skills()["attack"], allow_counter=False)
                steps.extend([{"kind": "next"}, hit(target_key)])
                events.append((key(side, actor.record.monster_id), target.hp, before - target.hp))

            engine.rng.shuffle.side_effect = shuffled
            engine._take_action = mock.Mock(side_effect=perform)
            for _ in range(3):
                engine.run_round()
                steps.append({"kind": "next"})
                if not engine._living(engine.allies) or not engine._living(engine.enemies):
                    break
            engine.learning.learn.assert_not_called()
            cases.append(case(input, steps))
            expected.append((events, [[actor.hp for actor in team] for team in (engine.allies, engine.enemies)]))
        for actual, (events, hp) in zip(self.invoke(cases)["cases"], expected):
            resolved = [entry["value"] for entry in actual["observations"] if entry["value"].get("executed")]
            self.assertEqual([(value["ticket"]["actor"], value["numbers"]["remaining_hp"], value["numbers"]["dealt"])
                              for value in resolved], events)
            self.assertEqual([[actor["hp"] for actor in actual["session"]["teams"][side]]
                              for side in ("allies", "enemies")], hp)
            self.assertTrue(all(entry["value"]["ok"] for entry in actual["observations"]))

    def test_readonly_application_uses_canonical_equipment_and_preserves_all_private_files(self):
        self.seed_state(current_party=["owned", None, None, None], private={"keep": True})
        owned = self.seed_record("owned", level=50, plus_choices=[], equipment_id="ken")
        ai = {"schema_version": 1, "battles": 123, "actions": 456, "action_preferences": {"attack": 0.9}}
        self.write("monsters/owned/ai.json", ai)
        self.write("items/items.json", {"items": {"herb": 99}, "private": True})
        self.write("parties/owned.json", {"members": ["owned"]})
        inputs = [{"allies": [{"monster": owned, "ai": ai}], "enemies": [combatant.record("enemy", level=100)],
                   "shuffle_order": [key("allies", "owned"), key("enemies", "enemy")]}]
        for species in self.repository.list_species_ids():
            for level in (1, 50, 100):
                gear = "metal_claw" if species in ("slime", "ball_slime", "metal_slime", "dice_slime") else "wood_staff"
                inputs.append({"allies": [combatant.record("ally", species, level=level, equipment_id=gear)],
                               "enemies": [combatant.record("enemy", level=100)],
                               "shuffle_order": [key("allies", "ally"), key("enemies", "enemy")]})
        loader = BattleDataLoader(self.repository)
        joined = []
        expected = []
        for input in inputs:
            allies = [loader.build_combatant(MonsterRecord(entry["monster"], entry["ai"])) for entry in input["allies"]]
            enemies = [loader.build_combatant(MonsterRecord(entry["monster"], entry["ai"])) for entry in input["enemies"]]
            side = "allies" if allies[0].speed >= enemies[0].speed else "enemies"
            target_side = "enemies" if side == "allies" else "allies"
            actor, target = (allies[0], enemies[0]) if side == "allies" else (enemies[0], allies[0])
            expected.append(self.reference({"attack": actor.stats["attack"], "defense": target.defense,
                                            "target_hp": target.hp, "equipment": actor.equipment,
                                            "critical_roll": 0, "variance": 1.08}))
            joined.append(case(input, [{"kind": "next"},
                                       hit(key(target_side, target.record.monster_id),
                                           overrides={"critical_roll": 0, "variance": 1.08}, mutate_result=True)],
                               mutate_initial=True))
        before = self.byte_snapshot()
        for actual, expected in zip(self.invoke(joined=joined)["joined"], expected):
            self.assertTrue(actual["initialized"]["ok"], actual)
            result = actual["observations"][1]["value"]["numbers"]
            for field in ("dealt", "remaining_hp", "critical"):
                self.assertEqual(result[field], expected[field])
            self.assertTrue(actual["input_preserved"])
            self.assertNotIn("ai", actual["session"]["teams"]["allies"][0])
        self.assertEqual(self.byte_snapshot(), before)

    def test_modded_skill_power_is_readonly_and_invalid_global_definitions_do_not_start(self):
        path = self.content / "data/skills/skills.json"
        valid = {"schema_version": 1, "skills": [{"id": "attack", "display_name": "こうげき", "kind": "physical", "power": 1.7,
                                                 "critical_multiplier": 2, "mp_cost": 0}]}
        input = {"allies": [combatant.record("ally", level=100)], "enemies": [combatant.record("enemy")],
                 "shuffle_order": [key("allies", "ally"), key("enemies", "enemy")]}
        path.write_text(json.dumps(valid), encoding="utf-8")
        before = self.byte_snapshot()
        actual = self.invoke(joined=[case(input, [{"kind": "next"}, hit(overrides={"critical_roll": 0.1})])])["joined"][0]
        self.assertTrue(actual["observations"][1]["value"]["numbers"]["critical"])
        self.assertEqual(actual["observations"][1]["value"]["numbers"]["effective_power"], 1.7)
        loader = BattleDataLoader(self.repository)
        actor = loader.build_combatant(MonsterRecord(input["allies"][0]["monster"], input["allies"][0]["ai"]))
        target = loader.build_combatant(MonsterRecord(input["enemies"][0]["monster"], input["enemies"][0]["ai"]))
        expected = self.reference({"attack": actor.stats["attack"], "defense": target.defense, "target_hp": target.hp,
                                   "critical_roll": 0.1, "variance": 1.0, "power": 1.7, "critical_multiplier": 2})
        for field in ("dealt", "remaining_hp", "critical"):
            self.assertEqual(actual["observations"][1]["value"]["numbers"][field], expected[field])
        self.assertEqual(self.byte_snapshot(), before)
        for document in ({}, {"schema_version": 99, "skills": []}, {"schema_version": True, "skills": []},
                         {"schema_version": "1", "skills": []}, {"schema_version": [], "skills": []},
                         {"schema_version": 1, "skills": []},
                         {"schema_version": 1, "skills": valid["skills"] * 2},
                         {"schema_version": 1, "skills": [{**valid["skills"][0], "status_effect": {}}]}):
            with self.subTest(document=document):
                path.write_text(json.dumps(document), encoding="utf-8")
                before = self.byte_snapshot()
                actual = self.invoke(joined=[case(input)])["joined"][0]
                self.assertFalse(actual["initialized"]["ok"])
                self.assertEqual(actual["session"]["phase"], "not_started")
                self.assertFalse(actual["observations"][1]["value"]["ok"])
                self.assertEqual(self.byte_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
