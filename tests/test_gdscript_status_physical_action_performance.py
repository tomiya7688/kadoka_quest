"""付与付き物理の性能checkerが、高速拒否・不完全更新・偽の時間条件を合格にしないことを確認します。"""
# {
#   責務: [test_gdscript_status_physical_action_performance: 実行観測を使って性能checkerの固定期待値/時間境界と反復条件拒否を検査します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import importlib.util
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

from gdscript_status_action_fixture import StatusActionFixture, fixture


# {
#   責務: [StatusPhysicalPerformanceTests: 専用性能プローブの正常実更新と、checkerの合否境界を検査します]
#   フィールド: [folder: 共用fixtureの専用要求/保存ダミー領域（Path）]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for status action benchmark probes")
class StatusPhysicalPerformanceTests(StatusActionFixture, unittest.TestCase):
    # {
    #   責務: [test_checker_validates_actual_updates_and_rejects_corrupted_observations: 実Godotの更新結果を照合し、観測値の破損や不正な時間条件を拒否します]
    #   処理: [1: 少数回の実更新を取得し、合成時間を使ったchecker単体検査で各境界を確認します]
    #   引数: [self: checker単体の合否境界を検査するテストケース]
    #   戻り値: [result: なし（None）。標準条件の性能合格は専用CLIで別に検査します]
    # }
    def test_checker_validates_actual_updates_and_rejects_corrupted_observations(self):
        path = fixture.godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_status_physical_action.py"
        specification = importlib.util.spec_from_file_location("status_action_benchmark", path)
        module = importlib.util.module_from_spec(specification)
        with mock.patch.object(sys, "path", [str(path.parent), *sys.path]):
            specification.loader.exec_module(module)
        benchmark = module.StatusPhysicalActionBenchmark(str(fixture.godot_fixture.GODOT),
                                                          SimpleNamespace(iterations=32, samples=2, warmup=8))
        observed = self.observe(benchmark.configuration)
        self.assertGreater(observed["microseconds"], 0)
        # 時間の単体境界は合成値で固定し、短い反復の実時間を標準性能の合格根拠にしません。
        timing_fixture = {**observed, "microseconds": 1.0}
        self.assertTrue(benchmark.valid_result(timing_fixture), {"numeric": observed["numeric"], "last": observed["last"]})
        self.assertTrue(benchmark.valid_result({**timing_fixture, "microseconds": 3000}))
        for field, value in (("original_source", {}), ("original_order", []), ("completed", 0), ("numeric", {}),
                             ("statuses", {}), ("last", {}), ("input_preserved", False), ("iterations", 8),
                             ("microseconds", -1), ("microseconds", 3001), ("microseconds", True)):
            changed = copy.deepcopy(timing_fixture)
            changed[field] = value
            self.assertFalse(benchmark.valid_result(changed), field)

    # {
    #   責務: [test_incomplete_eight_action_batches_are_refused: 反復または事前実行が八の倍数でない要求を計測前に拒否します]
    #   処理: [1: 不完全バッチの二条件を実プローブへ渡し、時間や更新結果を返さない拒否を確認します]
    #   引数: [self: 反復条件の拒否境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_incomplete_eight_action_batches_are_refused(self):
        for iterations, warmup in ((1, 0), (8, 1)):
            self.assertEqual(self.observe({"performance": True, "iterations": iterations, "samples": 1, "warmup": warmup}),
                             {"ok": False, "reason": "complete_rounds_required"})
