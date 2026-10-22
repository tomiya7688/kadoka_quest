"""参加者別速度のSession接続と初期化原子性を、実Godotと実Pythonで比較します。"""
# {
#   責務: [test_gdscript_session_speed: 速度集合・Session・Applicationの独立保持と行動順への接続を検証します]
#   フィールド: []
# }
from __future__ import annotations

import base64
import copy
import hashlib
import json
import subprocess
import importlib.util
import itertools
import unittest

import status_turn_order_fixture as reference
import test_gdscript_combatant as combatant
import test_gdscript_speed_state as speed
import test_gdscript_status_cure as fixture
import test_gdscript_status_session_round as rounds

ACTOR, ENEMY = rounds.ACTOR, rounds.ENEMY


# {
#   責務: [speed_case: 状態と速度を分離したSession初期化と正常ラウンド開始の要求を作ります]
#   処理: [1: 共用の同ID両陣営へ別倍率と重複出血を設定します]
#   引数: [changes: 開始区分・倍率・操作列の個別上書き（dict）]
#   戻り値: [result: 実セーブと独立した新規要求（dict）]
# }
def speed_case(**changes):
    # 初期値はケースごとに共用fixtureが複製し、別ケースや実セーブへ倍率を共有しません。
    return {**rounds.round_case(["bleeding", {"id": "bleeding"}]),
            "initial_speed_multipliers": {"allies": {"same": 2.0}, "enemies": {"same": 0.75}}, **changes}


