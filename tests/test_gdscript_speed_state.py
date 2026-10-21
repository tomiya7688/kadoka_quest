"""速度倍率の保持・延長・復元を実Python/実Godotで比較し、保存ダミーの不変を確認します。"""
# {
#   責務: [test_gdscript_speed_state: 一体の速度所有契約・八体の独立性・厳密な拒否・性能結果を検査します]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import importlib.util
import json
import random
import subprocess
from types import SimpleNamespace
import unittest

from kadoka_quest.core.battle import BattleEngine
import test_gdscript_status_cure as fixture


# {
#   責務: [python_trace: Python正本の一時倍率更新と期限経過から、各操作後の三キー状態を求めます]
#   処理: [1: 初期倍率を独立保持し、指定操作を実Pythonヘルパーへ渡して更新後の状態を収集します]
#   引数: [operations: startから始まる正常な速度強化操作列（list）]
#   戻り値: [result: 各操作の直後にPythonが保持する倍率・残り期間・復元先の列（list）]
# }
def python_trace(operations):
    target = SimpleNamespace(speed_multiplier=1.0, timed_buff_turns={}, timed_buff_baselines={})
    snapshots = []
    # 実装間比較の期待値へ最大値や期限規則を複写せず、既存の戦闘処理を実行します。
    for operation in operations:
        method = operation["method"]
        value = operation.get("value")
        if method == "start":
            target.speed_multiplier = 1.0 if "value" not in operation else value
        elif method == "apply":
            BattleEngine._apply_multiplier(target, "speed_multiplier", value["multiplier"], value.get("duration"))
        elif method == "elapse":
            BattleEngine._tick_timed_buffs(target)
        snapshots.append({"speed_multiplier": target.speed_multiplier,
                          "remaining_turns": target.timed_buff_turns.get("speed_multiplier", 0),
                          "baseline_multiplier": target.timed_buff_baselines.get("speed_multiplier", target.speed_multiplier)})
    return snapshots


