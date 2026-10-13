"""陣営と個体IDで指定する状態集合の一件付与を実Godot/Pythonで検証します。実セーブは使いません。"""
# {
#   責務: [test_gdscript_roster_status_application: 状態集合の対象分離・最新付与/治療・拒否・独立コピー・保存ダミー保持を確認します]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import copy
import importlib.util
import itertools
import unittest

import test_gdscript_normal_attack_action as normal
import test_gdscript_status_apply as apply_fixture
import test_gdscript_status_cure as fixture


# {
#   責務: [roster_case: 同IDの両陣営に数値参加者と明示初期状態を用意し、専用観測条件を作ります]
#   処理: [1: 陣営別に独立した六キー参加者と状態配列を作り、ケース条件を上書きします]
#   引数: [
#     effects: 全個体へ深くコピーする初期状態。Noneなら空配列です
#     count: 両陣営それぞれの参加数。既定は1、八体試験では4です（int）
#     changes: ケースごとの開始/連続操作条件を上書きする値
#   ]
#   戻り値: [result: snapshots/initial_statuses/stepsと任意条件を持つ専用ケース（dict）]
# }
def roster_case(effects=None, count=1, **changes):
    snapshots = {side: [normal.member("same" if count == 1 else f"same_{index}") for index in range(count)]
                 for side in ("allies", "enemies")}
    statuses = {side: {entry["identity"]["id"]: copy.deepcopy(effects or []) for entry in members}
                for side, members in snapshots.items()}
    return {"snapshots": snapshots, "initial_statuses": statuses, "steps": [], **changes}