# {
#   責務: [SessionSpeedTests: 実Godot観測と隔離保存ダミーを所有し、速度読取・拒否・順序・互換性を検証します]
#   フィールド: [
#     folder: 専用要求を置く一時領域（Path）
#     saved_files: 個体・AI・items・party・stateの不変を確認する保存ダミー（list）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for session speed probes")
class SessionSpeedTests(unittest.TestCase):
    setUp = fixture.StatusCureQuoteTests.setUp
    run_probe = speed.SpeedStateTests.run_probe

    # {
    #   責務: [observe: 速度接続の全ケースを実行し、結果数・原本・返却コピーの独立性を確認します]
    #   処理: [1: 共用起動で要求/保存ダミー不変を確認し、各操作の独立性を照合します]
    #   引数: [
    #     self: 一時要求領域と保存ダミーの所有者
    #     cases: 開始条件とstepsを持つ独立ケース列（list）
    #   ]
    #   戻り値: [result: ケースと同数の実観測列（list）]
    # }
    def observe(self, cases):
        actual = self.run_probe({"session_speed": True, "cases": cases})["results"]
        self.assertEqual(len(actual), len(cases))
        for case, observed in zip(cases, actual):
            self.assertEqual(len(observed["steps"]), len(case.get("steps", [])))
            self.assertTrue(observed["input_preserved"] and observed["source_independent"])
            self.assertTrue(all(step["independent"] and step["request_preserved"] for step in observed["steps"]))
        return actual

    # {
    #   責務: [test_owned_multipliers_match_python_and_do_not_compound_between_rounds: 所有倍率と最新状態からの順序を実Pythonへ照合し、補正の累積を防ぎます]
    #   処理: [1: 倍率/状態/明示順の組合せで三ラウンドを完了し、全計画・補正前資源・保持倍率を比較します]
    #   引数: [self: PythonとGodotの速度順序を比較するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_owned_multipliers_match_python_and_do_not_compound_between_rounds(self):
        cases = []
        for left, right, effects, order in itertools.product(
                (0, 0.75, 1, 1.2, 2), (0, 1, 1.5), ([], ["bleeding", {"id": "bleeding"}]),
                ([ACTOR, ENEMY], [ENEMY, ACTOR])):
            case = speed_case(initial_speed_multipliers={"allies": {"same": left}, "enemies": {"same": right}})
            case["initial_statuses"]["allies"]["same"] = effects
            case["steps"] = [{"operation": "begin", "order": order}]
            case["steps"] += rounds.complete_round(2) + [{"operation": "begin", "order": order}]
            case["steps"] += rounds.complete_round(2) + [{"operation": "begin", "order": order}]
            cases.append(case)
        for case, observed in zip(cases, self.observe(cases)):
            with self.subTest(multipliers=case["initial_speed_multipliers"], states=case["initial_statuses"]):
                request = reference.request(case["snapshots"]["allies"], case["snapshots"]["enemies"])
                request.update(statuses=case["initial_statuses"], speed_multipliers=case["initial_speed_multipliers"],
                               shuffle_order=case["steps"][0]["order"])
                expected = {"ok": True, "scope": "status_turn_order", **reference.python_result(request)}
                for index in (0, 7, 14):
                    self.assertEqual(observed["steps"][index]["result"]["plan"], expected)
                self.assertEqual(observed["state"]["numeric"]["teams"], case["snapshots"])
                for side in ("allies", "enemies"):
                    multiplier = case["initial_speed_multipliers"][side]["same"]
                    self.assertEqual(observed["state"]["speeds"]["teams"][side]["same"],
                        {"speed_multiplier": multiplier, "remaining_turns": 0, "baseline_multiplier": multiplier})

    # {
    #   責務: [test_invalid_initial_maps_are_atomic_retryable_and_never_coerced: 辞書不正・ID不一致・不正倍率は部分開始せず、正常入力で再試行できます]
    #   処理: [1: 集合/Sessionの不正初期値とエンジン値を拒否し、再試行成功と再初期化拒否を照合します]
    #   引数: [self: 初期化の検証境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_initial_maps_are_atomic_retryable_and_never_coerced(self):
        invalid = [False, 1, [], {}, {"allies": {}, "enemies": {}},
                   {"allies": {"same": 1}, "other": {"same": 1}},
                   {"allies": {"wrong": 1}, "enemies": {"same": 1}},
                   {"allies": {"same": 1}, "enemies": {"same": 1}, "extra": {}}]
        invalid += [{"allies": {"same": 1}, "enemies": {"same": value}}
                    for value in (None, True, "1", [], {}, -1, 2**53)]
        cases = []
        for mode in ("collection", "session"):
            good = speed_case(mode=mode, steps=[])
            for value in invalid:
                cases.append(speed_case(mode=mode, initial_speed_multipliers=value,
                    steps=[{"operation": "start", "input": good}, {"operation": "start", "input": good}]))
            for native in ("nan", "inf", "object"):
                cases.append(speed_case(mode=mode, special=native,
                    steps=[{"operation": "start", "input": good}, {"operation": "start", "input": good}]))
        for observed in self.observe(cases):
            self.assertFalse(observed["started"]["ok"])
            self.assertTrue(observed["steps"][0]["result"]["ok"])
            self.assertEqual(observed["steps"][1]["result"], {"ok": False, "reason": "already_initialized"})
            self.assertTrue(observed["steps"][1]["unchanged"])
        # 数値参加者/初期状態が不正な場合も速度だけを公開しません。
        cases = [speed_case(snapshots={"allies": False, "enemies": []}, steps=[]),
                 speed_case(initial_statuses={}, steps=[])]
        for observed in self.observe(cases):
            self.assertFalse(observed["started"]["ok"])
            self.assertEqual(observed["state"]["speeds"], {})
            self.assertEqual(observed["state"]["numeric"]["phase"], "not_started")

    # {
    #   責務: [test_read_keys_default_legacy_and_empty_rosters_preserve_contracts: 読取キー・倍率省略・従来開始・空陣営の形式を保持します]
    #   処理: [1: 全区分で不正/不在キーと未開始を拒否し、省略/nullの全員1と従来の未設定を照合します]
    #   引数: [self: 速度読取と既存開始互換性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_read_keys_default_legacy_and_empty_rosters_preserve_contracts(self):
        bad_keys = [None, False, [], {}, {"side": "allies"}, {**ACTOR, "extra": 1},
                    {"side": "other", "id": "same"}, {"side": "allies", "id": ""}]
        steps = [{"operation": "speed", "actor": value} for value in bad_keys + [rounds.normal.key("allies", "missing"), ACTOR, ENEMY]]
        for mode in ("collection", "session"):
            observed = self.observe([speed_case(mode=mode, steps=steps)])[0]
            for index in range(len(bad_keys)):
                self.assertEqual(observed["steps"][index]["result"]["reason"], "invalid_actor_key")
            self.assertEqual(observed["steps"][len(bad_keys)]["result"]["reason"], "actor_missing")
            self.assertEqual(observed["steps"][-2]["result"]["snapshot"]["speed_multiplier"], 2)
            self.assertEqual(observed["steps"][-1]["result"]["snapshot"]["speed_multiplier"], 0.75)
            self.assertTrue(all(step["unchanged"] for step in observed["steps"]))
            before = self.observe([speed_case(mode=mode, no_start=True, steps=[{"operation": "speed", "actor": ACTOR}])])[0]
            self.assertEqual(before["state"]["speeds"], {})
            self.assertEqual(before["steps"][0]["result"]["reason"], "not_initialized")
        omitted = speed_case(steps=[])
        del omitted["initial_speed_multipliers"]
        for observed in self.observe([omitted, speed_case(initial_speed_multipliers=None, steps=[])]):
            self.assertTrue(observed["started"]["ok"])
            self.assertEqual(observed["state"]["speeds"]["teams"]["allies"]["same"]["speed_multiplier"], 1)
        legacy = self.observe([speed_case(legacy=True, steps=[{"operation": "speed", "actor": ACTOR}])])[0]
        self.assertEqual(legacy["state"]["speeds"], {})
        self.assertEqual(legacy["steps"][0]["result"]["reason"], "speed_not_configured")
        # 空陣営でも明示辞書は全参加者と一致させ、停止は勝敗確定や速度解除に置き換えません。
        empty = speed_case(steps=[{"operation": "begin", "order": []}])
        empty.update(snapshots={"allies": [], "enemies": []}, initial_statuses={"allies": {}, "enemies": {}},
                     initial_speed_multipliers={"allies": {}, "enemies": {}})
        observed = self.observe([empty])[0]
        self.assertTrue(observed["steps"][0]["result"]["stop"])
        self.assertEqual(observed["state"]["speeds"], {"teams": {"allies": {}, "enemies": {}}, "scope": "battle_speed_only"})

    # {
    #   責務: [test_eight_owners_and_rejected_round_plans_keep_speed_and_reservations: 八体の速度は死亡/逃走で消えず、不正順・途中開始・精度超過で予約と資源を変更しません]
    #   処理: [1: 公開APIで離脱と予約を作り、全員読取・生存順・拒否時の全状態保持を照合します]
    #   引数: [self: 八体と行動段階の非変更境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_eight_owners_and_rejected_round_plans_keep_speed_and_reservations(self):
        case = rounds.roster.roster_case(["bleeding"], count=4)
        order = [rounds.normal.key(side, f"same_{index}") for side in ("allies", "enemies") for index in range(4)]
        case["initial_speed_multipliers"] = {side: {f"same_{index}": index + (1 if side == "allies" else 2)
            for index in range(4)} for side in ("allies", "enemies")}
        case["steps"] = [{"operation": "damage", "actor": order[0], "value": 999},
                         {"operation": "flee", "actor": order[-1]}, {"operation": "begin", "order": []},
                         {"operation": "begin", "order": order[1:-1]}, {"operation": "next"},
                         {"operation": "begin", "order": order[1:-1]}, {"operation": "claim"},
                         {"operation": "begin", "order": order[1:-1]}]
        observed = self.observe([case])[0]
        for index in (2, 5, 7):
            self.assertFalse(observed["steps"][index]["result"]["ok"])
            self.assertTrue(observed["steps"][index]["unchanged"])
        self.assertEqual(sum(map(len, observed["state"]["speeds"]["teams"].values())), 8)
        current = observed["state"]["numeric"]["teams"]
        request = reference.request(current["allies"], current["enemies"])
        request.update(statuses=case["initial_statuses"], speed_multipliers=case["initial_speed_multipliers"],
                       shuffle_order=order[1:-1])
        self.assertEqual(observed["steps"][3]["result"]["plan"]["order"], reference.python_result(request)["order"])
        overflow = speed_case(initial_speed_multipliers={"allies": {"same": 2**53 - 1}, "enemies": {"same": 1}})
        observed = self.observe([overflow])[0]
        self.assertTrue(observed["started"]["ok"])
        self.assertFalse(observed["steps"][0]["result"]["ok"])
        self.assertTrue(observed["steps"][0]["unchanged"])

    # {
    #   責務: [test_application_publishes_only_fully_planned_speed_owners: Applicationは初回速度順を含む全準備成功後だけSessionを公開します]
    #   処理: [1: 不正初期倍率/初回計画の失敗後に再試行し、公開行動で次ラウンドへ進めて所有倍率を確認します]
    #   引数: [self: 正規JSONの読取だけを使うApplication検証ケース]
    #   戻り値: [result: なし（None）。実セーブは使用しません]
    # }
    def test_application_publishes_only_fully_planned_speed_owners(self):
        good = speed_case(mode="application", project_root=str(fixture.godot_fixture.ROOT),
            records={side: [combatant.record("same", "slime", level=7)] for side in ("allies", "enemies")},
            order=[ACTOR, ENEMY], steps=[])
        steps = [{"operation": op} for _ in range(2) for op in ("next", "defend_action")]
        steps += [{"operation": "begin", "order": [ACTOR, ENEMY]}, {"operation": "speeds"}]
        cases = [{**good, "steps": steps}]
        for changes in ({"initial_speed_multipliers": {"allies": {}, "enemies": {}}},
                        {"initial_speed_multipliers": {"allies": {"same": 2**53 - 1}, "enemies": {"same": 1}}},
                        {"order": []}):
            cases.append({**copy.deepcopy(good), **changes, "steps": [{"operation": "start", "input": good}, *steps]})
        observed = self.observe(cases)
        self.assertEqual(observed[0]["started"]["session"]["order"], [ACTOR, ENEMY])
        for index, value in enumerate(observed):
            if index:
                self.assertFalse(value["started"]["ok"])
                self.assertTrue(value["steps"][0]["result"]["ok"])
            self.assertEqual(value["state"]["numeric"]["round"], 2)
            self.assertEqual(value["state"]["numeric"]["order"], [ACTOR, ENEMY])
            self.assertEqual(value["state"]["speeds"]["teams"]["allies"]["same"]["speed_multiplier"], 2)

    # {
    #   責務: [test_latest_statuses_use_owned_speed_only_at_next_round: 所有倍率が1以外でも治療は現在順を変えず、次回だけ最新状態を反映します]
    #   処理: [1: 取得済み行動票で本人の出血を治療し、次の二ラウンドの順序と倍率非変更を確認します]
    #   引数: [self: 最新状態と所有速度の合成を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_latest_statuses_use_owned_speed_only_at_next_round(self):
        # 速度倍率2を両陣営へ保持し、治療前19対20・治療後22対20で順序が変わる入力を使います。
        case = speed_case(initial_speed_multipliers={"allies": {"same": 2}, "enemies": {"same": 2}})
        case["steps"] += [*rounds.complete_round(1), {"operation": "next"}, {"operation": "claim"},
            {"operation": "apply_cure", "actor": ACTOR, "request": {"cure_chance": 1, "roll": 0}},
            {"operation": "finish"}, {"operation": "begin", "order": [ACTOR, ENEMY]},
            *rounds.complete_round(2), {"operation": "begin", "order": [ACTOR, ENEMY]}]
        # 重複出血を一件治療しても残存出血は有効なので、このケースの初期一覧は一件だけにします。
        case["initial_statuses"]["allies"]["same"] = ["bleeding"]
        observed = self.observe([case])[0]
        self.assertTrue(observed["steps"][6]["result"]["ok"])
        self.assertEqual(observed["steps"][6]["state"]["numeric"]["order"], [ENEMY, ACTOR])
        for index in (8, 15):
            self.assertEqual(observed["steps"][index]["result"]["plan"]["order"], [ACTOR, ENEMY])
        self.assertEqual(observed["state"]["speeds"], observed["steps"][0]["state"]["speeds"])
        # 集合の倍率専用投影も独立コピーで、整数精度上限の初期倍率を保持できます。
        boundary = speed_case(mode="collection", steps=[{"operation": "multipliers"}],
            initial_speed_multipliers={"allies": {"same": 2**53 - 1}, "enemies": {"same": 0}})
        actual = self.observe([boundary])[0]
        self.assertEqual(actual["steps"][0]["result"], boundary["initial_speed_multipliers"])
        self.assertTrue(actual["steps"][0]["unchanged"])

    # {
    #   責務: [test_speed_round_benchmark_rejects_forged_states_and_fast_failures: 速度付き性能検査は固定八体・正常進行・所有倍率・有限時間の全一致を要求します]
    #   処理: [1: 実Godotの小反復結果を独立期待値へ照合し、入力/速度/順序/時間の偽装を拒否します]
    #   引数: [self: 専用性能要求と保存ダミーの所有者]
    #   戻り値: [result: なし（None）]
    # }
    def test_speed_round_benchmark_rejects_forged_states_and_fast_failures(self):
        # 共用の性能fixtureを使い、専用結果の比較規則だけを今回の倍率付き区分で追加確認します。
        path = fixture.godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_battle_session.py"
        spec = importlib.util.spec_from_file_location("speed_session_performance", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        request = {"performance": True, "status_round": True, "speed_round": True,
                   "iterations": 20, "samples": 3, "warmup": 2}
        request_path = self.folder / "session-speed-performance.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        before = {file: hashlib.sha256(file.read_bytes()).digest() for file in [request_path, *self.saved_files]}
        process = subprocess.run([str(fixture.godot_fixture.GODOT), "--headless", "--path",
            str(fixture.godot_fixture.ROOT / "gdscript"), "--script", "res://tests/run_battle_session_probe.gd",
            "--", str(request_path)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertNotIn("SCRIPT ERROR", process.stderr)
        self.assertNotIn("ERROR:", process.stderr)
        self.assertEqual(before, {file: hashlib.sha256(file.read_bytes()).digest() for file in before})
        lines = [line for line in process.stdout.splitlines() if line.startswith("KADOKA_SESSION_RESULT=")]
        self.assertEqual(len(lines), 1, process.stdout)
        actual = json.loads(base64.b64decode(lines[0].split("=", 1)[1]))
        self.assertTrue(module.valid_status_round_result(actual, request), actual)
        for field, value in (("session", {}), ("input", {}), ("initial_speed_multipliers", {}),
                             ("speeds", {}), ("input_preserved", False), ("actors", True),
                             ("microseconds", float("nan")), ("microseconds", True), ("microseconds", 2001)):
            self.assertFalse(module.valid_status_round_result({**actual, field: value}, request), field)