# {
#   責務: [SpeedStateBoundaryTests: 速度所有者をI/O・乱数・HPMP・Session・保存から独立させる境界を確認します]
#   フィールド: []
# }
class SpeedStateBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_owner_has_no_io_rng_numeric_resources_or_session_connection: 速度保持だけの実装を既存Sessionへ無断接続しないことを確認します]
    #   処理: [1: 所有者の禁止依存と、Session/Application/数値資源からの新しい直接参照の未追加を検査します]
    #   引数: [self: 責務境界を検査するテストケース]
    #   戻り値: [result: なし（None）。境界違反はassertionで失敗します]
    # }
    def test_owner_has_no_io_rng_numeric_resources_or_session_connection(self):
        # 保持契約の完成を、スキル行動やラウンド終端への接続完了と混同しません。
        root = fixture.godot_fixture.ROOT / "gdscript"
        source = (root / "engine/combatant_speed_state.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "OS.", "Input.", "Time.", "randf(", "randi(",
                          "res://data/", "res://ui/", "res://application/", "battle_session",
                          "combatant_state.gd", "status_effect", ".pay_mp(", ".learn("):
            self.assertNotIn(forbidden, source)
        for relative in ("engine/battle_session.gd", "engine/combatant_state.gd",
                         "application/battle_session_application.gd"):
            self.assertNotIn("combatant_speed_state", (root / relative).read_text(encoding="utf-8"))


# {
#   責務: [SpeedStateTests: 専用要求領域・保存ダミーと、実Godotでの速度強化操作の比較を所有します]
#   フィールド: [
#     folder: 要求JSONを置く専用一時領域（Path）
#     saved_files: 内容不変を確認する個体/AI/items/party/stateダミーの一覧（list）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real speed-state probes")
class SpeedStateTests(unittest.TestCase):
    setUp = fixture.StatusCureQuoteTests.setUp

    # {
    #   責務: [run_probe: 速度専用プローブを起動し、診断と要求/保存ダミーのバイト不変を確認します]
    #   処理: [1: 一時要求を書いて実Godotを呼び、終了状態・診断・ハッシュと専用出力を照合します]
    #   引数: [
    #     self: 一時領域と保存ダミーを持つテストケース
    #     payload: 操作ケース一覧または性能条件の辞書（dict）
    #   ]
    #   戻り値: [result: 診断なしで復号した観測辞書（dict）]
    # }
    def run_probe(self, payload):
        path = self.folder / "speed-request.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        before = {item: hashlib.sha256(item.read_bytes()).digest() for item in (path, *self.saved_files)}
        process = subprocess.run(
            [str(fixture.godot_fixture.GODOT), "--headless", "--path", str(fixture.godot_fixture.ROOT / "gdscript"),
             "--script", "res://tests/run_speed_multiplier_probe.gd", "--", str(path)],
            cwd=self.folder, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        # JSONの結果だけでは成功にせず、解析/実行診断と実ファイルの非変更も確認します。
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        self.assertNotIn("SCRIPT ERROR", process.stderr)
        self.assertNotIn("ERROR:", process.stderr)
        self.assertEqual(before, {item: hashlib.sha256(item.read_bytes()).digest() for item in before})
        for line in process.stdout.splitlines():
            if line.startswith("KADOKA_SPEED_STATE_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(process.stderr + process.stdout)

    # {
    #   責務: [observe: 全操作で元要求・返却値・他個体と、拒否時の所有状態が変わらないことを確認します]
    #   処理: [1: ケース一覧を実プローブへ渡し、各独立性フラグと拒否時保持を検査します]
    #   引数: [
    #     self: 実Godotの観測を取得するテストケース
    #     cases: operationsを持つ専用ケースの一覧（list）
    #   ]
    #   戻り値: [result: ケースと同数の観測辞書の一覧（list）]
    # }
    def observe(self, cases):
        observed = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(observed), len(cases))
        for case in observed:
            self.assertTrue(case["input_preserved"])
            for item in case["observations"]:
                self.assertTrue(item["result_independent"])
                self.assertTrue(item["others_unchanged"])
                self.assertTrue(item["rejection_preserved"])
        return observed

    # {
    #   責務: [test_sequences_match_python_independent_maxima_and_baseline_updates: 再付与・期間なし・期限切れの各中間状態を実Pythonへ照合します]
    #   処理: [1: 固定とseed付き操作列を実行し、全操作直後の三キー状態を比較します]
    #   引数: [self: 実装間の状態一致を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_sequences_match_python_independent_maxima_and_baseline_updates(self):
        generator = random.Random(123)
        cases = []
        # 弱い長期間への再付与と、強化中の期間なし付与を必ず通り、単純な上書き実装を検出します。
        for initial in (0, 0.75, 1, 1.2, 2, 2**53 - 1):
            operations = [{"method": "start", "value": initial}, {"method": "apply", "value": {"multiplier": 2, "duration": 2}},
                          {"method": "apply", "value": {"multiplier": 1.5, "duration": 6}},
                          {"method": "apply", "value": {"multiplier": 1.75}},
                          *[{"method": "elapse"} for _ in range(7)]]
            cases.append({"operations": operations})
        for _index in range(60):
            operations = [{"method": "start", "value": generator.choice((0, 0.5, 1.0, 1.2, 2.5))}]
            for _step in range(30):
                if generator.random() < 0.4:
                    operations.append({"method": "elapse"})
                else:
                    operations.append({"method": "apply", "value": {
                        "multiplier": generator.choice((0, 0.5, 1, 1.3, 1.5, 2)),
                        "duration": generator.choice((None, 1, 2, 6))}})
            cases.append({"operations": operations})
        for index, (case, observed) in enumerate(zip(cases, self.observe(cases))):
            for step, (expected, actual) in enumerate(zip(python_trace(case["operations"]), observed["observations"])):
                with self.subTest(case=index, step=step):
                    self.assertTrue(actual["result"]["ok"])
                    self.assertEqual(actual["snapshot"], expected)
                    self.assertIs(type(actual["snapshot"]["remaining_turns"]), int)

    # {
    #   責務: [test_exact_numeric_bounds_and_null_duration_preserve_timer: JSON整数精度上限の倍率/期間と明示nullの期間なし付与を確認します]
    #   処理: [1: 上限値の期間を一減らし、期間なしの弱い倍率で残り期間が消えないことを固定値へ照合します]
    #   引数: [self: 数値の受理上限と期間なし付与の境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_exact_numeric_bounds_and_null_duration_preserve_timer(self):
        # 巨大期間を全消費せず一回だけ進め、境界値の丸めや期間なし付与による誤解除を確認します。
        maximum = 2**53 - 1
        operations = [{"method": "start", "value": 0},
                      {"method": "apply", "value": {"multiplier": maximum, "duration": maximum}},
                      {"method": "elapse"}, {"method": "apply", "value": {"multiplier": 0, "duration": None}}]
        observed = self.observe([{"operations": operations}])[0]
        self.assertEqual(observed["final"][0], {"speed_multiplier": maximum, "remaining_turns": maximum - 1,
                                               "baseline_multiplier": 0})
        self.assertTrue(all(item["result"]["ok"] for item in observed["observations"]))

    # {
    #   責務: [test_uninitialized_retry_reinitialization_and_expiration_once: 開始前拒否・不正初回の再試行・再初期化拒否と一回だけの期限切れを確認します]
    #   処理: [1: 未開始から期限切れ後までの明示列を実行し、拒否理由とexpiredの正確な位置を照合します]
    #   引数: [self: 初期化と期限境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_uninitialized_retry_reinitialization_and_expiration_once(self):
        operations = [{"method": "apply", "value": {"multiplier": 1.5}}, {"method": "elapse"},
                      {"method": "start", "value": False}, {"method": "snapshot"}, {"method": "start"},
                      {"method": "start", "value": 2}, {"method": "apply", "value": {"multiplier": 1.5, "duration": 1.0}},
                      {"method": "elapse"}, {"method": "elapse"}]
        observed = self.observe([{"operations": operations}])[0]["observations"]
        self.assertEqual([observed[i]["result"]["reason"] for i in (0, 1, 2, 5)],
                         ["not_initialized", "not_initialized", "invalid_speed_multiplier", "already_initialized"])
        self.assertEqual(observed[3]["snapshot"], {})
        self.assertTrue(observed[7]["result"]["expired"])
        self.assertFalse(observed[8]["result"]["expired"])
        self.assertEqual(observed[8]["snapshot"], {"speed_multiplier": 1, "remaining_turns": 0, "baseline_multiplier": 1})

    # {
    #   責務: [test_invalid_requests_and_native_values_never_partially_update: 不正な型・未知キー・非有限/native値・精度超過を全更新前に拒否します]
    #   処理: [1: 開始値と既存強化への不正付与を組み合わせ、拒否フラグと状態保持を確認します]
    #   引数: [self: 公開入力境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_requests_and_native_values_never_partially_update(self):
        invalid = (None, True, False, "", "1.5", [], {}, -0.01, 2**53)
        requests = [None, True, [], {}, {"multiplier": 2, "unknown": 1}, {"speed_multiplier": 2},
                    {"multiplier": 2, "snapshot": {}}, {"multiplier": 2, "remaining_turns": 4}]
        requests += [{"multiplier": value, "duration": 6} for value in invalid]
        requests += [{"multiplier": 9, "duration": value} for value in (0, -1, True, "2", [], {}, 1.5, 2**53)]
        cases = [{"operations": [{"method": "start", "value": value}, {"method": "start"}]} for value in invalid]
        cases += [{"operations": [{"method": "start"}, {"method": "apply", "value": {"multiplier": 1.5, "duration": 3}},
                                  {"method": "apply", "value": value}]} for value in requests]
        for special in ("nan", "inf", "negative_inf", "object", "vector"):
            cases.append({"operations": [{"method": "start", "special": special}, {"method": "start"}]})
            for field in ("multiplier", "duration"):
                cases.append({"operations": [{"method": "start"},
                    {"method": "apply", "value": {"multiplier": 1.5, "duration": 3}},
                    {"method": "apply", "value": {"multiplier": 9, "duration": 6}, "special": special, "field": field}]})
        for index, observed in enumerate(self.observe(cases)):
            with self.subTest(case=index):
                rejected = observed["observations"][0 if len(observed["observations"]) == 2 else 2]
                self.assertFalse(rejected["result"]["ok"])

    # {
    #   責務: [test_eight_owners_returned_snapshots_and_inputs_remain_independent: 八体の倍率と期間を分け、他個体や返却辞書の編集で変更しないことを確認します]
    #   処理: [1: 八体を別倍率で開始して一体ずつ強化/経過し、各個体の最終状態を固定値へ比較します]
    #   引数: [self: 個体ごとの所有境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_eight_owners_returned_snapshots_and_inputs_remain_independent(self):
        operations = [{"method": "start", "owner": index, "value": index + 1} for index in range(8)]
        operations += [{"method": "apply", "owner": index, "value": {"multiplier": 10, "duration": index + 1}}
                       for index in range(8)]
        operations += [{"method": "elapse", "owner": index} for index in range(8)]
        case = {"operations": operations}
        original = copy.deepcopy(case)
        observed = self.observe([case])[0]
        self.assertEqual(case, original)
        for index, snapshot in enumerate(observed["final"]):
            self.assertEqual(snapshot, {"speed_multiplier": 1 if index == 0 else 10,
                                        "remaining_turns": index, "baseline_multiplier": index + 1})

    # {
    #   責務: [test_benchmark_rejects_failed_incomplete_or_fake_fast_results: 性能検査が実更新と全反復を要求し、速い拒否・欠落・改変結果を拒否することを確認します]
    #   処理: [1: 実Godotの短い計測結果を検査し、中間状態・実行件数・時間を変えた複製の拒否を照合します]
    #   引数: [self: 性能結果の意味を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_benchmark_rejects_failed_incomplete_or_fake_fast_results(self):
        path = fixture.godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_speed_state.py"
        spec = importlib.util.spec_from_file_location("speed_state_benchmark", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        arguments = argparse.Namespace(iterations=50, samples=3, warmup=10)
        checker = module.SpeedStateBenchmark(str(fixture.godot_fixture.GODOT), arguments)
        observed = self.run_probe(checker.configuration)
        self.assertTrue(checker.valid_result(observed), observed)
        # 最後の復元値だけでなく、途中の倍率/期間や全件数の破壊も失敗として扱います。
        for field, value in (("trace", []), ("operations_completed", 7), ("iterations", 1),
                             ("all_traces_match", False), ("microseconds", -1), ("microseconds", float("nan")),
                             ("microseconds", float("inf")), ("microseconds", True), ("microseconds", 3001)):
            broken = copy.deepcopy(observed)
            broken[field] = value
            self.assertFalse(checker.valid_result(broken), (field, value))
        broken = copy.deepcopy(observed)
        broken["trace"][2]["snapshot"]["speed_multiplier"] = 1.3
        self.assertFalse(checker.valid_result(broken))
        self.assertFalse(checker.valid_result({"ok": False, "microseconds": 0}))
