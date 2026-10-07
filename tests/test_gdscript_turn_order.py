"""Pure round planning/latest liveness parity; real Godot on private fixtures, no actions/AI ported."""
# {
#   責務: [test_gdscript_turn_order: Pure round planning/latest liveness parity; real Godot on private fixtures, no actions/AI ported.]
#   フィールド: []
# }
from __future__ import annotations

import base64
import copy
import itertools
import json
import os
import random
import subprocess
import unittest
from unittest import mock

import test_gdscript_combatant as combatant
import test_gdscript_roster as fixture
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.combatant import Combatant
from kadoka_quest.core.monster import MonsterRecord, equipment_allows_species
from kadoka_quest.data.battle_data import BattleDataLoader
from kadoka_quest.data.repository import GameRepository

ROOT = fixture.ROOT


# {
#   責務: [member: 指定ID・速度・HP・逃走状態を持つ順序比較用の資源辞書を作ります]
#   処理: [1: 指定ID・速度・HP・逃走状態を持つ順序比較用の資源辞書を作ります]
#   引数: [
#     identifier: 専用比較個体の識別ID
#     speed: 素早さ
#     hp: HP
#     fled: 逃走済み
#   ]
#   戻り値: [result: 個体情報・能力値・現在HP/MP・生存と逃走を持つ資源辞書（dict）]
# }
def member(identifier, speed=10, *, hp=30, fled=False):
    return {"identity": combatant.identity(identifier), "stats": combatant.stats(speed=speed),
            "hp": hp, "mp": 7, "fled": fled, "alive": hp > 0 and not fled}


# {
#   責務: [key: 戦闘参加者を識別するsideとidの辞書を作ります]
#   処理: [1: 戦闘参加者を識別するsideとidの辞書を作ります]
#   引数: [
#     side: 陣営
#     identifier: 専用比較個体の識別ID
#   ]
#   戻り値: [result: sideとidを持つ独立辞書（dict）]
# }
def key(side, identifier):
    return {"side": side, "id": identifier}


# {
#   責務: [participants: HPが正で未逃走の味方・敵を入力順でside/idの列へ投影します]
#   処理: [1: HPが正で未逃走の味方・敵を入力順でside/idの列へ投影します]
#   引数: [
#     allies: 味方
#     enemies: 敵
#   ]
#   戻り値: [result: 生存参加者のside/id列（list）]
# }
def participants(allies, enemies):
    return [key(side, entry["identity"]["id"]) for side, team in (("allies", allies), ("enemies", enemies))
            for entry in team if entry["alive"]]


# {
#   責務: [request: 両陣営の資源と生存参加者の明示順を持つ検証要求を作ります]
#   処理: [1: 両陣営の資源と生存参加者の明示順を持つ検証要求を作ります]
#   引数: [
#     allies: 味方
#     enemies: 敵
#     changes: 比較ケース別の値や設定の上書き
#   ]
#   戻り値: [result: 両陣営・装備・明示順とケース別条件を持つ開始情報（dict）]
# }
def request(allies=None, enemies=None, **changes):
    allies = [member("ally")] if allies is None else allies
    enemies = [member("enemy")] if enemies is None else enemies
    return {"allies": allies, "enemies": enemies, "shuffle_order": participants(allies, enemies), **changes}


# {
#   責務: [case: test・gdscript・ターン・順序のcaseを求める]
#   処理: [1: test・gdscript・ターン・順序のcaseを求める]
#   引数: [
#     operation: operation
#     value: 値
#     changes: changes
#   ]
#   戻り値: [result: test・gdscript・ターン・順序のcaseを求めるための結果（型注釈なし）]
# }
def case(operation, value, **changes):
    return {"operation": operation, "input": value, **changes}


