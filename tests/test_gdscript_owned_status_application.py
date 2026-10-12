"""個体が保持する最新一覧への一件付与・治療との連続操作を実Godot/Pythonで検証します。"""
# {
#   責務: [test_gdscript_owned_status_application: 付与準備/予測非変更/実更新・重複・拒否・独立コピーと保存ダミー不変を確認します]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import copy
import importlib.util
import itertools
import unittest

import test_gdscript_combatant_status as owner_fixture
import test_gdscript_status_apply as apply_fixture
import test_gdscript_status_cure as cure_fixture


# {
#   責務: [OwnedStatusApplicationBoundaryTests: 個体の一件付与をSession/HPMP/保存/AI/乱数生成へ無断接続しないことを確認します]
#   フィールド: []
# }
class OwnedStatusApplicationBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_owner_delegates_rules_and_preserves_external_boundaries: 状態所有者が純粋付与へ委譲し、禁止依存を持たないことを確認します]
    #   処理: [1: 付与契約への委譲と、I/O/乱数生成/実資源/場面への未依存をソースで検査します]
    #   引数: [self: 状態所有者の責務境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_owner_delegates_rules_and_preserves_external_boundaries(self):
        source = (cure_fixture.godot_fixture.ROOT / "gdscript/engine/combatant_status_state.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "RandomNumberGenerator", "randf(", ".pay_mp(", ".heal(",
                          "res://application/", "res://data/", "res://ui/", "res://engine/combatant_state.gd"):
            self.assertNotIn(forbidden, source)
        self.assertIn("ApplyContract.quote_application", source)
        self.assertNotIn("MULTIPLIERS", source)


# {
#   責務: [OwnedStatusApplicationTests: 専用保存ダミー領域と最新一覧に対する付与/治療の実Godot/Python比較を所有します]
#   フィールド: [
#     folder: 共用fixtureが作る要求と保存ダミーの専用一時領域（Path）
#     saved_files: 毎起動後にbyte不変を確認する五種類の保存ダミー（list[Path]）
#   ]
# }
@unittest.skipUnless(cure_fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for owned-status application")
class OwnedStatusApplicationTests(unittest.TestCase):
    setUp = owner_fixture.CombatantStatusTests.setUp
    run_probe = owner_fixture.CombatantStatusTests.run_probe

    # {
    #   責務: [test_sequences_match_python_latest_state_and_do_not_stack: 最新一覧で付与予測/実更新を繰り返し、重複しない結果をPython正本へ合わせます]
    #   処理: [1: 確率/耐性/初期状態の組合せで準備・予測・付与・再予測/付与の前後一覧と独立性を照合します]
    #   引数: [self: 付与の正本互換と所有状態保持を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_sequences_match_python_latest_state_and_do_not_stack(self):
        decks = [[], ["poison"], ["bleeding"], [{"id": "bleeding", "metadata": {"deck": [1]}}],
                 [{"id": " bleeding "}, {"id": "lock", "removable": False}]]
        cases = []
        for effects, chance, resistance, roll in itertools.product(
            decks, (-1, 0, 0.4, 1, "0.4"), ("very_weak", "weak", "normal", "strong", "immune", "absorb", "mod"),
            (0, 0.4, 0.9)
        ):
            request = {"effect": {"id": " bleeding ", "display_name": "出血", "chance": chance,
                                  "metadata": {"deck": ["a", {"kept": True}]}},
                       "resistance_level": resistance, "roll": roll}
            preparation = copy.deepcopy(request)
            preparation.pop("roll")
            steps = [{"operation": "prepare_application", "request": preparation}]
            steps += [{"operation": operation, "request": copy.deepcopy(request)}
                      for operation in ("quote_application", "apply", "quote_application", "apply")]
            cases.append({"effects": copy.deepcopy(effects), "steps": steps})
        results = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(results), len(cases))
        for case, observed in zip(cases, results):
            with self.subTest(case=case):
                current = copy.deepcopy(case["effects"])
                self.assertTrue(observed["started"]["ok"])
                self.assertTrue(observed["initial_independent"])
                self.assertTrue(observed["input_preserved"])
                for step, actual in zip(case["steps"], observed["steps"]):
                    result = actual["result"]
                    self.assertTrue(result["ok"], result)
                    self.assertTrue(actual["result_independent"])
                    self.assertTrue(actual["request_preserved"])
                    self.assertEqual(actual["before"], {"status_effects": current})
                    if step["operation"] == "prepare_application":
                        self.assertEqual(result["effects"], current)
                        self.assertEqual(actual["after"], actual["before"])
                        continue
                    expected = apply_fixture.StatusApplyQuoteTests.python_result(
                        self, {"status_effects": copy.deepcopy(current), **step["request"]})
                    for field, value in expected.items():
                        self.assertEqual(result[field], value, field)
                    if step["operation"] == "apply":
                        current = copy.deepcopy(expected["resulting_status_effects"])
                    self.assertEqual(result["scope"], "combatant_status_apply" if step["operation"] == "apply" else "status_apply_quote")
                    self.assertEqual(actual["after"], {"status_effects": current})
                self.assertEqual(observed["snapshot"], {"status_effects": current})

    # {
    #   責務: [test_uninitialized_retry_and_reinitialization_preserve_state: 未開始付与・不正開始後の再試行と付与後リセット拒否を確認します]
    #   処理: [1: 三つの付与APIを未開始で拒否し、正常開始/一件付与後の再開始拒否で状態を保持します]
    #   引数: [self: 状態所有者の初期化境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_uninitialized_retry_and_reinitialization_preserve_state(self):
        request = {"effect": {"id": "mod", "chance": 1}, "roll": 0}
        steps = [{"operation": operation, "request": request}
                 for operation in ("prepare_application", "quote_application", "apply")]
        steps += [{"operation": "start", "effects": []}, {"operation": "apply", "request": request},
                  {"operation": "start", "effects": []}]
        cases = [{"initialize": False, "effects": [], "steps": steps}, {"effects": None, "steps": steps}]
        for observed in self.run_probe({"cases": cases})["results"]:
            for actual in observed["steps"][:3]:
                self.assertEqual(actual["result"], {"ok": False, "reason": "not_initialized"})
                self.assertEqual(actual["after"], {})
            self.assertTrue(observed["steps"][3]["result"]["ok"])
            self.assertTrue(observed["steps"][4]["result"]["applied"])
            self.assertEqual(observed["steps"][5]["result"], {"ok": False, "reason": "already_initialized"})
            self.assertEqual(observed["snapshot"], {"status_effects": [{"id": "mod", "display_name": "mod", "removable": True}]})

    # {
    #   責務: [test_apply_then_cure_then_reapply_uses_latest_state: 付与・重複・治療・再付与の順で古い予測を使わず最新一覧を更新します]
    #   処理: [1: 出血一件を追加し、同ID再追加を抑止し、治療後に再付与可能になることを確認します]
    #   引数: [self: 付与/治療の連続更新を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_apply_then_cure_then_reapply_uses_latest_state(self):
        effect = {"id": "bleeding", "chance": 1, "metadata": {"deck": [1, {"kept": True}]}}
        request = {"effect": effect, "roll": 0}
        duplicate = {"effect": effect}
        steps = [{"operation": "quote_application", "request": request},
                 {"operation": "apply", "request": request},
                 {"operation": "apply", "request": duplicate},
                 {"operation": "cure", "request": {"cure_chance": 1, "roll": 0}},
                 {"operation": "prepare_application", "request": duplicate},
                 {"operation": "apply", "request": request}]
        observed = self.run_probe({"cases": [{"effects": [{"id": "lock", "removable": False}], "steps": steps}]})["results"][0]
        self.assertEqual(len(observed["steps"][0]["after"]["status_effects"]), 1)
        self.assertEqual(len(observed["steps"][1]["after"]["status_effects"]), 2)
        self.assertEqual(observed["steps"][2]["result"]["outcome"], "already_present")
        self.assertFalse(observed["steps"][2]["result"]["roll_required"])
        self.assertEqual(len(observed["steps"][3]["after"]["status_effects"]), 1)
        self.assertTrue(observed["steps"][4]["result"]["roll_required"])
        self.assertTrue(observed["steps"][5]["result"]["applied"])
        self.assertEqual(observed["steps"][1]["result"], observed["steps"][5]["result"])
        self.assertTrue(all(step["result_independent"] and step["request_preserved"] for step in observed["steps"]))

    # {
    #   責務: [test_rejected_external_overrides_and_native_invalid_values_preserve_latest_state: 古い一覧/結果・未知要求・不正定義/roll・native不正値を拒否し、一覧を保持します]
    #   処理: [1: 三つの付与APIで拒否と前後不変を確認し、予測/実更新の型や範囲を緩めません]
    #   引数: [self: 不正要求と状態保護を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_rejected_external_overrides_and_native_invalid_values_preserve_latest_state(self):
        requests = [None, [], False, {}, {"effect": None}, {"effect": {"id": "mod", "chance": True}},
                    {"effect": {"id": "mod", "chance": "nan"}}, {"effect": {"id": 1, "chance": 1}}]
        for field, value in itertools.product(
            ("status_effects", "resulting_status_effects", "remaining_status_effects", "applied", "effect_index", "mp_cost"),
            (False, 0, [], {}, None)
        ):
            requests.append({"effect": {"id": "mod", "chance": 1}, "roll": 0, field: value})
        steps = [{"operation": operation, "request": request}
                 for operation, request in itertools.product(("prepare_application", "quote_application", "apply"), requests)]
        steps += [{"operation": operation, "request": {"effect": {"id": "mod", "chance": 1}, "roll": value}}
                  for operation, value in itertools.product(("quote_application", "apply"), (None, -1, 1, True, "0"))]
        steps.append({"operation": "prepare_application", "request": {"effect": {"id": "mod", "chance": 1}, "roll": None}})
        for operation, value in itertools.product(("prepare_application", "quote_application", "apply"), (None, True, [], {})):
            request = {"effect": {"id": "mod", "chance": 1}, "resistance_level": value}
            if operation != "prepare_application":
                request["roll"] = 0
            steps.append({"operation": operation, "request": request})
        for operation, special in itertools.product(("quote_application", "apply"), ("nan", "inf", "object", "cycle")):
            steps.append({"operation": operation, "request": {"effect": {"id": "mod", "chance": 1}, "roll": 0},
                          "special": {"field": "roll", "value": special}})
        for operation, field, special in itertools.product(("prepare_application", "quote_application", "apply"),
                                                           ("chance", "metadata"), ("nan", "inf", "object", "cycle")):
            request = {"effect": {"id": "mod", "chance": 1}}
            if operation != "prepare_application":
                request["roll"] = 0
            steps.append({"operation": operation, "request": request,
                          "special": {"target": "effect", "field": field, "value": special}})
        nested = "leaf"
        for _ in range(31):
            nested = [nested]
        steps.append({"operation": "apply", "request": {"effect": {"id": "mod", "chance": 1, "metadata": nested}, "roll": 0}})
        initial = [{"id": "lock", "removable": False, "metadata": {"deck": [1]}}, "poison"]
        observed = self.run_probe({"cases": [{"effects": initial, "steps": steps}]})["results"][0]
        self.assertEqual(len(observed["steps"]), len(steps))
        for actual in observed["steps"]:
            self.assertFalse(actual["result"]["ok"], actual)
            self.assertEqual(set(actual["result"]), {"ok", "reason"})
            self.assertEqual(actual["before"], actual["after"])
            self.assertTrue(actual["result_independent"])
            self.assertTrue(actual["request_preserved"])
        self.assertEqual(observed["snapshot"], {"status_effects": initial})

    # {
    #   責務: [test_no_op_defaults_roll_boundaries_and_independent_owners: 不成立/同値roll/未知IDの省略値と個体間の独立性を確認します]
    #   処理: [1: 判定不要の付与なしと成功一件を別所有者で観測し、候補と返却値の編集が伝播しないことを確認します]
    #   引数: [self: 付与境界と個体の独立保持を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_no_op_defaults_roll_boundaries_and_independent_owners(self):
        cases = []
        for request in ({ "effect": {} }, {"effect": {"id": "mod"}}, {"effect": {"id": "mod", "chance": -1}},
                        {"effect": {"id": "mod", "chance": 1}, "resistance_level": "immune"},
                        {"effect": {"id": "mod", "chance": 0.4}, "roll": 0.4},
                        {"effect": {"id": "　mod　", "chance": 1}, "roll": 0}):
            preparation = copy.deepcopy(request)
            preparation.pop("roll", None)
            cases.append({"effects": [], "steps": [{"operation": "prepare_application", "request": preparation},
                                                   {"operation": "quote_application", "request": request},
                                                   {"operation": "apply", "request": request}]})
        observations = self.run_probe({"cases": cases})["results"]
        for observed in observations:
            self.assertTrue(all(step["result"]["ok"] for step in observed["steps"]))
            self.assertTrue(all(step["result_independent"] and step["request_preserved"] for step in observed["steps"]))
            self.assertEqual(observed["steps"][0]["before"], observed["steps"][0]["after"])
            self.assertEqual(observed["steps"][1]["before"], observed["steps"][1]["after"])
        self.assertTrue(all(observed["snapshot"] == {"status_effects": []} for observed in observations[:-1]))
        self.assertEqual(observations[-1]["snapshot"], {"status_effects": [{"id": "mod", "display_name": "mod", "removable": True}]})

    # {
    #   責務: [test_lifecycle_checker_requires_real_append_and_duplicate_preservation: 性能検査が実付与五件・準備/予測非変更・重複保持まで固定期待値で検査することを確認します]
    #   処理: [1: 少量の実計測結果をCLIへ渡し、更新なし・拒否・原本不保持・不正時間の結果を拒否します]
    #   引数: [self: 付与ライフサイクルの性能結果検査を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_lifecycle_checker_requires_real_append_and_duplicate_preservation(self):
        result = self.run_probe({"performance": True, "status_apply_state": True, "iterations": 20, "samples": 3, "warmup": 2})
        path = cure_fixture.godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_status_cure.py"
        spec = importlib.util.spec_from_file_location("owned_apply_checker", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        checker = module.StatusCureBenchmark("unused", argparse.Namespace(iterations=20, samples=3, warmup=2, status_apply_state=True))
        self.assertTrue(checker._valid_apply_state_result(result), result)
        for field, value in (("after", result["after_quote"]), ("after_repeat", result["after_quote"]),
                             ("prepared", {}), ("prediction", result["quote"]), ("quote", {"ok": False}),
                             ("repeated", result["quote"]), ("input_preserved", False),
                             ("microseconds", -1), ("microseconds", 3001), ("iterations", 1)):
            changed = copy.deepcopy(result)
            changed[field] = value
            self.assertFalse(checker._valid_apply_state_result(changed), field)
