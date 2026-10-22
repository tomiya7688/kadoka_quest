"""最新保持状態によるラウンド開始と従来開始の互換性を実Godot/Pythonで確認します。"""
# {
#   責務: [test_gdscript_status_session_round: 状態補正順序のSession接続・再計算・途中固定・拒否時保持を検証します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import base64
import hashlib
import importlib.util
import itertools
import json
import subprocess
import unittest

import status_turn_order_fixture as reference
import test_gdscript_combatant as combatant
import test_gdscript_normal_attack_action as normal
import test_gdscript_roster_status_application as roster
import test_gdscript_status_cure as fixture
import test_gdscript_status_physical_preflight as preflight

ACTOR = normal.key("allies", "same")
ENEMY = normal.key("enemies", "same")


# {
#   責務: [round_case: 同じIDを持つ両陣営へ独立した初期資源・状態と一回のラウンド開始を用意します]
#   処理: [1: 共用fixtureの速度を11対10にし、指定した味方状態と開始条件を追加します]
#   引数: [
#     effects: 味方だけに与える状態一覧。Noneは空状態です
#     changes: 開始条件や操作一覧を上書きするケース固有の値
#   ]
#   戻り値: [result: 実セーブから独立した状態付きSession観測要求（dict）]
# }
def round_case(effects=None, **changes):
    # 味方速度11が出血で9になり敵速度10より遅くなる、順序の変化が明確な入力を使います。
    case = roster.roster_case()
    for side, speed in (("allies", 11), ("enemies", 10)):
        case["snapshots"][side][0]["stats"]["speed"] = speed
    case["initial_statuses"]["allies"]["same"] = copy.deepcopy(effects or [])
    return {**case, "steps": [{"operation": "begin", "order": [ACTOR, ENEMY]}], **changes}


# {
#   責務: [complete_round: 全参加者の提示・取得・完了を繰り返す、資源を変更しない操作列を作ります]
#   処理: [1: 指定参加数だけ三段階の操作を独立生成します]
#   引数: [count: 現在ラウンドで残っている参加者数（int）]
#   戻り値: [result: next/claim/finishの操作列（list）]
# }
def complete_round(count):
    # プローブからSessionの非公開段階を書き換えず、製品APIで実際にラウンドを完了します。
    return [{"operation": operation} for _ in range(count) for operation in ("next", "claim", "finish")]