# {
#   責務: [RosterStatusApplicationBoundaryTests: 集合からの付与委譲がHPMP/予約/I/O/乱数/AI/画面へ無断依存しないことを確認します]
#   フィールド: []
# }
class RosterStatusApplicationBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_roster_delegates_to_owner_without_gameplay_or_io_duplication: 状態集合は対象検査と個体所有者への呼び出しだけを担当するか静的確認します]
    #   処理: [1: 集合の禁止依存/付与計算の未実装と、Sessionへの付与入口を未追加であることを確認します]
    #   引数: [self: 状態集合の責務境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_roster_delegates_to_owner_without_gameplay_or_io_duplication(self):
        root = fixture.godot_fixture.ROOT / "gdscript"
        source = (root / "engine/battle_status_state.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "RandomNumberGenerator", "randf(", "MULTIPLIERS",
                          "res://application/", "res://data/", "res://ui/", ".pay_mp(", ".heal("):
            self.assertNotIn(forbidden, source)
        self.assertIn('.apply(request)', source)
        self.assertNotIn("func apply_status_application(", (root / "engine/battle_session.gd").read_text(encoding="utf-8"))


# {
#   責務: [RosterStatusApplicationTests: 専用要求/保存ダミー領域と対象別の実Godot/Python比較を所有します]
#   フィールド: [
#     folder: 共用fixtureが作る要求/保存ダミーの専用領域（Path）
#     saved_files: 毎起動後にbyte不変を確認する五種類の保存ダミー（list[Path]）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for roster-status application")
class RosterStatusApplicationTests(unittest.TestCase):
    setUp = fixture.StatusCureQuoteTests.setUp

    # {
    #   責務: [observe: 状態集合の専用区分を付けて実Godotへ渡し、診断と要求/保存ダミーのbyte保持を確認します]
    #   処理: [1: 共用起動/保存保持fixtureへ要求を渡し、実観測結果を返します]
    #   引数: [
    #     self: 専用領域と保存ダミーの所有者
    #     payload: casesまたは性能条件を指定する辞書（dict）
    #   ]
    #   戻り値: [result: 診断とファイル保持を確認済みの実Godot観測（dict）]
    # }
    def observe(self, payload):
        return fixture.StatusCureQuoteTests.run_probe(self, {**payload, "roster_status_apply": True})

    # {
    #   責務: [test_latest_sequences_match_python_and_preserve_other_participants: 両陣営の同IDを分離して準備/予測/付与/重複を実Pythonへ合わせます]
    #   処理: [1: 陣営/初期状態/耐性/判定値の組合せで対象だけの前後更新と原本/返却独立性を照合します]
    #   引数: [self: 対象分離と正本互換を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_latest_sequences_match_python_and_preserve_other_participants(self):
        cases = []
        for side, initial, resistance, roll in itertools.product(
            ("allies", "enemies"), ([], ["bleeding"], [{"id": "lock", "removable": False}, "poison"]),
            ("very_weak", "weak", "normal", "immune", "absorb", "mod"), (0, 0.4, 0.9)
        ):
            key = normal.key(side, "same")
            request = {"effect": {"id": " bleeding ", "display_name": "出血", "chance": 0.4,
                                  "metadata": {"deck": [1, {"kept": True}]}},
                       "resistance_level": resistance, "roll": roll}
            preparation = copy.deepcopy(request)
            preparation.pop("roll")
            steps = [{"operation": "prepare_application", "key": key, "request": preparation}]
            steps += [{"operation": operation, "key": key, "request": copy.deepcopy(request)}
                      for operation in ("quote_application", "apply", "quote_application", "apply")]
            cases.append(roster_case(initial, steps=steps))
        results = self.observe({"cases": cases})["results"]
        self.assertEqual(len(results), len(cases))
        for case, actual in zip(cases, results):
            with self.subTest(case=case):
                current = copy.deepcopy(case["initial_statuses"])
                self.assertTrue(actual["started"]["ok"])
                self.assertTrue(actual["input_preserved"])
                self.assertTrue(actual["initial_independent"])
                for step, observation in zip(case["steps"], actual["steps"]):
                    key = step["key"]
                    result = observation["result"]
                    self.assertTrue(result["ok"], result)
                    self.assertEqual(observation["before"], {"teams": current, "scope": "battle_status_only"})
                    self.assertTrue(observation["independent"])
                    self.assertTrue(observation["request_preserved"])
                    if step["operation"] == "prepare_application":
                        self.assertEqual(result["effects"], current[key["side"]][key["id"]])
                    else:
                        expected = apply_fixture.StatusApplyQuoteTests.python_result(
                            self, {"status_effects": copy.deepcopy(current[key["side"]][key["id"]]), **step["request"]})
                        for field, value in expected.items():
                            self.assertEqual(result[field], value, field)
                        if step["operation"] == "apply":
                            current[key["side"]][key["id"]] = copy.deepcopy(expected["resulting_status_effects"])
                        self.assertEqual(result["scope"], "combatant_status_apply" if step["operation"] == "apply" else "status_apply_quote")
                    self.assertEqual(observation["after"], {"teams": current, "scope": "battle_status_only"})
                self.assertEqual(actual["snapshot"], {"teams": current, "scope": "battle_status_only"})

    # {
    #   責務: [test_eight_targets_cure_and_reapply_are_isolated: 八体の各対象への付与/重複/治療/再付与が他の七体を変えないことを確認します]
    #   処理: [1: 両陣営同IDの全対象で一件追加/一件除去/再追加と全体読取の独立性を照合します]
    #   引数: [self: 八体の更新対象分離を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_eight_targets_cure_and_reapply_are_isolated(self):
        cases = []
        for side, index in itertools.product(("allies", "enemies"), range(4)):
            key = normal.key(side, f"same_{index}")
            request = {"effect": {"id": "bleeding", "chance": 1, "metadata": {"deck": ["kept"]}}, "roll": 0}
            steps = [{"operation": "apply", "key": key, "request": request},
                     {"operation": "apply", "key": key, "request": {"effect": request["effect"]}},
                     {"operation": "cure", "key": key, "request": {"cure_chance": 1, "roll": 0}},
                     {"operation": "apply", "key": key, "request": request},
                     {"operation": "read", "key": key}]
            cases.append(roster_case([{"id": "lock", "removable": False}], count=4, steps=steps))
        for case, actual in zip(cases, self.observe({"cases": cases})["results"]):
            with self.subTest(key=case["steps"][0]["key"]):
                key = case["steps"][0]["key"]
                target_side, target_id = key["side"], key["id"]
                added = [{"id": "lock", "removable": False},
                         {"id": "bleeding", "metadata": {"deck": ["kept"]}, "display_name": "bleeding", "removable": True}]
                self.assertTrue(actual["steps"][0]["result"]["applied"])
                self.assertFalse(actual["steps"][1]["result"]["applied"])
                self.assertFalse(actual["steps"][1]["result"]["roll_required"])
                self.assertTrue(actual["steps"][2]["result"]["cured"])
                self.assertTrue(actual["steps"][3]["result"]["applied"])
                self.assertEqual(actual["steps"][4]["result"], {"ok": True, "snapshot": {"status_effects": added}})
                for side, team in actual["snapshot"]["teams"].items():
                    for identifier, effects in team.items():
                        self.assertEqual(effects, added if (side, identifier) == (target_side, target_id) else [{"id": "lock", "removable": False}])
                self.assertTrue(all(step["independent"] and step["request_preserved"] for step in actual["steps"]))

    # {
    #   責務: [test_initialization_failure_retry_empty_roster_and_reinitialization: 未開始/不正初期状態後の再試行・空集合・付与後リセット拒否を確認します]
    #   処理: [1: 三つの付与APIを未開始で拒否し、開始成功後の付与/再開始拒否で最新状態を保持します]
    #   引数: [self: 集合の原子的な初期化境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_initialization_failure_retry_empty_roster_and_reinitialization(self):
        valid = roster_case()
        key = normal.key("allies", "same")
        request = {"effect": {"id": "mod", "chance": 1}, "roll": 0}
        steps = [{"operation": operation, "key": key, "request": request}
                 for operation in ("prepare_application", "quote_application", "apply")]
        steps += [{"operation": "start", "snapshots": valid["snapshots"], "initial_statuses": valid["initial_statuses"]},
                  {"operation": "apply", "key": key, "request": request},
                  {"operation": "start", "snapshots": valid["snapshots"], "initial_statuses": valid["initial_statuses"]}]
        bad = roster_case()
        bad["initial_statuses"]["enemies"]["same"] = [{"id": None}]
        cases = [roster_case(no_start=True, steps=steps), {**bad, "steps": steps}]
        for actual in self.observe({"cases": cases})["results"]:
            for observation in actual["steps"][:3]:
                self.assertEqual(observation["result"], {"ok": False, "reason": "not_initialized"})
                self.assertEqual(observation["before"], {})
                self.assertEqual(observation["after"], {})
            self.assertTrue(actual["steps"][3]["result"]["ok"])
            self.assertTrue(actual["steps"][4]["result"]["applied"])
            self.assertEqual(actual["steps"][5]["result"], {"ok": False, "reason": "already_initialized"})
            self.assertEqual(actual["snapshot"]["teams"]["enemies"]["same"], [])
            self.assertEqual(len(actual["snapshot"]["teams"]["allies"]["same"]), 1)
        empty = roster_case(count=0, steps=[{"operation": "apply", "key": key, "request": request}])
        actual = self.observe({"cases": [empty]})["results"][0]
        self.assertTrue(actual["started"]["ok"])
        self.assertEqual(actual["steps"][0]["result"], {"ok": False, "reason": "actor_missing"})
        self.assertEqual(actual["snapshot"], {"teams": {"allies": {}, "enemies": {}}, "scope": "battle_status_only"})

    # {
    #   責務: [test_invalid_target_and_request_values_preserve_all_participants: 不正対象・未知要求・外部一覧/予測・native不正値を拒否し、全状態を保持します]
    #   処理: [1: 三つの付与入口へ不正キー/条件を渡し、全体snapshotの前後不変と返却独立性を照合します]
    #   引数: [self: 対象検査と状態保護を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_target_and_request_values_preserve_all_participants(self):
        operations = ("prepare_application", "quote_application", "apply")
        keys = [None, [], False, {}, {"side": "allies"}, {"side": "ALLIES", "id": "same"},
                {"side": "allies", "id": ""}, {"side": "allies", "id": 1}, {"side": "allies", "id": "missing"},
                {"side": "enemies", "id": "same", "extra": False}]
        steps = [{"operation": operation, "key": key, "request": {"effect": {"id": "mod", "chance": 1}, "roll": 0}}
                 for operation, key in itertools.product(operations, keys)]
        requests = [None, [], {}, {"effect": None}, {"effect": {"id": "mod", "chance": True}},
                    {"effect": {"id": "mod", "chance": 1}, "resistance_level": False}]
        for field, value in itertools.product(("status_effects", "resulting_status_effects", "applied", "mp_cost", "target"), (False, 0, [], {})):
            requests.append({"effect": {"id": "mod", "chance": 1}, "roll": 0, field: value})
        # 八体ケースに存在するIDを使い、不正要求を対象不在でなく条件検査まで到達させます。
        key = normal.key("allies", "same_0")
        steps += [{"operation": operation, "key": key, "request": request}
                  for operation, request in itertools.product(operations, requests)]
        steps += [{"operation": operation, "key": key, "request": {"effect": {"id": "mod", "chance": 1}, "roll": value}}
                  for operation, value in itertools.product(("quote_application", "apply"), (None, -1, 1, True, "0"))]
        steps.append({"operation": "prepare_application", "key": key,
                      "request": {"effect": {"id": "mod", "chance": 1}, "roll": None}})
        for operation, special in itertools.product(operations, ("nan", "inf", "object", "cycle", "non_string_key")):
            request = {"effect": {"id": "mod", "chance": 1}}
            if operation != "prepare_application":
                request["roll"] = 0
            steps.append({"operation": operation, "key": key, "request": request,
                          "special": {"target": "effect", "field": "metadata", "value": special}})
        for operation, special in itertools.product(("quote_application", "apply"), ("nan", "inf", "object", "cycle")):
            steps.append({"operation": operation, "key": key, "request": {"effect": {"id": "mod", "chance": 1}, "roll": 0},
                          "special": {"field": "roll", "value": special}})
        for operation, special in itertools.product(operations, ("nan", "object", "cycle")):
            steps.append({"operation": operation, "key": key, "request": {"effect": {"id": "mod", "chance": 1}, "roll": 0},
                          "special": {"target": "key", "field": "id", "value": special}})
        case = roster_case([{"id": "lock", "removable": False, "metadata": {"deck": [1]}}, "poison"], count=4, steps=steps)
        actual = self.observe({"cases": [case]})["results"][0]
        self.assertEqual(len(actual["steps"]), len(steps))
        for step, observation in zip(steps, actual["steps"]):
            self.assertFalse(observation["result"]["ok"], observation)
            self.assertEqual(set(observation["result"]), {"ok", "reason"})
            if step["key"] == key:
                self.assertNotEqual(observation["result"]["reason"], "actor_missing")
            self.assertEqual(observation["before"], observation["after"])
            self.assertTrue(observation["independent"])
            self.assertTrue(observation["request_preserved"])
        self.assertEqual(actual["snapshot"], {"teams": case["initial_statuses"], "scope": "battle_status_only"})

    # {
    #   責務: [test_empty_id_zero_chance_immune_and_roll_failure_do_not_modify_roster: 正常な付与なしと省略値/同値rollが全体状態を保持することを確認します]
    #   処理: [1: 不成立理由の異なるケースを対象一体へ要求し、準備/予測/実更新の前後不変を照合します]
    #   引数: [self: 正常な不成立と判定要否を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_empty_id_zero_chance_immune_and_roll_failure_do_not_modify_roster(self):
        cases = []
        for request in ({"effect": {}}, {"effect": {"id": "mod"}}, {"effect": {"id": "mod", "chance": -1}},
                        {"effect": {"id": "mod", "chance": 1}, "resistance_level": "immune"},
                        {"effect": {"id": "mod", "chance": 0.4}, "roll": 0.4}):
            preparation = copy.deepcopy(request)
            preparation.pop("roll", None)
            key = normal.key("enemies", "same")
            cases.append(roster_case(["sleep"], steps=[
                {"operation": "prepare_application", "key": key, "request": preparation},
                {"operation": "quote_application", "key": key, "request": request},
                {"operation": "apply", "key": key, "request": request}]))
        for case, actual in zip(cases, self.observe({"cases": cases})["results"]):
            self.assertTrue(all(step["result"]["ok"] and step["before"] == step["after"] for step in actual["steps"]))
            self.assertEqual(actual["snapshot"], {"teams": case["initial_statuses"], "scope": "battle_status_only"})

    # {
    #   責務: [test_benchmark_validator_requires_targeted_real_update_and_other_seven_unchanged: 性能検査が一体の実追加と他七体保持・原本/予測非変更を固定値で検査するか確認します]
    #   処理: [1: 少量実Godot結果は通過し、速い拒否/欠落/対象誤り/原本不保持/時間超過は拒否するか照合します]
    #   引数: [self: 八体ライフサイクル性能の実結果検査を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_benchmark_validator_requires_targeted_real_update_and_other_seven_unchanged(self):
        result = self.observe({"performance": True, "iterations": 20, "samples": 3, "warmup": 2})
        path = fixture.godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_status_cure.py"
        spec = importlib.util.spec_from_file_location("roster_status_checker", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        checker = module.StatusCureBenchmark("unused", argparse.Namespace(iterations=20, samples=3, warmup=2, roster_status_apply=True))
        self.assertTrue(checker._valid_roster_apply_result(result), result)
        for field, value in (("started", {"ok": False}), ("prepared", {}), ("prediction", result["applied"]),
                             ("applied", {"ok": False}), ("repeated", result["applied"]), ("single", {}),
                             ("input_preserved", False), ("microseconds", -1), ("microseconds", 3001), ("actors", 7)):
            changed = copy.deepcopy(result)
            changed[field] = value
            self.assertFalse(checker._valid_roster_apply_result(changed), field)
        changed = copy.deepcopy(result)
        changed["statuses"]["teams"]["allies"]["member_2"] = changed["statuses"]["teams"]["enemies"]["member_2"]
        self.assertFalse(checker._valid_roster_apply_result(changed))
        self.assertFalse(checker._valid_roster_apply_result({"ok": False}))
