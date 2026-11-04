"""明示状態付きSession開始・独立読取・拒否/保持を実Godotで検証します。実セーブは使いません。"""
# {
#   責務: [test_gdscript_session_status: 状態付き開始を数値/予約契約から分離し、原本保持と拒否後再試行を検証します]
#   フィールド: []
# }
from __future__ import annotations
import argparse
import copy
import importlib.util
import math
import unittest

import test_gdscript_cure_heal_context as context
import test_gdscript_normal_attack_action as normal
import test_gdscript_status_cure as fixture


# {
#   責務: [session_case: 同IDの両陣営に独立した数値開始と明示初期状態を用意します]
#   処理: [1: 共用準備fixtureから六キーsnapshotとside/id別状態を取り出します]
#   引数: [changes: 各専用ケースの開始/操作条件を上書きする値]
#   戻り値: [result: 実保存とは独立したSession観測要求（dict）]
# }
def session_case(**changes):
    prepared = context.context_case()
    return {"snapshots": {side: [entry["snapshot"] for entry in team] for side, team in prepared["teams"].items()},
            "initial_statuses": prepared["initial_statuses"], "steps": [], **changes}


# {
#   責務: [SessionStatusBoundaryTests: 状態保持の純粋な層境界と従来数値形式・専用/従来開始の分離を確認します]
#   フィールド: []
# }
class SessionStatusBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_status_storage_stays_pure_and_application_keeps_legacy_start: 状態所有にI/O/乱数/HPMP更新を持ち込まず、Applicationの従来開始を維持するか確認します]
    #   処理: [1: 状態保持の禁止依存と、Applicationの明示専用入口/従来区分・数値への状態キー未追加を静的確認します]
    #   引数: [self: 状態保持の境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_status_storage_stays_pure_and_application_keeps_legacy_start(self):
        root = fixture.godot_fixture.ROOT / "gdscript"
        for name in ("battle_status_state", "initial_status_map"):
            source = (root / f"engine/{name}.gd").read_text(encoding="utf-8")
            for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                              "randf(", "RandomNumberGenerator", ".pay_mp(", ".heal("):
                self.assertNotIn(forbidden, source)
        application = (root / "application/battle_session_application.gd").read_text(encoding="utf-8")
        self.assertIn("func start_with_statuses(", application)
        self.assertIn("_start(allies, enemies, shuffle_order, null, false, null)", application)
        self.assertNotIn("status_effects", (root / "engine/combatant_state.gd").read_text(encoding="utf-8"))


