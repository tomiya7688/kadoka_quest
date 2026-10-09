"""戦闘状態一覧の独立保持・予測非変更・一件更新を実GodotとPythonで検証します。実セーブは使いません。"""
# {
#   責務: [test_gdscript_combatant_status: 初期化・連続治療・厳密拒否・原本/返却値の独立性・保存非変更を検証します]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import copy
import importlib.util
import itertools
import unittest

import test_gdscript_status_cure as cure_fixture


# {
#   責務: [CombatantStatusBoundaryTests: 状態所有者を数値資源・Session・保存・AI・乱数生成から分離する境界を確認します]
#   フィールド: []
# }
class CombatantStatusBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_status_owner_does_not_change_numeric_snapshot_or_session_contract: 状態保持を数値snapshotと行動実行へ無断接続しないことを確認します]
    #   処理: [1: 新規所有者の禁止依存と、既存数値資源/Session/applicationの未接続を確認します]
    #   引数: [self: 状態所有者の境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_status_owner_does_not_change_numeric_snapshot_or_session_contract(self):
        root = cure_fixture.godot_fixture.ROOT / "gdscript"
        source = (root / "engine/combatant_status_state.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                          "res://engine/combatant_state.gd", "battle_session", "randf(", "RandomNumberGenerator",
                          ".pay_mp(", ".heal("):
            self.assertNotIn(forbidden, source)
        for name in ("engine/combatant_state", "engine/battle_session", "engine/heal_skill_action",
                     "application/combatant_builder", "application/battle_session_application"):
            self.assertNotIn("combatant_status_state", (root / f"{name}.gd").read_text(encoding="utf-8"))