# {
#   責務: [StatusSessionRoundTests: 隔離保存ダミーと実Godot観測を所有し、最新状態の順序と非変更境界を検証します]
#   フィールド: [
#     folder: 共用fixtureが作る専用要求領域（Path）
#     saved_files: byte不変を確認する五種類の保存ダミー（list）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for status session rounds")
class StatusSessionRoundTests(unittest.TestCase):
    setUp = fixture.StatusCureQuoteTests.setUp

    # {
    #   責務: [observe: 状態付きSessionの実Godot観測を取得し、全操作と原本・返却コピーの独立性を確認します]
    #   処理: [1: 共用起動で保存ダミー保持を検査し、結果数と全操作の非共有を照合します]
    #   引数: [
    #     self: 隔離保存ダミーの所有者
    #     cases: 独立した開始条件と操作一覧の配列（list）
    #   ]
    #   戻り値: [result: 全ケースの実観測（list）]
    # }
    def observe(self, cases):
        # 結果欠落によるzipの偽成功を防ぎ、編集した返却値が所有状態へ伝わらないことも確認します。
        actual = fixture.StatusCureQuoteTests.run_probe(self, {"session_status": True, "cases": cases})["results"]
        self.assertEqual(len(actual), len(cases))
        for case, result in zip(cases, actual):
            self.assertEqual(len(result["steps"]), len(case["steps"]))
            self.assertTrue(result["input_preserved"] and result["source_independent"])
            self.assertTrue(all(step["independent"] and step["request_preserved"] for step in result["steps"]))
        return actual

    # {
    #   責務: [test_first_round_matches_python_status_speed_and_stable_ties: 初回順序を実Pythonの速度と比較し、重複出血・未知状態・同速と下限を確認します]
    #   処理: [1: 状態六種・速度境界・明示順二種の組合せを比較し、数値資源と状態を保持するか確認します]
    #   引数: [self: 初回ラウンドの互換性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_first_round_matches_python_status_speed_and_stable_ties(self):
        # 同IDを両陣営で独立に扱い、重複出血を二重乗算しないことを実Pythonと照合します。
        cases = []
        for effects, speeds, order in itertools.product(
            ([], ["bleeding"], ["bleeding", {"id": "bleeding"}], ["Bleeding"], ["sleep", "poison"],
             [{"id": "mod", "metadata": {"deck": [None, True]}}]),
            ((11, 10), (10, 9), (0, 1), (1, 0)), ([ACTOR, ENEMY], [ENEMY, ACTOR])
        ):
            case = round_case(effects, steps=[{"operation": "begin", "order": order}])
            for side, speed in zip(("allies", "enemies"), speeds):
                case["snapshots"][side][0]["stats"]["speed"] = speed
            cases.append(case)
        for case, actual in zip(cases, self.observe(cases)):
            with self.subTest(case=case):
                request = reference.request(case["snapshots"]["allies"], case["snapshots"]["enemies"])
                request["statuses"] = case["initial_statuses"]
                request["shuffle_order"] = case["steps"][0]["order"]
                expected = reference.python_result(request)
                plan = actual["steps"][0]["result"]["plan"]
                self.assertEqual(plan, {"ok": True, "scope": "status_turn_order", **expected})
                self.assertEqual(actual["numeric"]["order"], expected["order"])
                self.assertEqual(actual["numeric"]["teams"], case["snapshots"])
                self.assertEqual(actual["statuses"]["teams"], case["initial_statuses"])

    # {
    #   責務: [test_application_and_cure_affect_only_the_next_round_without_compounding: 行動中の付与と治療は現在順を変えず、次ラウンドだけ最新状態から再計算します]
    #   処理: [1: 付与または治療後に実ラウンドを完了し、三ラウンドの順序と補正前速度を照合します]
    #   引数: [self: 最新状態とラウンド固定を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_application_and_cure_affect_only_the_next_round_without_compounding(self):
        # 状態更新は取得済みの行動票を通し、現在順序を直接書き換えず次回開始でだけ読み直します。
        cases = []
        for initial, operation, request in (
            ([], "apply_status", {"effect": {"id": "bleeding", "chance": 1}, "roll": 0}),
            (["bleeding"], "apply_cure", {"cure_chance": 1, "roll": 0})
        ):
            case = round_case(initial)
            case["steps"] += [*complete_round(1 if initial else 0), {"operation": "next"}, {"operation": "claim"},
                              {"operation": operation, "actor": ACTOR, "request": request},
                              {"operation": "finish"}, *complete_round(0 if initial else 1),
                              {"operation": "begin", "order": [ACTOR, ENEMY]},
                              *complete_round(2), {"operation": "begin", "order": [ACTOR, ENEMY]}]
            cases.append(case)
        for case, actual in zip(cases, self.observe(cases)):
            before = [ENEMY, ACTOR] if case["initial_statuses"]["allies"]["same"] else [ACTOR, ENEMY]
            after = list(reversed(before))
            updated = next(index for index, step in enumerate(case["steps"]) if step["operation"] in ("apply_status", "apply_cure"))
            self.assertTrue(actual["steps"][updated]["result"]["ok"], actual["steps"][updated]["result"])
            self.assertEqual(actual["steps"][updated]["numeric"]["order"], before)
            self.assertEqual(actual["steps"][8]["numeric"]["order"], after)
            self.assertEqual(actual["numeric"]["order"], after)
            self.assertEqual(actual["numeric"]["round"], 3)
            self.assertEqual(actual["numeric"]["teams"], case["snapshots"])

    # {
    #   責務: [test_invalid_order_and_active_phase_preserve_all_state_and_allow_retry: 不正明示順と進行中の開始は資源・状態・guard・予約を変更せず拒否します]
    #   処理: [1: 開始前/次回開始の不正順と未開始/提示中/取得済み/停止後の拒否を照合します]
    #   引数: [self: 開始の原子性と段階境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_order_and_active_phase_preserve_all_state_and_allow_retry(self):
        # 正常開始前の拒否と、予約を持つ最中の拒否を分離して検査します。
        invalid = [None, False, 0, {}, [], [ACTOR], [ACTOR, ACTOR], [ACTOR, ENEMY, ENEMY],
                   [ACTOR, {**ENEMY, "extra": 1}], [ACTOR, normal.key("enemies", "missing")]]
        cases = [round_case(["bleeding"], steps=[{"operation": "begin", "order": order},
                 {"operation": "begin", "order": [ACTOR, ENEMY]}]) for order in invalid]
        for actual in self.observe(cases):
            self.assertFalse(actual["steps"][0]["result"]["ok"])
            self.assertEqual(actual["steps"][0]["numeric"], actual["started"]["session"])
            self.assertTrue(actual["steps"][1]["result"]["ok"])
            self.assertEqual(actual["numeric"]["round"], 1)
        case = round_case(["bleeding"])
        case["steps"] += [{"operation": "next"}, {"operation": "begin", "order": []},
                          {"operation": "claim"}, {"operation": "defend", "value": 0.5},
                          {"operation": "begin", "order": [ACTOR, ENEMY]}, {"operation": "finish"},
                          *complete_round(1), {"operation": "begin", "order": []},
                          {"operation": "begin", "order": [ACTOR, ENEMY]}]
        actual = self.observe([case])[0]
        for index in (2, 5, 10):
            self.assertFalse(actual["steps"][index]["result"]["ok"])
            for field in ("numeric", "statuses", "guards"):
                self.assertEqual(actual["steps"][index][field], actual["steps"][index - 1][field])
        self.assertEqual(actual["numeric"]["round"], 2)
        self.assertEqual(self.observe([round_case(no_start=True)])[0]["steps"][0]["result"],
                         {"ok": False, "reason": "not_initialized"})

    # {
    #   責務: [test_eight_actors_dead_fled_empty_and_stopped_boundaries: 八体の全状態を保持し、死亡/逃走を順から除外し、空陣営と停止後拒否を確認します]
    #   処理: [1: 八体から二体を離脱させ、全員の速度辞書と生存者順序・停止を照合します]
    #   引数: [self: 最大参加者と終端境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_eight_actors_dead_fled_empty_and_stopped_boundaries(self):
        # 非公開資源の改変ではなく公開APIで死亡/逃走させ、状態/速度の全員対応と生存者順を区別します。
        case = roster.roster_case(["bleeding"], count=4)
        order = [normal.key(side, f"same_{index}") for side in ("allies", "enemies") for index in range(4)]
        case["steps"] = [{"operation": "damage", "actor": order[0], "value": 999},
                         {"operation": "flee", "actor": order[-1]}, {"operation": "begin", "order": order[1:-1]}]
        actual = self.observe([case])[0]
        plan = actual["steps"][-1]["result"]["plan"]
        self.assertEqual(plan["order"], order[1:-1])
        self.assertEqual(sum(map(len, plan["speeds"].values())), 8)
        self.assertEqual(actual["statuses"]["teams"], case["initial_statuses"])
        for side in ("allies", "enemies", "both"):
            empty = roster.roster_case()
            for removed in (("allies", "enemies") if side == "both" else (side,)):
                empty["snapshots"][removed] = []
                empty["initial_statuses"][removed] = {}
            keys = [normal.key(team, "same") for team in empty["snapshots"] if empty["snapshots"][team]]
            empty["steps"] = [{"operation": "begin", "order": keys}, {"operation": "begin", "order": keys}]
            result = self.observe([empty])[0]
            self.assertTrue(result["steps"][0]["result"]["stop"])
            self.assertEqual(result["numeric"]["phase"], "stopped")
            self.assertEqual(result["steps"][1]["result"], {"ok": False, "reason": "round_not_available"})

    # {
    #   責務: [test_legacy_start_keeps_base_speed_zero_and_statusless_shape: 従来開始は状態補正を使わず、最低速度1と元の順序結果形式を維持します]
    #   処理: [1: 出血の有無で従来/状態付き開始を比較し、速度0の下限・状態未設定と数値形式を照合します]
    #   引数: [self: 従来開始の互換性を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_legacy_start_keeps_base_speed_zero_and_statusless_shape(self):
        # 従来開始では出血による減速を使わず、基礎順序と状態未設定を維持することを確認します。
        case = round_case(["bleeding"], legacy=True)
        legacy, adjusted = self.observe([case, {**case, "legacy": False}])
        self.assertEqual(legacy["numeric"]["order"], [ACTOR, ENEMY])
        self.assertEqual(adjusted["numeric"]["order"], [ENEMY, ACTOR])
        self.assertEqual(legacy["statuses"], {})
        self.assertNotIn("speeds", legacy["steps"][0]["result"]["plan"])
        self.assertEqual(set(legacy["numeric"]), {"phase", "round", "cursor", "order", "pending", "teams", "scope"})
        # 速度0も元から最低1として扱い、同速の明示順を維持することを別入力で確認します。
        case["snapshots"]["allies"][0]["stats"]["speed"] = 0
        case["snapshots"]["enemies"][0]["stats"]["speed"] = 1
        self.assertEqual(self.observe([case])[0]["numeric"]["order"], [ACTOR, ENEMY])

    # {
    #   責務: [test_application_starts_first_and_later_rounds_with_owned_statuses_atomically: Applicationは初回/次回とも状態補正順を使い、初期状態不正時は未開始を保持します]
    #   処理: [1: 正規個体の再構築から専用開始を実行し、失敗後の再試行と従来開始の順序も比較します]
    #   引数: [self: 隔離要求と保存ダミーを所有するテストケース]
    #   戻り値: [result: なし（None）。正規dataと実セーブを変更しません]
    # }
    def test_application_starts_first_and_later_rounds_with_owned_statuses_atomically(self):
        # Applicationは正規JSONを読み取るだけとし、所有個体ではなく比較用レコードから開始します。
        case = preflight.preflight_case(joined=True, project_root=str(fixture.godot_fixture.ROOT),
            records={side: [combatant.record("same", "slime", level=7)] for side in ("allies", "enemies")},
            initial_statuses={"allies": {"same": ["bleeding"]}, "enemies": {"same": []}},
            steps=[{"operation": operation} for _ in range(2) for operation in ("next", "defend_action")]
                  + [{"operation": "begin", "order": [ACTOR, ENEMY]}])
        invalid = {**copy.deepcopy(case), "initial_statuses": {"allies": {}, "enemies": {}},
                   "steps": [{"operation": "start", "input": case}]}
        results = fixture.StatusCureQuoteTests.run_probe(self, {"status_physical_preflight": True,
                    "cases": [case, invalid, {**case, "legacy": True}]})["results"]
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["started"]["session"]["order"], [ENEMY, ACTOR])
        self.assertEqual(results[0]["numeric"]["order"], [ENEMY, ACTOR])
        self.assertEqual(results[0]["numeric"]["round"], 2)
        self.assertFalse(results[1]["started"]["ok"])
        self.assertTrue(results[1]["steps"][0]["result"]["ok"])
        self.assertEqual(results[1]["numeric"]["order"], [ENEMY, ACTOR])
        self.assertEqual(results[2]["numeric"]["order"], [ACTOR, ENEMY])
        self.assertTrue(all(result["input_preserved"] for result in results))
        self.assertTrue(all(step["independent"] and step["request_preserved"] for result in results for step in result["steps"]))

    # {
    #   責務: [test_status_round_performance_guard_rejects_fast_failure_and_forged_results: 性能ガードは実Godotの八体正常観測だけを通し、欠落・順序/状態の偽装・不正時間を拒否します]
    #   処理: [1: 少数反復の正常結果を取得し、入力・実段階・状態・時間を一つずつ改変して拒否を確認します]
    #   引数: [self: 専用要求と保存ダミーを所有するテストケース]
    #   戻り値: [result: なし（None）。実セーブと正規データは変更しません]
    # }
    def test_status_round_performance_guard_rejects_fast_failure_and_forged_results(self):
        # 既存Session性能プローブを使い、機械的な結果自己一致ではなく独立期待値への照合を確認します。
        path = fixture.godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_battle_session.py"
        spec = importlib.util.spec_from_file_location("status_session_performance", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        request = {"performance": True, "status_round": True, "iterations": 20, "samples": 3, "warmup": 2}
        request_path = self.folder / "performance.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        before = {file: hashlib.sha256(file.read_bytes()).digest() for file in [request_path, *self.saved_files]}
        process = subprocess.run([str(fixture.godot_fixture.GODOT), "--headless", "--path",
            str(fixture.godot_fixture.ROOT / "gdscript"), "--script", "res://tests/run_battle_session_probe.gd", "--", str(request_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertNotIn("SCRIPT ERROR", process.stderr)
        self.assertNotIn("ERROR:", process.stderr)
        self.assertEqual(before, {file: hashlib.sha256(file.read_bytes()).digest() for file in before})
        lines = [line for line in process.stdout.splitlines() if line.startswith("KADOKA_SESSION_RESULT=")]
        self.assertEqual(len(lines), 1, process.stdout)
        result = json.loads(base64.b64decode(lines[0].split("=", 1)[1]))
        self.assertTrue(module.valid_status_round_result(result, request), result)
        # 高速な拒否、偽の最終順、状態未保持、計測条件のすり替えを一つずつ拒否します。
        for field, value in (("session", {}), ("input", {}), ("statuses", {}), ("initial_statuses", {}),
                             ("actors", 0), ("input_preserved", False), ("iterations", True), ("samples", 1),
                             ("microseconds", True), ("microseconds", -1), ("microseconds", 2001),
                             ("microseconds", float("nan")), ("microseconds", float("inf"))):
            self.assertFalse(module.valid_status_round_result({**result, field: value}, request), field)
        for field, value in (("order", []), ("cursor", 0), ("round", 0), ("phase", "stopped"), ("pending", {})):
            changed = copy.deepcopy(result)
            changed["session"][field] = value
            self.assertFalse(module.valid_status_round_result(changed, request), field)
        self.assertFalse(module.valid_status_round_result({}, request))
        # Pythonでは等しい数値1と真偽値Trueも、固定JSON入力の型が異なれば成功にしません。
        changed = copy.deepcopy(result)
        changed["input"]["allies"][0]["stats"]["speed"] = True
        changed["session"]["teams"]["allies"][0]["stats"]["speed"] = True
        self.assertFalse(module.valid_status_round_result(changed, request))