# {
#   責務: [SessionStatusTests: 共用の要求/保存ダミー領域と実Godotの状態付きSession観測を所有します]
#   フィールド: [
#     folder: 専用要求領域（Path）
#     saved_files: byte保持対象の保存ダミー列（list[Path]）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real session-status probes")
class SessionStatusTests(unittest.TestCase):
    # {
    #   責務: [setUp: 利用者セーブと分離した要求領域と五種類の保存ダミーを用意します]
    #   処理: [1: 共用治療fixtureへ一時領域の作成を委譲します]
    #   引数: [self: 専用要求と保存ダミーの所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        fixture.StatusCureQuoteTests.setUp(self)

    # {
    #   責務: [run_probe: 状態付きSession区分で実Godotを呼び、診断と要求/保存ダミーのbyte保持を確認します]
    #   処理: [1: コピー要求にsession_status=trueを付け、共用起動/検証へ委譲します]
    #   引数: [
    #     self: 専用領域の所有者
    #     payload: ケース一覧または計測要求（dict）
    #   ]
    #   戻り値: [result: 実Godotから復号した診断なしの観測結果（dict）]
    # }
    def run_probe(self, payload):
        return fixture.StatusCureQuoteTests.run_probe(self, {**copy.deepcopy(payload), "session_status": True})

    # {
    #   責務: [test_read_copies_side_identity_mod_metadata_and_empty_teams: 同IDを陣営別に保持し、ネスト/順序/重複・空状態を変更せず返すことを確認します]
    #   処理: [1: 個別/全体読取を編集した後も所有状態と入力が保持され、数値六キーが変わらないか照合します]
    #   引数: [self: 読取独立性を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_read_copies_side_identity_mod_metadata_and_empty_teams(self):
        cases = [session_case(steps=[{"operation": "status", "actor": normal.key(side, "same")}
                                    for side in ("allies", "enemies")] + [{"operation": "statuses"}]),
                 session_case(snapshots={"allies": [], "enemies": []}, initial_statuses={"allies": {}, "enemies": {}})]
        cases[0]["initial_statuses"]["allies"]["same"] += ["sleep", {"id": "mod_unknown", "metadata": {"deck": [None, True]}}]
        for request, actual in zip(cases, self.run_probe({"cases": cases})["results"]):
            self.assertTrue(actual["started"]["ok"])
            self.assertEqual(actual["statuses"], {"teams": request["initial_statuses"], "scope": "battle_status_only"})
            self.assertEqual(actual["numeric"]["teams"], request["snapshots"])
            self.assertEqual(set(actual["numeric"]), {"phase", "round", "cursor", "order", "pending", "teams", "scope"})
            self.assertTrue(actual["source_independent"])
            self.assertTrue(actual["input_preserved"])
            if actual["steps"]:
                for side, step in zip(("allies", "enemies"), actual["steps"][:2]):
                    self.assertEqual(step["result"], {"ok": True, "snapshot": {
                        "status_effects": request["initial_statuses"][side]["same"]}})
            for step in actual["steps"]:
                self.assertTrue(step["independent"])
            for side in request["snapshots"].values():
                for member in side:
                    self.assertEqual(set(member), {"identity", "stats", "hp", "mp", "fled", "alive"})
        self.assertEqual(self.run_probe({"cases": [cases[0]]})["results"][0]["statuses"],
                         {"teams": cases[0]["initial_statuses"], "scope": "battle_status_only"})

    # {
    #   責務: [test_unstarted_legacy_and_invalid_keys: 未開始・従来開始の状態未設定と不正side/idを理由付きで拒否することを確認します]
    #   処理: [1: 状態未設定の空読取と個別読取拒否、専用開始後の不正キーを照合します]
    #   引数: [self: 状態読取の前提条件を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_unstarted_legacy_and_invalid_keys(self):
        steps = [{"operation": "statuses"}, {"operation": "status", "actor": normal.key("allies", "same")}]
        cases = [session_case(no_start=True, steps=steps), session_case(legacy=True, steps=steps),
                 session_case(steps=[{"operation": "status", "actor": value} for value in
                              (None, False, 0, [], {}, {"side": "other", "id": "same"},
                               {"side": "allies", "id": ""}, {"side": "allies", "id": "same", "extra": 1},
                               normal.key("allies", "missing"))])]
        actual = self.run_probe({"cases": cases})["results"]
        for index, reason in enumerate(("not_initialized", "status_not_configured")):
            self.assertEqual(actual[index]["statuses"], {})
            self.assertEqual(actual[index]["steps"][1]["result"], {"ok": False, "reason": reason})
        self.assertTrue(all(not step["result"]["ok"] for step in actual[2]["steps"]))

    # {
    #   責務: [test_atomic_failure_retry_and_reinitialization_rejection: 不正初期状態を部分保持せず、正常再試行と開始後上書き拒否を確認します]
    #   処理: [1: 型・陣営/個体集合・状態内容・非JSON値・数値資源の不正を渡し、失敗後の未開始と正常再開始を照合します]
    #   引数: [self: 全成功時だけの開始を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_atomic_failure_retry_and_reinitialization_rejection(self):
        valid = session_case()
        invalid = [session_case(initial_statuses=value) for value in
                   (None, False, 0, [], {}, {"allies": {}, "enemies": {}},
                    {**valid["initial_statuses"], "extra": {}},
                    {"allies": {"same": [], "extra": []}, "enemies": {"same": []}},
                    {"allies": {"wrong": []}, "enemies": {"same": []}},
                    {"allies": {"same": False}, "enemies": {"same": []}},
                    {"allies": {"same": 0}, "enemies": {"same": []}},
                    {"allies": {"same": {}}, "enemies": {"same": []}},
                    {"allies": {"same": []}, "enemies": {"same": None}})]
        invalid += [session_case(special=value) for value in ("nan", "inf", "object", "cycle")]
        for field in ("hp", "mp", "fled", "status_effects"):
            request = session_case()
            request["snapshots"]["allies"][0][field] = True if field == "fled" else (0 if field != "status_effects" else [])
            invalid.append(request)
        for extra in ("duplicate", "over_limit"):
            request = session_case()
            request["snapshots"]["allies"] += ([copy.deepcopy(request["snapshots"]["allies"][0])] if extra == "duplicate"
                                               else [normal.member(str(index)) for index in range(4)])
            invalid.append(request)
        steps = [{"operation": "status", "actor": normal.key("allies", "same")},
                 {"operation": "start", "input": valid}, {"operation": "start", "input": valid},
                 {"operation": "start", "input": valid, "legacy": True}]
        for request in invalid:
            request["steps"] = steps
        for actual in self.run_probe({"cases": invalid})["results"]:
            self.assertFalse(actual["started"]["ok"])
            self.assertEqual(actual["steps"][0]["numeric"]["phase"], "not_started")
            self.assertEqual(actual["steps"][0]["numeric"]["teams"], {"allies": [], "enemies": []})
            self.assertEqual(actual["steps"][0]["statuses"], {})
            self.assertTrue(actual["steps"][1]["result"]["ok"])
            for step in actual["steps"][2:]:
                self.assertEqual(step["result"], {"ok": False, "reason": "already_initialized"})
            self.assertEqual(actual["statuses"]["teams"], valid["initial_statuses"])
            self.assertTrue(actual["source_independent"])
            self.assertTrue(actual["input_preserved"])

    # {
    #   責務: [test_round_guards_death_and_flee_keep_initial_statuses: 状態を物理防御倍率・ラウンド/終端・死亡/逃走で暗黙解除しないことを確認します]
    #   処理: [1: 予約取得/完了を二ラウンド繰り返し、物理防御・資源変化と状態保持を独立に照合します]
    #   引数: [self: 状態保持期間を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_round_guards_death_and_flee_keep_initial_statuses(self):
        order = [normal.key(side, "same") for side in ("allies", "enemies")]
        steps = []
        for _ in range(2):
            steps.append({"operation": "begin", "order": order})
            for _ in range(2):
                steps += [{"operation": "next"}, {"operation": "claim"},
                          {"operation": "defend", "value": 0.5}, {"operation": "finish"}]
        cases = [session_case(steps=steps + [{"operation": operation, "actor": order[1], "value": 999},
                                           {"operation": "begin", "order": [order[0]]}]) for operation in ("damage", "flee")]
        for request, actual in zip(cases, self.run_probe({"cases": cases})["results"]):
            self.assertEqual(actual["numeric"]["phase"], "stopped")
            self.assertTrue(all(step["statuses"]["teams"] == request["initial_statuses"] for step in actual["steps"]))
            self.assertTrue(any(step["guards"]["teams"]["allies"]["same"] == 0.5 for step in actual["steps"]))

    # {
    #   責務: [test_prepared_data_and_ordinary_heal_do_not_cure_statuses: 純粋準備のコピーを専用開始へ渡し、通常回復だけでは状態を解除しないことを確認します]
    #   処理: [1: 準備→開始→通常回復定義準備→損傷→回復行動を実行し、HP変化と初期状態保持を照合します]
    #   引数: [self: 準備との接続と通常回復互換性を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_prepared_data_and_ordinary_heal_do_not_cure_statuses(self):
        actor = normal.key("allies", "same")
        prepared = context.context_case()
        for side in prepared["teams"].values():
            side[0]["snapshot"]["stats"]["mp"] = 100
            side[0]["snapshot"]["mp"] = 100
        request = session_case(preparation=prepared, steps=[{"operation": "heal_start"},
                              {"operation": "damage", "actor": actor, "value": 20},
                              {"operation": "begin", "order": [actor, normal.key("enemies", "same")]},
                              {"operation": "next"}, {"operation": "heal_action", "actor": actor, "skill_id": "small_heal"}])
        actual = self.run_probe({"cases": [request]})["results"][0]
        self.assertTrue(actual["prepared"]["ok"])
        self.assertTrue(actual["steps"][-1]["result"]["ok"], actual)
        self.assertGreater(actual["numeric"]["teams"]["allies"][0]["hp"], 10)
        self.assertLess(actual["numeric"]["teams"]["allies"][0]["mp"], 100)
        self.assertEqual(actual["statuses"]["teams"], prepared["initial_statuses"])

    # {
    #   責務: [test_performance_validator_rejects_fast_failed_or_incomplete_results: 計測の正常結果条件を短い実測と欠落/改変結果で確認します]
    #   処理: [1: 二十反復の実結果を検査し、開始失敗・空状態・原本破壊・超過/負時間を拒否します]
    #   引数: [self: 性能ガードの結果照合を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_performance_validator_rejects_fast_failed_or_incomplete_results(self):
        path = fixture.godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_status_cure.py"
        spec = importlib.util.spec_from_file_location("session_status_performance", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        validator = module.StatusCureBenchmark("unused", argparse.Namespace(iterations=20, samples=3, warmup=2, session_status=True))
        result = self.run_probe({"performance": True, "iterations": 20, "samples": 3, "warmup": 2})
        # 少数回の実測は機械の負荷で揺れるため、時間は有限の非負値だけを確かめ、3000us上限は標準の性能CLIで判定します。
        self.assertTrue(math.isfinite(result["microseconds"]) and result["microseconds"] >= 0, result)
        result = {**result, "microseconds": 1000}
        self.assertTrue(validator._valid_session_result(result), result)
        for field, value in (("started", {"ok": False}), ("single", {}), ("statuses", {}),
                             ("actors", 0), ("numeric", {}), ("original_statuses", {}),
                             ("input_preserved", False), ("microseconds", -1), ("microseconds", 3001)):
            self.assertFalse(validator._valid_session_result({**result, field: value}), field)