# {
#   責務: [CombatantStatusTests: 保存ダミー領域と実Godotの連続状態操作/Python比較を所有します]
#   フィールド: [
#     folder: 共用起動プローブが使う専用要求領域（Path）
#     saved_files: byte不変を確認する個体・AI・items・party・stateの保存ダミー（list[Path]）
#   ]
# }
@unittest.skipUnless(cure_fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real combatant-status probes")
class CombatantStatusTests(unittest.TestCase):
    # {
    #   責務: [setUp: 状態操作を実保存データから分離した専用要求領域と保存ダミーを用意します]
    #   処理: [1: 共用の保存ダミーfixtureへ一時領域の作成を委譲します]
    #   引数: [self: 専用領域と保存ダミーを持つ所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        cure_fixture.StatusCureQuoteTests.setUp(self)

    # {
    #   責務: [run_probe: 状態所有者の明示区分を付け、共用の実Godot起動/診断/byte保持検証へ委譲します]
    #   処理: [1: コピー要求へstatus_state=trueを付け、共用プローブで検証します]
    #   引数: [
    #     self: 専用領域と保存ダミーを持つ所有者
    #     payload: 状態操作ケース一覧またはライフサイクル性能条件（dict）
    #   ]
    #   戻り値: [result: 診断なし・要求と保存ダミーのbyte不変を確認した実Godot観測（dict）]
    # }
    def run_probe(self, payload):
        copied = copy.deepcopy(payload)
        copied["status_state"] = True
        return cure_fixture.StatusCureQuoteTests.run_probe(self, copied)

    # {
    #   責務: [test_sequence_matches_python_and_quotes_do_not_update_owned_effects: 最新一覧を使う連続一件治療と予測非変更を実Pythonへ合わせます]
    #   処理: [1: 状態順・表示名・確率・判定値の組合せでquote/cureを二回繰り返し、Python実治療と前後一覧を照合します]
    #   引数: [self: 順序付き状態の連続操作を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_sequence_matches_python_and_quotes_do_not_update_owned_effects(self):
        locked = {"id": "lock", "removable": False, "metadata": {"deck": [1, {"kept": [True, None]}]}}
        poison = {"id": "poison", "display_name": "毒"}
        decks = [[], [locked], [""], [{}], [poison, poison, "sleep"],
                 [locked, poison, "sleep"], [{"id": "mod", "metadata": {"deck": [1]}}]]
        cases = []
        for effects, chance, roll in itertools.product(decks, (-1, 0, 0.03, 1, 2, "0.03"), (0, 0.02, 0.03, 0.5)):
            steps = [{"operation": operation, "request": {"cure_chance": chance, "roll": roll}}
                     for operation in ("quote", "cure", "quote", "cure")]
            cases.append({"effects": copy.deepcopy(effects), "steps": steps})
        results = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(results), len(cases))
        for case, observation in zip(cases, results):
            with self.subTest(case=case):
                current = copy.deepcopy(case["effects"])
                self.assertTrue(observation["started"]["ok"])
                self.assertTrue(observation["initial_independent"])
                self.assertTrue(observation["input_preserved"])
                for step, actual in zip(case["steps"], observation["steps"]):
                    before = copy.deepcopy(current)
                    expected = cure_fixture.StatusCureQuoteTests.python_result(
                        self, {"status_effects": current, **step["request"]})
                    result = actual["result"]
                    self.assertTrue(result["ok"], result)
                    for key, value in expected.items():
                        self.assertEqual(result[key], value, key)
                    if step["operation"] == "cure":
                        current = copy.deepcopy(expected["remaining_status_effects"])
                    self.assertEqual(result["scope"], "status_cure_quote" if step["operation"] == "quote" else "combatant_status_cure")
                    self.assertEqual(actual["before"], {"status_effects": before})
                    self.assertEqual(actual["after"], {"status_effects": current})
                    self.assertTrue(actual["result_independent"])
                self.assertEqual(observation["snapshot"], {"status_effects": current})

    # {
    #   責務: [test_uninitialized_invalid_start_retry_and_reinitialization: 未開始・初期化失敗からの再試行・開始済みリセット拒否を確認します]
    #   処理: [1: 未開始操作と不正開始後の正常開始、治療後の再初期化拒否を観測します]
    #   引数: [self: 状態所有者の初期化を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_uninitialized_invalid_start_retry_and_reinitialization(self):
        request = {"cure_chance": 1, "roll": 0}
        steps = [{"operation": "quote", "request": request}, {"operation": "cure", "request": request},
                 {"operation": "start", "effects": ["poison", "sleep"]},
                 {"operation": "cure", "request": request}, {"operation": "start", "effects": []}]
        cases = [{"initialize": False, "effects": [], "steps": steps}, {"effects": None, "steps": steps}]
        for observation in self.run_probe({"cases": cases})["results"]:
            self.assertEqual(observation["steps"][0]["result"], {"ok": False, "reason": "not_initialized"})
            self.assertEqual(observation["steps"][1]["result"], {"ok": False, "reason": "not_initialized"})
            self.assertTrue(observation["steps"][2]["result"]["ok"])
            self.assertEqual(observation["steps"][3]["result"]["cured_name"], "poison")
            self.assertEqual(observation["steps"][4]["result"], {"ok": False, "reason": "already_initialized"})
            self.assertEqual(observation["snapshot"], {"status_effects": ["sleep"]})
            self.assertTrue(observation["input_preserved"])
            self.assertTrue(observation["initial_independent"])

    # {
    #   責務: [test_rejected_requests_and_stale_quote_overrides_preserve_owned_state: 不正要求と外部一覧/予測結果の上書きを拒否し、所有一覧を保持します]
    #   処理: [1: 型・確率・判定値・未知キーと外部状態/候補位置をquote/cureへ渡し、前後不変を確認します]
    #   引数: [self: 厳密要求と状態保持を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_rejected_requests_and_stale_quote_overrides_preserve_owned_state(self):
        invalid_requests = [None, [], False, {}, {"cure_chance": None}, {"cure_chance": True},
                            {"cure_chance": 2**53, "roll": 0}, {"cure_chance": "nan", "roll": 0},
                            {"cure_chance": 1}, {"cure_chance": 0, "roll": None}]
        invalid_requests += [{"cure_chance": 0.03, "roll": value} for value in (-1, 1, True, "0.02")]
        for field, value in itertools.product(("status_effects", "candidate_index", "remaining_status_effects", "cured", "mp_cost"),
                                              (False, 0, [], {}, None)):
            invalid_requests.append({"cure_chance": 1, "roll": 0, field: value})
        steps = [{"operation": operation, "request": request}
                 for operation, request in itertools.product(("quote", "cure"), invalid_requests)]
        for operation, field, value in itertools.product(("quote", "cure"), ("cure_chance", "roll"), ("nan", "inf")):
            steps.append({"operation": operation, "request": {"cure_chance": 1, "roll": 0},
                          "special": {"field": field, "value": value}})
        effects = [{"id": "lock", "removable": False, "metadata": {"deck": [1]}}, "poison", "sleep"]
        observation = self.run_probe({"cases": [{"effects": effects, "steps": steps}]})["results"][0]
        self.assertEqual(len(observation["steps"]), len(steps))
        for index, actual in enumerate(observation["steps"]):
            with self.subTest(index=index):
                self.assertFalse(actual["result"]["ok"], actual)
                self.assertEqual(actual["before"], actual["after"])
                self.assertTrue(actual["result_independent"])
        self.assertEqual(observation["snapshot"], {"status_effects": effects})

    # {
    #   責務: [test_invalid_initial_types_depth_and_native_values_do_not_initialize: 不正一覧・深さ超過・非有限/Object/循環値で開始済みにしないことを確認します]
    #   処理: [1: 不正な初期一覧を拒否した後、空一覧の開始へ正常に再試行できることを確認します]
    #   引数: [self: 初期一覧検証と再試行を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_initial_types_depth_and_native_values_do_not_initialize(self):
        invalid = [None, {}, False, 0, "poison", [0], [None], [{"removable": 1}], [{"id": None}],
                   [{"display_name": False}], [{"metadata": 2**53}]]
        nested = "bottom"
        for _ in range(33):
            nested = [nested]
        invalid.append([{"metadata": nested}])
        cases = [{"effects": effects, "steps": [{"operation": "start", "effects": []}]} for effects in invalid]
        cases += [{"effects": [{}], "special_effect": {"field": "metadata", "value": value},
                   "steps": [{"operation": "start", "effects": []}]}
                  for value in ("nan", "inf", "object", "cycle")]
        observations = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        for index, observation in enumerate(observations):
            with self.subTest(index=index):
                self.assertEqual(observation["started"], {"ok": False, "reason": "invalid_status_effects"})
                self.assertEqual(observation["steps"][0]["before"], {})
                self.assertTrue(observation["steps"][0]["result"]["ok"])
                self.assertEqual(observation["snapshot"], {"status_effects": []})
                self.assertTrue(observation["initial_independent"])
                self.assertTrue(observation["input_preserved"])

    # {
    #   責務: [test_candidate_free_state_needs_no_roll_and_does_not_change: 空一覧/解除不可だけの状態は判定値なしで不成立・一覧不変になることを確認します]
    #   処理: [1: 候補なしのquote/cureで省略/null判定値を受理し、指定済み不正値は拒否します]
    #   引数: [self: 候補なし状態の判定と保持を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_candidate_free_state_needs_no_roll_and_does_not_change(self):
        cases = [{"effects": effects, "steps": [
            {"operation": "quote", "request": {"cure_chance": 1}},
            {"operation": "cure", "request": {"cure_chance": 0, "roll": None}},
            {"operation": "cure", "request": {"cure_chance": 1, "roll": True}}]}
                 for effects in ([], [{"id": "lock", "removable": False}])]
        for case, observation in zip(cases, self.run_probe({"cases": cases})["results"]):
            for actual in observation["steps"][:2]:
                self.assertTrue(actual["result"]["ok"])
                self.assertFalse(actual["result"]["roll_required"])
                self.assertFalse(actual["result"]["cured"])
                self.assertEqual(actual["before"], actual["after"])
            self.assertEqual(observation["steps"][2]["result"], {"ok": False, "reason": "invalid_cure_roll"})
            self.assertEqual(observation["snapshot"], {"status_effects": case["effects"]})

    # {
    #   責務: [test_lifecycle_benchmark_and_checker_verify_real_update: 性能経路が新規初期化・予測非変更・毒一件実解除を検査することを確認します]
    #   処理: [1: 少数反復の実Godot観測をCLI検査器へ渡し、更新なし/不正区分の観測は拒否することを確認します]
    #   引数: [self: ライフサイクル性能の実結果を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_lifecycle_benchmark_and_checker_verify_real_update(self):
        result = self.run_probe({"performance": True, "iterations": 20, "samples": 3, "warmup": 2})
        self.assertTrue(result["input_preserved"])
        self.assertEqual(len(result["started"]["snapshot"]["status_effects"]), 4)
        self.assertEqual(result["after_quote"], result["started"]["snapshot"])
        self.assertEqual(len(result["after"]["status_effects"]), 3)
        self.assertEqual(result["quote"]["cured_name"], "毒")
        path = cure_fixture.godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_status_cure.py"
        spec = importlib.util.spec_from_file_location("kadoka_status_benchmark", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        checker = module.StatusCureBenchmark("unused", argparse.Namespace(iterations=20, samples=3, warmup=2, status_state=True))
        self.assertTrue(checker._valid_state_result(result))
        for field, value in (("after", result["after_quote"]), ("started", {"ok": False}),
                             ("prediction", result["quote"]), ("after_quote", result["after"])):
            damaged = copy.deepcopy(result)
            damaged[field] = value
            self.assertFalse(checker._valid_state_result(damaged), field)
