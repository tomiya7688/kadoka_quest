"""実PythonのCombatantと実Godotの状態能力値予測を照合します。利用者のセーブは使いません。"""
# {
#   責務: [test_gdscript_status_stats: 出血・一時速度倍率・端数・拒否・独立性と性能判定の境界を検査します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import importlib.util
import itertools
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

import test_battle_bleeding as python_fixture
import test_gdscript_roster as godot_fixture
import test_gdscript_status_cure as cure_fixture


# {
#   責務: [StatusStatBoundaryTests: 状態能力値の予測がI/O・UI・乱数・実資源所有者へ依存しないことを確認します]
#   フィールド: []
# }
class StatusStatBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_pure_dependency_boundary: 純粋補正APIの禁止依存と、Sessionへ未接続の境界を確認します]
    #   処理: [1: 純粋実装とSession/Applicationのソースを読み、計算と実行が混在しないことを確認します]
    #   引数: [self: 計算責務の境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_pure_dependency_boundary(self):
        source = (godot_fixture.ROOT / "gdscript/engine/status_stat_contract.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                          "battle_session", "combatant_state", "RandomNumberGenerator", "randf("):
            self.assertNotIn(forbidden, source)
        for relative in ("engine/battle_session", "application/battle_session_application"):
            source = (godot_fixture.ROOT / f"gdscript/{relative}.gd").read_text(encoding="utf-8")
            self.assertNotIn("status_stat_contract", source)


# {
#   責務: [StatusStatQuoteTests: 専用要求と保存ダミーを使い、実Godot/Pythonの能力値一致を検査します]
#   フィールド: [
#     folder: 共用fixtureが用意する一時要求領域（Path）
#     saved_files: 毎起動後にbyte不変を検査する個体/AI/items/party/stateダミー（list[Path]）
#   ]
# }
@unittest.skipUnless(godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real status-stat probes")
class StatusStatQuoteTests(unittest.TestCase):
    setUp = cure_fixture.StatusCureQuoteTests.setUp

    # {
    #   責務: [observe: 保存ダミーと要求byteを保護する共用実Godot起動へ、状態能力値の専用区分を渡します]
    #   処理: [1: 専用ケースまたは性能条件を実プローブへ渡して観測辞書を返します]
    #   引数: [
    #     self: 一時要求領域と保存ダミーを持つテストケース
    #     payload: casesまたはperformance/iterations/samples/warmupの辞書（dict）
    #   ]
    #   戻り値: [result: 診断なしとbyte保持を確認済みの観測結果（dict）]
    # }
    def observe(self, payload):
        return cure_fixture.StatusCureQuoteTests.run_probe(self, {"status_stats": True, **payload})

    # {
    #   責務: [case: ケース間で状態を共有しない実効防御力・速度の要求を作ります]
    #   処理: [1: 状態を深くコピーし、補正前の防御力・速度と一時速度倍率を付けます]
    #   引数: [
    #     effects: 現在の状態一覧（list）
    #     defense: 状態補正前の非負防御力（int）
    #     speed: 一時倍率と状態補正を掛ける前の非負速度（int）
    #     multiplier: 一時速度倍率（float）
    #   ]
    #   戻り値: [result: requestを持つ専用ケース（dict）]
    # }
    @staticmethod
    def case(effects, defense=51, speed=41, multiplier=1.0):
        return {"request": {"defense": defense, "speed": speed, "speed_multiplier": multiplier,
                            "status_effects": copy.deepcopy(effects)}}

    # {
    #   責務: [test_quotes_match_python_without_changing_combatant_or_record: 実Pythonの二つのpropertyと状態能力値予測を同一入力で照合します]
    #   処理: [1: 出血・重複・未知ID・空白・倍率・数値境界の直積を実Godotへ渡し、原個体/AI/HPMP保持も確認します]
    #   引数: [self: 状態能力値のPython互換範囲を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_quotes_match_python_without_changing_combatant_or_record(self):
        decks = [[], ["bleeding"], [{"id": "bleeding", "removable": False}],
                 ["bleeding", {"id": "bleeding"}], [" bleeding "], ["Bleeding"],
                 ["poison", "sleep", {"id": "mod", "stat_multipliers": {"defense": 0.2}}],
                 [{"metadata": {"deck": [True, None, 1]}}]]
        cases = [self.case(deck, defense, speed, multiplier)
                 for deck, (defense, speed), multiplier in itertools.product(
                     decks, ((0, 0), (1, 1), (3, 3), (11, 11), (51, 41), (2**53 - 1, 1)),
                     (0, 0.1, 0.5, 1, 1.5, 2, 1e-300))]
        observations = self.observe({"cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        for case, observed in zip(cases, observations):
            request = case["request"]
            with self.subTest(request=request):
                actor = python_fixture.make_combatant("isolated")
                actor.stats.update(defense=request["defense"], speed=request["speed"])
                actor.status_effects = copy.deepcopy(request["status_effects"])
                actor.speed_multiplier = request["speed_multiplier"]
                actor.record.ai["kept"] = {"deck": [1, 2]}
                before = copy.deepcopy(actor)
                self.assertEqual(observed["result"], {"ok": True, "scope": "status_stat_quote",
                                                      "defense": actor.defense, "speed": actor.speed})
                self.assertEqual(actor, before)
                self.assertTrue(observed["input_preserved"])
                self.assertTrue(observed["result_independent"])

    # {
    #   責務: [test_defaults_rounding_lower_bounds_and_latest_status: 倍率省略・積の順序・下限と出血解除後の再計算を固定値で確認します]
    #   処理: [1: 同一補正前数値で出血あり/なしを連続予測し、途中整数化や状態キャッシュがないことを確認します]
    #   引数: [self: 固定期待値を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_defaults_rounding_lower_bounds_and_latest_status(self):
        default = self.case(["bleeding"], 11, 3)
        default["request"].pop("speed_multiplier")
        cases = [default, self.case(["bleeding"], 11, 3, 1.5), self.case([], 11, 3, 1.5),
                 self.case(["bleeding"], 0, 0, 0), self.case([], 1, 2**53 - 1)]
        expected = [(9, 2), (9, 4), (11, 4), (0, 1), (1, 2**53 - 1)]
        for observed, (defense, speed) in zip(self.observe({"cases": cases})["results"], expected):
            self.assertEqual(observed["result"], {"ok": True, "scope": "status_stat_quote", "defense": defense, "speed": speed})

    # {
    #   責務: [test_invalid_requests_return_no_partial_stats: 不正型・欠損・未知キー・範囲超過を部分成功なしで拒否します]
    #   処理: [1: 各入力境界へ不正値を渡し、失敗の二キー形式と入力保持を確認します]
    #   引数: [self: 予測の拒否境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_requests_return_no_partial_stats(self):
        cases = [{"request": request} for request in (None, [], {}, "invalid")]
        for field in ("defense", "speed", "status_effects"):
            case = self.case([])
            case["request"].pop(field)
            cases.append(case)
        for field, values in (("defense", (None, True, "1", -1, 0.5, 2**53, {}, [])),
                              ("speed", (None, False, "1", -1, 0.5, 2**53, {}, [])),
                              ("speed_multiplier", (None, True, "1.5", -0.1, 2**53, {}, [])),
                              ("status_effects", (None, {}, [1], [True], [[]], ["bleeding", {"id": 1}],
                                                  [{"display_name": 1}], [{"removable": 0}]))):
            for value in values:
                case = self.case([])
                case["request"][field] = value
                cases.append(case)
        for key, value in itertools.product(("guard", "attack_multiplier", "stats", "result"), (False, 0, "", {}, [])):
            case = self.case([])
            case["request"][key] = value
            cases.append(case)
        cases.append(self.case(["bleeding"], speed=2**53 - 1, multiplier=1.1))
        for observed in self.observe({"cases": cases})["results"]:
            with self.subTest(result=observed):
                self.assertFalse(observed["result"]["ok"])
                self.assertEqual(set(observed["result"]), {"ok", "reason"})
                self.assertTrue(observed["input_preserved"])
                self.assertTrue(observed["result_independent"])

    # {
    #   責務: [test_native_values_and_json_depth_are_validated_before_copy: 非有限・Object・循環・非文字列キーと状態深さ上限を確認します]
    #   処理: [1: 専用プローブ内の不正値は拒否し、状態一覧の深さ32だけは正常に予測できることを確認します]
    #   引数: [self: JSON外の入力と深さ境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_native_values_and_json_depth_are_validated_before_copy(self):
        cases = []
        for field, value in itertools.product(("defense", "speed", "speed_multiplier"), ("nan", "inf", "object")):
            case = self.case([{"id": "bleeding"}])
            case["special"] = {"target": "request", "field": field, "value": value}
            cases.append(case)
        for value in ("nan", "inf", "object", "non_string_key", "cycle"):
            case = self.case([{"id": "bleeding"}])
            case["special"] = {"target": "effect", "field": "metadata", "value": value}
            cases.append(case)
        request_key = self.case([])
        request_key["special"] = {"target": "request", "field": "unused", "value": "non_string_key"}
        cases.append(request_key)
        for observed in self.observe({"cases": cases})["results"]:
            self.assertFalse(observed["result"]["ok"])
            self.assertEqual(set(observed["result"]), {"ok", "reason"})
            self.assertTrue(observed["input_preserved"])
        depth_cases = []
        for container in (list, dict):
            nested = "leaf"
            for _ in range(30):
                nested = [nested] if container is list else {"child": nested}
            depth_cases += [self.case([{"id": "bleeding", "metadata": nested}]),
                            self.case([{"id": "bleeding", "metadata": [nested] if container is list else {"child": nested}}])]
        results = self.observe({"cases": depth_cases})["results"]
        for offset in (0, 2):
            self.assertTrue(results[offset]["result"]["ok"])
            self.assertEqual(results[offset + 1]["result"], {"ok": False, "reason": "invalid_status_effects"})

    # {
    #   責務: [test_benchmark_checks_fixed_success_inputs_and_timing: 実Godotの性能観測だけが通り、偽の成功や拒否/原本変更が通らないことを確認します]
    #   処理: [1: 少数回の実測を検査し、結果・入力・反復条件・時間を改変した観測は拒否させます]
    #   引数: [self: 性能checkerの期待値を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_benchmark_checks_fixed_success_inputs_and_timing(self):
        path = godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_status_stats.py"
        specification = importlib.util.spec_from_file_location("status_stat_benchmark", path)
        module = importlib.util.module_from_spec(specification)
        with mock.patch.object(sys, "path", [str(path.parent), *sys.path]):
            specification.loader.exec_module(module)
        benchmark = module.StatusStatBenchmark(str(godot_fixture.GODOT), SimpleNamespace(iterations=32, samples=3, warmup=4))
        result = self.observe(benchmark.configuration)
        self.assertTrue(benchmark.valid_result(result), result)
        for key, value in (("quote", {"ok": False, "reason": "invalid"}), ("input_preserved", False),
                           ("iterations", 1), ("samples", 0), ("warmup", 0), ("request", {}),
                           ("microseconds", -1), ("microseconds", 3001)):
            changed = copy.deepcopy(result)
            changed[key] = value
            self.assertFalse(benchmark.valid_result(changed))
        self.assertFalse(benchmark.valid_result({}))