# {
#   責務: [TurnBoundaryTests: ターン・boundary・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class TurnBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_order_keeps_io_ui_rng_ai_and_actions_out_of_pure_engine: 検証: order keeps io ui rng ai and actions out of pure engine]
    #   処理: [1: 検証: order keeps io ui rng ai and actions out of pure engine]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_order_keeps_io_ui_rng_ai_and_actions_out_of_pure_engine(self):
        source = (ROOT / "gdscript/engine/turn_order.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "OS.", "randf(", "randi(", "RandomNumberGenerator",
                          "Input.", "Label", "sort_custom(", "res://data/", "res://ui/", "res://application/",
                          ".learn(", "take_damage(", "pay_mp("):
            self.assertNotIn(forbidden, source)
        source = (ROOT / "gdscript/application/turn_preparation.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "save(", "write_atomic", "Label", ".learn(", "stats\"][\"speed"):
            self.assertNotIn(forbidden, source)
        field = (ROOT / "gdscript/application/field_application.gd").read_text(encoding="utf-8")
        self.assertNotIn("turn_preparation", field)
        self.assertNotIn("turn_order", field)

    # {
    #   責務: [test_performance_guard_is_developer_only_and_covers_plan_and_latest_check: 検証: performance guard is developer only and covers plan and latest check]
    #   処理: [1: 検証: performance guard is developer only and covers plan and latest check]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_performance_guard_is_developer_only_and_covers_plan_and_latest_check(self):
        probe = (ROOT / "gdscript/tests/run_combatant_probe.gd").read_text(encoding="utf-8")
        self.assertIn("Order.plan(", probe)
        self.assertIn("Order.check_actor(", probe)
        tool = (ROOT / "tools/performance-check/script/check_gdscript_combatant.py").read_text(encoding="utf-8")
        self.assertIn('result["round_microseconds"] <= 2000', tool)
        for directory in (ROOT / "src/kadoka_quest", ROOT / "gdscript/application", ROOT / "gdscript/ui"):
            for path in directory.rglob("*"):
                if path.suffix in (".py", ".gd"):
                    self.assertNotIn("check_gdscript_combatant", path.read_text(encoding="utf-8"))


# {
#   責務: [GDScriptTurnTests: gdscript・ターン・testsの状態と振る舞いを担当する]
#   フィールド: [
#     setUp: set・up
#     seed_state: seed・状態
#     seed_record: seed・個体レコード
#     write: write
#     byte_snapshot: byte・独立した状態の写し
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real turn-order probes")
class GDScriptTurnTests(unittest.TestCase):
    setUp = fixture.GDScriptRosterTests.setUp
    seed_state = fixture.GDScriptRosterTests.seed_state
    seed_record = fixture.GDScriptRosterTests.seed_record
    write = fixture.GDScriptRosterTests.write
    byte_snapshot = combatant.GDScriptCombatantTests.byte_snapshot

    # {
    #   責務: [invoke: gdscript・ターン・testsのinvokeを求める]
    #   処理: [1: gdscript・ターン・testsのinvokeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     cases: cases
    #     joined: joined
    #   ]
    #   戻り値: [result: gdscript・ターン・testsのinvokeを求めるための結果（型注釈なし）]
    # }
    def invoke(self, cases=(), joined=()):
        path = self.content / "turn-probe.json"
        path.write_text(json.dumps({"cases": list(cases), "joined": list(joined)}, ensure_ascii=False), encoding="utf-8")
        environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content), KADOKA_SAVE_DIR=str(self.legacy),
                           KADOKA_GDSCRIPT_SAVE_ROOT=str(self.saves), KADOKA_GDSCRIPT_SAVE_NAME="default")
        process = subprocess.run(
            [str(fixture.GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
             "res://tests/run_turn_probe.gd", "--", str(path)],
            cwd=self.content, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout[-1600:])
        self.assertNotIn("SCRIPT ERROR", process.stderr)
        self.assertNotIn("ERROR:", process.stderr)
        for line in process.stdout.splitlines():
            if line.startswith("KADOKA_TURN_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(process.stderr + process.stdout[-1600:])

    # {
    #   責務: [engine: gdscript・ターン・testsのルール処理を求める]
    #   処理: [1: gdscript・ターン・testsのルール処理を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     allies: 味方
    #     enemies: 敵
    #   ]
    #   戻り値: [result: ルール処理（型注釈なし）]
    # }
    def engine(self, allies, enemies):
        engine = BattleEngine(GameRepository(self.content / "data"), [], [], learning_enabled=False)
        teams = []
        for team in (allies, enemies):
            built = []
            for snapshot in team:
                entry = Combatant(MonsterRecord(copy.deepcopy(snapshot["identity"]), {"keep": [12, 34]}),
                                  copy.deepcopy(snapshot["stats"]), [], {})
                entry.hp, entry.mp, entry.fled = snapshot["hp"], snapshot["mp"], snapshot["fled"]
                built.append(entry)
            teams.append(built)
        engine.allies, engine.enemies = teams
        return engine

    # {
    #   責務: [reference: gdscript・ターン・testsのreferenceを求める]
    #   処理: [1: gdscript・ターン・testsのreferenceを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     parameters: parameters
    #   ]
    #   戻り値: [result: gdscript・ターン・testsのreferenceを求めるための結果（型注釈なし）]
    # }
    def reference(self, parameters):
        engine = self.engine(parameters["allies"], parameters["enemies"])
        captured = {}
        executed = []

        # {
        #   責務: [actor_key: gdscript・ターン・testsの行動個体・キーを求める]
        #   処理: [1: gdscript・ターン・testsの行動個体・キーを求める]
        #   引数: [
        #     actor: 行動個体
        #     friends: friends
        #   ]
        #   戻り値: [result: gdscript・ターン・testsの行動個体・キーを求めるための結果（型注釈なし）]
        # }
        def actor_key(actor, friends):
            side = "allies" if any(entry is actor for entry in engine.allies) else "enemies"
            return key(side, actor.record.monster_id)

        # {
        #   責務: [shuffle: gdscript・ターン・testsの並べ替えを求める]
        #   処理: [1: gdscript・ターン・testsの並べ替えを求める]
        #   引数: [actors: actors]
        #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
        # }
        def shuffle(actors):
            captured["initial"] = [actor_key(actor, friends) for actor, _, friends in actors]
            by_key = {(entry["side"], entry["id"]): actor
                      for entry, actor in zip(captured["initial"], actors)}
            actors[:] = [by_key[(entry["side"], entry["id"])] for entry in parameters["shuffle_order"]]
            captured["actors"] = actors  # Real run_round subsequently sorts this exact list.

        engine.rng = mock.Mock()
        engine.rng.shuffle.side_effect = shuffle
        engine._take_action = mock.Mock(side_effect=lambda actor, foes, friends: executed.append(actor_key(actor, friends)))
        engine._check_end = mock.Mock()  # Isolate planning; no outcome/reward/AI/action implementation claimed.
        engine.learning.learn = mock.Mock()
        engine.run_round()
        engine.rng.shuffle.assert_called_once()
        engine.learning.learn.assert_not_called()
        return {"initial": captured["initial"],
                "order": [actor_key(actor, friends) for actor, _, friends in captured["actors"]], "executed": executed}

    # {
    #   責務: [assert_case: gdscript・ターン・testsのassert・caseを求める]
    #   処理: [1: gdscript・ターン・testsのassert・caseを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     actual: actual
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def assert_case(self, actual):
        self.assertTrue(actual["input_preserved"])
        self.assertEqual(actual["again"], actual["value"])

    # {
    #   責務: [test_all_shuffle_permutations_preserve_ties_like_actual_python_run_round: 検証: all shuffle permutations preserve ties like actual python run round]
    #   処理: [1: 検証: all shuffle permutations preserve ties like actual python run round]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_all_shuffle_permutations_preserve_ties_like_actual_python_run_round(self):
        cases = []
        for speeds in ((10, 10, 10, 10), (10, 2, 2, 1), (0, 1, 0, 1), (2**53 - 1, 1, 3, 3)):
            allies = [member("a0", speeds[0]), member("a1", speeds[1])]
            enemies = [member("e0", speeds[2]), member("e1", speeds[3])]
            for permutation in itertools.permutations(participants(allies, enemies)):
                cases.append(case("plan", request(allies, enemies, shuffle_order=list(permutation)), mutate_result=True))
        result = self.invoke(cases)["cases"]
        for parameters, actual in zip(cases, result):
            with self.subTest(parameters=parameters["input"]):
                self.assert_case(actual)
                self.assertTrue(actual["value"]["ok"])
                expected = self.reference(parameters["input"])
                self.assertEqual(actual["value"]["initial"], expected["initial"])
                self.assertEqual(actual["value"]["order"], expected["order"])
                self.assertEqual(expected["order"], expected["executed"])

    # {
    #   責務: [test_eight_actors_mixed_speeds_dead_and_fled_match_python: 検証: eight actors mixed speeds dead and fled match python]
    #   処理: [1: 検証: eight actors mixed speeds dead and fled match python]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_eight_actors_mixed_speeds_dead_and_fled_match_python(self):
        generator = random.Random(228)
        cases = []
        for index in range(100):
            teams = [[member(f"id_{slot}", generator.choice((0, 1, 7, 7, 100)),
                             hp=generator.choice((0, 1, 30)), fled=generator.choice((False, False, True)))
                      for slot in range(4)] for _ in range(2)]
            shuffled = participants(*teams)
            generator.shuffle(shuffled)
            cases.append(case("plan", request(*teams, shuffle_order=shuffled), mutate_result=True))
        result = self.invoke(cases)["cases"]
        for parameters, actual in zip(cases, result):
            with self.subTest(index=parameters["input"]):
                self.assert_case(actual)
                expected = self.reference(parameters["input"])
                self.assertEqual(actual["value"]["order"], expected["order"])
                self.assertEqual(actual["value"]["initial"], expected["initial"])

    # {
    #   責務: [test_participants_keep_ally_then_enemy_slot_order_and_side_namespaces: 検証: participants keep ally then enemy slot order and side namespaces]
    #   処理: [1: 検証: participants keep ally then enemy slot order and side namespaces]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_participants_keep_ally_then_enemy_slot_order_and_side_namespaces(self):
        allies = [member("shared"), member("dead", hp=0), member("fled", fled=True), member("まる")]
        enemies = [member("shared"), member("かどか"), member("other", hp=0)]
        parameters = request(allies, enemies)
        actual = self.invoke([case("participants", parameters, mutate_result=True),
                              case("plan", parameters, mutate_result=True)])["cases"]
        expected = [key("allies", "shared"), key("allies", "まる"), key("enemies", "shared"), key("enemies", "かどか")]
        self.assertEqual(actual[0]["value"]["members"], expected)
        self.assertEqual(actual[1]["value"]["order"], expected)
        for value in actual:
            self.assert_case(value)

    # {
    #   責務: [test_empty_sides_and_all_dead_or_fled_do_not_invent_actors: 検証: empty sides and all dead or fled do not invent actors]
    #   処理: [1: 検証: empty sides and all dead or fled do not invent actors]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_empty_sides_and_all_dead_or_fled_do_not_invent_actors(self):
        pairs = [([], []), ([], [member("e")]), ([member("a")], []),
                 ([member("a", hp=0)], [member("e", fled=True)]),
                 ([member("a", hp=0)], [member("e")])]
        cases = [case("plan", request(*pair)) for pair in pairs]
        actual = self.invoke(cases)["cases"]
        for parameters, value in zip(cases, actual):
            self.assert_case(value)
            expected = self.reference(parameters["input"])
            self.assertEqual(value["value"]["order"], expected["order"])
            self.assertEqual(expected["executed"], [])

    # {
    #   責務: [test_latest_eligibility_matches_python_alive_and_living_for_both_sides: 検証: latest eligibility matches python alive and living for both sides]
    #   処理: [1: 検証: latest eligibility matches python alive and living for both sides]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_latest_eligibility_matches_python_alive_and_living_for_both_sides(self):
        cases = []
        for side in ("allies", "enemies"):
            for hp, fled, foe_hp, foe_fled in itertools.product((0, 1, 30), (False, True), (0, 1, 30), (False, True)):
                actor = member("shared", hp=hp, fled=fled)
                foe = member("shared", hp=foe_hp, fled=foe_fled)
                allies, enemies = ([actor], [foe]) if side == "allies" else ([foe], [actor])
                cases.append(case("check", request(allies, enemies, actor=key(side, "shared")), mutate_result=True))
        actual = self.invoke(cases)["cases"]
        for parameters, result in zip(cases, actual):
            with self.subTest(parameters=parameters["input"]):
                self.assert_case(result)
                value = result["value"]
                engine = self.engine(parameters["input"]["allies"], parameters["input"]["enemies"])
                friends, foes = ((engine.allies, engine.enemies) if parameters["input"]["actor"]["side"] == "allies"
                                 else (engine.enemies, engine.allies))
                self.assertTrue(value["ok"])
                self.assertEqual(value["can_act"], friends[0].alive and bool(engine._living(foes)))
                self.assertEqual(value["stop"], not engine._living(foes))
                self.assertEqual([entry["identity"]["id"] for entry in value["friends"]],
                                 [entry.record.monster_id for entry in engine._living(friends)])
                self.assertEqual([entry["identity"]["id"] for entry in value["foes"]],
                                 [entry.record.monster_id for entry in engine._living(foes)])

    # {
    #   責務: [test_plan_does_not_cache_liveness_for_the_next_action: 検証: plan does not cache liveness for the next action]
    #   処理: [1: 検証: plan does not cache liveness for the next action]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_plan_does_not_cache_liveness_for_the_next_action(self):
        before = request([member("a", 20), member("b", 10)], [member("e", 5)])
        killed = copy.deepcopy(before)
        killed["allies"][1].update(hp=0, alive=False)
        fled = copy.deepcopy(before)
        fled["allies"][1].update(fled=True, alive=False)
        ended = copy.deepcopy(killed)
        ended["enemies"][0].update(hp=0, alive=False)
        cases = [case("plan", before)]
        cases += [case("check", {**state, "actor": key("allies", "b")}) for state in (before, killed, fled, ended)]
        actual = self.invoke(cases)["cases"]
        self.assertEqual(actual[0]["value"]["order"], before["shuffle_order"])
        self.assertEqual([entry["value"]["reason"] for entry in actual[1:]],
                         ["ready", "actor_not_alive", "actor_not_alive", "no_living_foes"])
        self.assertEqual([entry["value"]["stop"] for entry in actual[1:]], [False, False, False, True])
        for entry in actual:
            self.assert_case(entry)

    # {
    #   責務: [test_invalid_shuffle_order_missing_duplicate_unknown_dead_and_side_are_refused: 検証: invalid shuffle order missing duplicate unknown dead and side are refused]
    #   処理: [1: 検証: invalid shuffle order missing duplicate unknown dead and side are refused]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_shuffle_order_missing_duplicate_unknown_dead_and_side_are_refused(self):
        allies, enemies = [member("a"), member("dead", hp=0)], [member("e")]
        keys = participants(allies, enemies)
        invalid = [None, {}, "auto", [], keys[:1], keys + [key("allies", "dead")], [keys[0], keys[0]],
                   [key("allies", "dead"), keys[1]], [key("allies", "missing"), keys[1]],
                   [key("other", "a"), keys[1]], [key("enemies", "a"), keys[1]],
                   [{**keys[0], "extra": 1}, keys[1]], [{"side": True, "id": "a"}, keys[1]],
                   [{"side": "allies", "id": 1}, keys[1]], [None, keys[1]], [[], keys[1]]]
        cases = [case("plan", request(allies, enemies, shuffle_order=order)) for order in invalid]
        actual = self.invoke(cases)["cases"]
        for value in actual:
            self.assert_case(value)
            self.assertFalse(value["value"]["ok"])
            self.assertIn("reason", value["value"])
            self.assertNotIn("order", value["value"])

    # {
    #   責務: [test_invalid_teams_snapshot_fields_and_duplicate_ids_are_refused: 検証: invalid teams snapshot fields and duplicate ids are refused]
    #   処理: [1: 検証: invalid teams snapshot fields and duplicate ids are refused]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_teams_snapshot_fields_and_duplicate_ids_are_refused(self):
        malformed = [None, {}, member("a"), [None], [member("dup"), member("dup")],
                     [member(str(index)) for index in range(5)], [{**member("bad"), "hp": -1}],
                     [{**member("bad"), "hp": 31}], [{**member("bad"), "mp": True}],
                     [{**member("bad"), "alive": False}], [{**member("bad"), "fled": 1}]]
        cases = []
        for team in malformed:
            for side in ("allies", "enemies"):
                for operation in ("plan", "participants", "check"):
                    parameters = {**request(), side: team, "actor": key("allies", "ally")}
                    cases.append(case(operation, parameters))
        for result in self.invoke(cases)["cases"]:
            self.assert_case(result)
            self.assertFalse(result["value"]["ok"])
            self.assertIn("reason", result["value"])

    # {
    #   責務: [test_invalid_numeric_stats_and_nonfinite_snapshot_values_are_refused: 検証: invalid numeric stats and nonfinite snapshot values are refused]
    #   処理: [1: 検証: invalid numeric stats and nonfinite snapshot values are refused]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_numeric_stats_and_nonfinite_snapshot_values_are_refused(self):
        cases = []
        for field in combatant.STAT_KEYS:
            for value in (None, True, "10", -1, 1.5, 2**53):
                parameters = request()
                parameters["allies"][0]["stats"][field] = value
                cases.append(case("plan", parameters))
            for special in ("inf", "nan"):
                cases.append(case("plan", request(), special=[{"path": ["allies", 0, "stats", field], "value": special}]))
        for resource in ("hp", "mp"):
            for special in ("inf", "nan"):
                cases.append(case("check", {**request(), "actor": key("allies", "ally")},
                                  special=[{"path": ["allies", 0, resource], "value": special}]))
        for result in self.invoke(cases)["cases"]:
            self.assert_case(result)
            self.assertFalse(result["value"]["ok"])

    # {
    #   責務: [test_unported_status_speed_buffs_or_unknown_snapshot_fields_are_not_ignored: 検証: unported status speed buffs or unknown snapshot fields are not ignored]
    #   処理: [1: 検証: unported status speed buffs or unknown snapshot fields are not ignored]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_unported_status_speed_buffs_or_unknown_snapshot_fields_are_not_ignored(self):
        cases = []
        for change in ({"status_effects": []}, {"status_effects": [{"id": "slow"}]}, {"speed_multiplier": 1},
                       {"speed_multiplier": 2}, {"timed_buff_turns": {}}, {"mod_runtime": {"speed": 999}}):
            parameters = request()
            parameters["allies"][0].update(change)
            cases.append(case("plan", parameters))
        for location in ("stats", "identity"):
            parameters = request()
            parameters["allies"][0][location]["effective_speed"] = 999
            cases.append(case("check", {**parameters, "actor": key("allies", "ally")}))
        for result in self.invoke(cases)["cases"]:
            self.assert_case(result)
            self.assertEqual(result["value"]["reason"], "unsupported_combatant_fields")

    # {
    #   責務: [test_invalid_or_missing_actor_key_refuses_without_assuming_death: 検証: invalid or missing actor key refuses without assuming death]
    #   処理: [1: 検証: invalid or missing actor key refuses without assuming death]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_or_missing_actor_key_refuses_without_assuming_death(self):
        invalid = [None, {}, [], {"id": "ally"}, key("other", "ally"), key("allies", "../escape"),
                   key("allies", 1), {**key("allies", "ally"), "extra": 1}]
        cases = [case("check", {**request(), "actor": actor}) for actor in invalid]
        cases.append(case("check", {**request(), "actor": key("allies", "missing")}))
        actual = self.invoke(cases)["cases"]
        for value in actual:
            self.assert_case(value)
            self.assertFalse(value["value"]["ok"])
            self.assertNotIn("can_act", value["value"])
        self.assertEqual(actual[-1]["value"]["reason"], "actor_missing")

    # {
    #   責務: [test_readonly_canonical_record_preparation_matches_python_and_keeps_ai: 検証: readonly canonical record preparation matches python and keeps ai]
    #   処理: [1: 検証: readonly canonical record preparation matches python and keeps ai]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_readonly_canonical_record_preparation_matches_python_and_keeps_ai(self):
        repository = GameRepository(self.content / "data")
        loader = BattleDataLoader(repository)
        joined = []
        for species in repository.list_species_ids():
            chain = [stage["options"][0]["id"] for stage in repository.get_species(species).plus["stages"]]
            allowed = [identifier for identifier, item in repository.get_equipment().items()
                       if equipment_allows_species(item, species)]
            for level in (1, 50, 100):
                for equipment in (None, *allowed):
                    allies = [combatant.record("shared", species, level=level, plus_choices=chain, equipment_id=equipment)]
                    enemies = [combatant.record("shared", "slime", level=level)]
                    joined.append({
                        "allies": allies, "enemies": enemies,
                        "shuffle_order": [key("enemies", "shared"), key("allies", "shared")], "mutate_result": True,
                    })
        before = self.byte_snapshot()
        actual = self.invoke(joined=joined)["joined"]
        for parameters, result in zip(joined, actual):
            with self.subTest(monster=parameters["allies"][0]["monster"]):
                self.assert_case(result)
                self.assertTrue(result["value"]["ok"], result)
                snapshots = {}
                for side in ("allies", "enemies"):
                    built = result["value"]["teams"][side]
                    for entry, original in zip(built, parameters[side]):
                        expected = loader.build_combatant(MonsterRecord(original["monster"], original["ai"]))
                        self.assertEqual(entry["snapshot"]["stats"], expected.stats)
                        self.assertEqual(entry["snapshot"]["hp"], expected.hp)
                        self.assertEqual(entry["snapshot"]["mp"], expected.mp)
                        self.assertNotIn("ai", entry["snapshot"])
                    snapshots[side] = [entry["snapshot"] for entry in built]
                expected = self.reference({**snapshots, "shuffle_order": parameters["shuffle_order"]})
                self.assertEqual(result["value"]["plan"]["order"], expected["order"])
                self.assertEqual(result["value"]["scope"], "base_turn_preparation")
        self.assertEqual(self.byte_snapshot(), before)

    # {
    #   責務: [test_preparation_refuses_bad_records_limits_or_reconstruction_without_repairs: 検証: preparation refuses bad records limits or reconstruction without repairs]
    #   処理: [1: 検証: preparation refuses bad records limits or reconstruction without repairs]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_preparation_refuses_bad_records_limits_or_reconstruction_without_repairs(self):
        joined = [{"allies": value, "enemies": [combatant.record("enemy")], "shuffle_order": []}
                  for value in (None, {}, [None], [combatant.record("one"), combatant.record("one")],
                                [combatant.record(str(index)) for index in range(5)],
                                [combatant.record(species="missing")], [combatant.record(level=101)])]
        before = self.byte_snapshot()
        for value in self.invoke(joined=joined)["joined"]:
            self.assert_case(value)
            self.assertFalse(value["value"]["ok"])
            self.assertEqual(value["value"]["reason"], "team_reconstruction_failed")
        self.assertEqual(self.byte_snapshot(), before)
        path = self.content / "data/species/slime/stats.json"
        path.write_text('{"schema_version":99,"levels":{}}', encoding="utf-8")
        before = self.byte_snapshot()
        result = self.invoke(joined=[{"allies": [combatant.record()], "enemies": [], "shuffle_order": []}])["joined"][0]
        self.assertFalse(result["value"]["ok"])
        self.assertEqual(self.byte_snapshot(), before)

    # {
    #   責務: [test_individuals_learned_ai_parties_items_and_content_remain_byte_identical: 検証: individuals learned ai parties items and content remain byte identical]
    #   処理: [1: 検証: individuals learned ai parties items and content remain byte identical]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_individuals_learned_ai_parties_items_and_content_remain_byte_identical(self):
        self.seed_state(current_party=["owned", None, None, None], private={"keep": True})
        monster = self.seed_record("owned", level=50, plus_choices=[], equipment_id=None)
        ai = {"schema_version": 1, "battles": 123, "actions": 456, "action_preferences": {"attack": 0.9}}
        self.write("monsters/owned/ai.json", ai)
        self.write("items/items.json", {"items": {"herb": 99}, "private": True})
        self.write("parties/owned.json", {"members": ["owned"]})
        before = self.byte_snapshot()
        self.invoke([case("plan", request(), mutate_result=True),
                     case("check", {**request(), "actor": key("allies", "ally")}, mutate_result=True)],
                    joined=[{"allies": [{"monster": monster, "ai": ai}], "enemies": [combatant.record("enemy")],
                             "shuffle_order": [key("enemies", "enemy"), key("allies", "owned")], "mutate_result": True}])
        self.assertEqual(self.byte_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
