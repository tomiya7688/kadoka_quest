"""状態順序の性能checkerが拒否や壊れた固定入力を速い成功として受理しないことを検査します。"""
# {
#   責務: [test_gdscript_status_turn_order_performance: 実Godotの少数反復と改変観測で性能検査の期待値を検証します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import importlib.util
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

import test_gdscript_roster as godot
import test_gdscript_status_cure as cure


# {
#   責務: [StatusTurnPerformanceTests: 専用保存ダミーを所有し、状態順序の固定期待値と性能判定の健全性を検査します]
#   フィールド: [
#     folder: 共用fixtureが用意する要求JSONの専用一時領域（Path）
#     saved_files: 起動後にbyte不変を検査する個体/AI/items/party/stateダミー（list）
#   ]
# }
@unittest.skipUnless(godot.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real status turn-order timing")
class StatusTurnPerformanceTests(unittest.TestCase):
    setUp = cure.StatusCureQuoteTests.setUp

    # {
    #   責務: [test_checker_requires_fixed_inputs_stable_order_and_valid_timing: 実測の正常計画だけが性能checkerを通過し、入力/出力の偽装や不正時間が拒否されることを確認します]
    #   処理: [1: 少数反復を実Godotで測り、順序/速度/原本/計測条件を一つずつ改変して拒否を確認します]
    #   引数: [self: 実Godotの観測と性能checkerを検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_checker_requires_fixed_inputs_stable_order_and_valid_timing(self):
        # 実Godotの正常観測を基準にし、性能checker自体の偽陽性を改変ケースで調べます。
        path = godot.ROOT / "tools/performance-check/script/check_gdscript_status_turn_order.py"
        specification = importlib.util.spec_from_file_location("status_turn_benchmark", path)
        module = importlib.util.module_from_spec(specification)
        with mock.patch.object(sys, "path", [str(path.parent), *sys.path]):
            specification.loader.exec_module(module)
        benchmark = module.StatusTurnOrderBenchmark(str(godot.GODOT), SimpleNamespace(iterations=32, samples=3, warmup=4))
        result = cure.StatusCureQuoteTests.run_probe(self, benchmark.configuration)
        self.assertTrue(benchmark.valid_result(result), result)
        for field, value in (("plan", {"ok": False}), ("request", {}), ("input_preserved", False), ("iterations", 1),
                             ("samples", True), ("warmup", None), ("microseconds", -1), ("microseconds", 3001),
                             ("microseconds", True), ("microseconds", float("nan")), ("microseconds", float("inf"))):
            changed = copy.deepcopy(result)
            changed[field] = value
            self.assertFalse(benchmark.valid_result(changed), field)
        for field in ("initial", "order", "speeds"):
            changed = copy.deepcopy(result)
            changed["plan"][field] = []
            self.assertFalse(benchmark.valid_result(changed), field)
        changed = copy.deepcopy(result)
        changed["request"]["allies"][0]["stats"]["speed"] = 999
        changed["plan"]["speeds"]["allies"]["member_0"] = 999
        self.assertFalse(benchmark.valid_result(changed))
        for field in ("ok", "speed"):
            changed = copy.deepcopy(result)
            if field == "ok":
                changed["plan"]["ok"] = 1
            else:
                changed["plan"]["speeds"]["allies"]["member_2"] = True
            self.assertFalse(benchmark.valid_result(changed), field)
        self.assertFalse(benchmark.valid_result({}))
