"""付与付き物理の専用開始と非消費検査を実Godotで確認します。実セーブ/正規JSONは保持します。"""
# {
#   責務: [test_gdscript_status_physical_preflight: 最新予約/資源/状態・開始一致・専用入口/原本独立性の検証を所有します]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import shutil
import sys
import unittest
from unittest import mock

import test_gdscript_combatant as combatant
import test_gdscript_normal_attack_action as normal
import test_gdscript_status_cure as fixture
import test_gdscript_status_physical_context as context

ACTOR = normal.key("allies", "same")
TARGET = normal.key("enemies", "same")


# {
#   責務: [preflight_case: 独立した満資源/初期状態とMOD定義へ、現在予約を使う非消費検査を追加します]
#   処理: [1: 既存準備fixtureの両陣営MPを明示し、固定順と検査手順を作ります]
#   引数: [changes: 個別ケースの開始入力/操作列を上書きする値]
#   戻り値: [result: 実Godot観測用の独立ケース（dict）]
# }
def preflight_case(**changes):
    # 数値正本/AIを再利用せず、前単位と同じ独立MOD入力で非消費検査を準備します。
    case = context.context_case()
    for side in ("allies", "enemies"):
        case["teams"][side][0]["snapshot"]["mp"] = 50
        case["teams"][side][0]["snapshot"]["stats"]["mp"] = 50
    return {**case, "order": [ACTOR, TARGET], "steps": [
        {"operation": "next"}, {"operation": "inspect", "target": TARGET}], **changes}


# {
#   責務: [StatusPhysicalPreflightBoundaryTests: 非消費検査と実行/IO/画面・数値計算の責務境界を確認します]
#   フィールド: []
# }
class StatusPhysicalPreflightBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_only_shared_selection_and_read_only_session_calls: 検査が既存選択/予約/状態/MP検査を使い、実更新や予測計算を持たないことを確認します]
    #   処理: [1: 非消費検査の依存・禁止呼出を照合し、Applicationの専用設定/委譲を確認します]
    #   引数: [self: 責務境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_only_shared_selection_and_read_only_session_calls(self):
        # 非消費検査へ実行/保存の依存を入れず、既存の予約・選択・資源検査を共用します。
        root = fixture.godot_fixture.ROOT / "gdscript"
        source = (root / "engine/status_physical_skill_preflight.gd").read_text(encoding="utf-8")
        for shared in ("Context.prepare(", "Context.select(", ".inspect_ticket(", ".mp_cost(", ".status(", ".guard("):
            self.assertIn(shared, source)
        for forbidden in (".claim(", ".finish(", ".pay_mp(", ".take_damage(", ".apply_status", "quote_damage",
                          "FileAccess", "DirAccess", "RandomNumberGenerator", "randf(", "res://application/", "res://ui/"):
            self.assertNotIn(forbidden, source)
        application = (root / "application/battle_session_application.gd").read_text(encoding="utf-8")
        self.assertIn("_status_physical.inspect(request)", application)
        self.assertIn("_status_physical.resolve(request)", application)


# {
#   責務: [StatusPhysicalPreflightTests: 専用要求・保存ダミー・正規JSON保持と実Godotの非消費検査を所有します]
#   フィールド: [
#     folder: 共用fixtureの専用要求/保存ダミー領域（Path）
#     saved_files: byte保持を確認する五種類の保存ダミー（list[Path]）
#     content: 読取専用の正規dataを持つプロジェクトルート（Path）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for status physical preflight")
class StatusPhysicalPreflightTests(unittest.TestCase):
    # {
    #   責務: [setUp: 共用fixtureの専用保存ダミーと正規JSONハッシュ確認を設定します]
    #   処理: [1: 前単位の隔離準備と正規JSON保持検査へ委譲します]
    #   引数: [self: 専用領域と保持確認の所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        # 共用fixtureが隔離保存先と正規JSONの終了時ハッシュ検査を所有します。
        context.StatusPhysicalContextTests.setUp(self)

    # {
    #   責務: [check_canonical: 正規JSONの開始時ハッシュと終了時ハッシュを共用検査で照合します]
    #   処理: [1: 読取専用JSONのbyte保持を前単位の確認へ委譲します]
    #   引数: [
    #     self: 正規JSONの保持を確認するテストケース
    #     hashes: 開始時のパス別ハッシュ（dict）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def check_canonical(self, hashes):
        # テストのApplication用MOD編集が正規dataへ漏れていないことを確認します。
        context.StatusPhysicalContextTests.check_canonical(self, hashes)

    # {
    #   責務: [observe: 専用区分で実Godotを起動し、要求/保存ダミー保持と全結果の返却独立性を確認します]
    #   処理: [1: 共用起動へ専用区分を渡し、各ケースの原本保持と返却編集後の正本を照合します]
    #   引数: [
    #     self: 専用要求と保存ダミーの所有者
    #     payload: ケース配列または性能の反復条件（dict）
    #   ]
    #   戻り値: [result: 実Godotの診断なし観測（dict）]
    # }
    def observe(self, payload):
        # 実Godotの診断/要求/保存保持は共用し、返却編集後の所有正本も全操作で確認します。
        result = fixture.StatusCureQuoteTests.run_probe(self, {**copy.deepcopy(payload), "status_physical_preflight": True})
        for case in result.get("results", []):
            self.assertTrue(case["input_preserved"])
            self.assertTrue(all(step["independent"] for step in case["steps"]))
        return result

    # {
    #   責務: [test_success_is_repeatable_non_consuming_and_source_independent: 同じofferedを繰り返し検査し、初期入力/返却編集から内部contextを保護します]
    #   処理: [1: 状態/耐性/装備と数値六キー・Session七キーを照合し、検査前後の完全一致を確認します]
    #   引数: [self: 非消費検査の正常系を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_success_is_repeatable_non_consuming_and_source_independent(self):
        # 入力/返却の装備・耐性・状態ネストを編集しても、内部contextの次の選択は保持します。
        case = preflight_case()
        case["teams"]["allies"][0]["equipment"] = {"allowed_species_ids": ["slime"], "fixed_bonus_damage": 3,
            "skill_modifiers": {"mod_status_hit": {"power_multiplier": 2}}}
        case["teams"]["enemies"][0]["status_resistances"] = {"bleeding": "immune", "custom": "future"}
        case["initial_statuses"]["enemies"]["same"] = [{"id": "bleeding", "metadata": {"deck": [1, True]}}]
        case["steps"] += [{"operation": "input_edit"}, {"operation": "inspect", "target": TARGET}]
        actual = self.observe({"cases": [case]})["results"][0]
        # 同じofferedを二回読んでも資源/状態/予約が完全一致し、実行結果を返さないことを確認します。
        first, repeated = actual["steps"][1], actual["steps"][3]
        self.assertEqual(first["result"], repeated["result"])
        checked = first["result"]
        self.assertTrue(first["unchanged"])
        self.assertTrue(repeated["unchanged"])
        self.assertEqual(checked["scope"], "status_physical_preflight_only")
        self.assertTrue(checked["eligibility"]["can_act"])
        self.assertEqual(checked["stats_scope"], "before_status_modifiers")
        self.assertEqual(checked["equipment"], {"power_multiplier": 2, "fixed_bonus_damage": 3})
        self.assertEqual(checked["target_status_resistances"], case["teams"]["enemies"][0]["status_resistances"])
        self.assertEqual(checked["target_status"]["status_effects"], case["initial_statuses"]["enemies"]["same"])
        self.assertEqual(checked["actor_status"]["status_effects"], case["initial_statuses"]["allies"]["same"])
        self.assertEqual(checked["target_guard"], 1)
        self.assertEqual(set(checked["actor_resources"]), {"identity", "stats", "hp", "mp", "fled", "alive"})
        self.assertEqual(set(actual["numeric"]), {"phase", "round", "cursor", "order", "pending", "teams", "scope"})
        self.assertEqual(actual["numeric"]["pending"]["stage"], "offered")
        for absent in ("executed", "damage", "physical", "applied", "status_eligible"):
            self.assertNotIn(absent, checked)

    # {
    #   責務: [test_invalid_requests_and_targets_preserve_current_ticket: 不正三キー要求/予約/対象/未習得を拒否し、有効要求を同じ予約で再試行します]
    #   処理: [1: 未知キーをfalse/0/空でも拒否し、非JSON値と厳密side/id・予約の境界を確認します]
    #   引数: [self: 要求/予約/対象の厳密検査を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_requests_and_targets_preserve_current_ticket(self):
        # 値が偽/空でも未知入力を拒否し、不正要求の後で同じ予約の有効検査を試します。
        invalid = [{"operation": "inspect", "request": value} for value in (None, False, 0, [], {}, {"ticket": None, "target": TARGET})]
        for field in ("status_effects", "status_resistances", "status_roll", "critical_roll", "variance", "skill", "equipment", "mode"):
            for value in (False, 0, {}):
                invalid.append({"operation": "inspect", "target": TARGET, "extra": {field: value}})
        for target in (None, False, {}, {**TARGET, "extra": 0}, normal.key("bad", "same"), normal.key("enemies", "../same"), ACTOR,
                       normal.key("enemies", "missing")):
            invalid.append({"operation": "inspect", "target": target})
        invalid += [{"operation": "inspect", "target": TARGET, "skill_id": value}
                    for value in (None, False, {}, "attack", "defend", "missing", "body_bash")]
        invalid += [{"operation": "inspect", "target": TARGET, "special": {"field": field, "value": value}}
                    for field in ("target", "ticket", "skill_id") for value in ("object", "nan")]
        invalid += [{"operation": "inspect", "target": TARGET, "ticket": value}
                    for value in (None, {}, {"round": 2, "slot": 0, "actor": ACTOR},
                                  {"round": 1, "slot": 0, "actor": TARGET},
                                  {"round": 1, "slot": 0, "actor": ACTOR, "extra": False})]
        case = preflight_case(steps=[{"operation": "next"}, *invalid, {"operation": "inspect", "target": TARGET}])
        actual = self.observe({"cases": [case]})["results"][0]
        # 一件でも予約を消費した拒否があれば、再試行可能性の破綻として失敗させます。
        for step in actual["steps"][1:-1]:
            with self.subTest(result=step["result"]):
                self.assertFalse(step["result"]["ok"])
                self.assertTrue(step["unchanged"])
        self.assertTrue(actual["steps"][-1]["result"]["ok"])
        self.assertTrue(actual["steps"][-1]["unchanged"])

    # {
    #   責務: [test_start_mismatches_and_failed_configuration_can_retry: 初回ラウンド前の数値/状態一致・未設定状態・一回設定を確認します]
    #   処理: [1: 設定失敗後に正しい開始情報で再試行し、ラウンド開始後/二重設定を拒否します]
    #   引数: [self: 非公開contextの設定寿命を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_start_mismatches_and_failed_configuration_can_retry(self):
        # 数値不一致/状態不一致の両方で、失敗した検査を正しい開始情報へ再設定できるか確認します。
        cases = []
        base = preflight_case()
        for field in ("context", "action_statuses"):
            case = copy.deepcopy(base)
            case[field] = copy.deepcopy(case["teams"] if field == "context" else case["initial_statuses"])
            if field == "context":
                case[field]["allies"][0]["snapshot"]["stats"]["attack"] += 1
            else:
                case[field]["enemies"]["same"].append("sleep")
            case["steps"] = [{"operation": "configure"}, {"operation": "configure"},
                             {"operation": "begin", "order": base["order"]}, {"operation": "next"},
                             {"operation": "inspect", "target": TARGET}]
            cases.append(case)
        cases += [preflight_case(legacy=True), preflight_case(configure=False, steps=[
            {"operation": "inspect", "target": TARGET}, {"operation": "begin", "order": base["order"]},
            {"operation": "configure"}])]
        actual = self.observe({"cases": cases})["results"]
        for index, reason in enumerate(("status_physical_context_mismatch", "status_physical_status_mismatch")):
            self.assertEqual(actual[index]["configured"]["reason"], reason)
            self.assertTrue(actual[index]["steps"][0]["result"]["ok"])
            self.assertEqual(actual[index]["steps"][1]["result"]["reason"], "already_initialized")
            self.assertTrue(actual[index]["steps"][-1]["result"]["ok"])
        self.assertEqual(actual[2]["configured"]["reason"], "status_not_configured")
        self.assertEqual(actual[3]["steps"][0]["result"]["reason"], "not_initialized")
        self.assertEqual(actual[3]["steps"][-1]["result"]["reason"], "session_not_fresh")

    # {
    #   責務: [test_latest_mp_damage_death_flee_claim_and_status_change: 検査のたびに最新MP/HP・生存/逃走/予約段階・所有状態を読み直します]
    #   処理: [1: Sessionの実APIで資源/状態を変更し、過去の成功検査を再利用せず最新結果を照合します]
    #   引数: [self: 予約提示後の状態変化を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_latest_mp_damage_death_flee_claim_and_status_change(self):
        # Sessionの実APIでだけ状態を変え、古い成功結果に依存しない検査を比較します。
        cases = [
            preflight_case(steps=[{"operation": "next"}, {"operation": "pay", "actor": ACTOR, "value": 48},
                {"operation": "inspect", "target": TARGET}]),
            preflight_case(steps=[{"operation": "next"}, {"operation": "damage", "actor": TARGET, "value": 10},
                {"operation": "inspect", "target": TARGET}]),
            preflight_case(steps=[{"operation": "next"}, {"operation": "damage", "actor": ACTOR, "value": 100},
                {"operation": "pay", "actor": ACTOR, "value": 50}, {"operation": "inspect", "target": TARGET}]),
            preflight_case(steps=[{"operation": "next"}, {"operation": "flee", "actor": ACTOR},
                {"operation": "inspect", "target": TARGET}]),
            preflight_case(steps=[{"operation": "next"}, {"operation": "claim"},
                {"operation": "inspect", "target": TARGET}, {"operation": "finish"},
                {"operation": "next"}, {"operation": "inspect", "target": ACTOR}]),
            preflight_case(steps=[{"operation": "next"}, {"operation": "claim"},
                {"operation": "apply_status", "actor": TARGET, "request": {"effect": {"id": "sleep", "chance": 1}, "roll": 0}},
                {"operation": "finish"}, {"operation": "next"}, {"operation": "inspect", "target": ACTOR}]),
        ]
        actual = self.observe({"cases": cases})["results"]
        self.assertEqual(actual[0]["steps"][-1]["result"]["reason"], "insufficient_mp")
        self.assertEqual(actual[1]["steps"][-1]["result"]["target_resources"]["hp"], 90)
        for case in actual[2:4]:
            self.assertTrue(case["steps"][-1]["result"]["ok"])
            self.assertFalse(case["steps"][-1]["result"]["eligibility"]["can_act"])
            self.assertTrue(case["steps"][-1]["unchanged"])
        self.assertEqual(actual[4]["steps"][2]["result"]["reason"], "already_claimed")
        self.assertTrue(actual[4]["steps"][-1]["result"]["ok"])
        self.assertEqual(actual[5]["steps"][-1]["result"]["actor_status"]["status_effects"],
                         [{"id": "sleep", "display_name": "sleep", "removable": True}])
        self.assertTrue(all(case["steps"][-1]["unchanged"] for case in actual))

    # {
    #   責務: [test_application_learning_legacy_and_atomic_failure_retry: MODコピーの正規習得境界と専用開始/従来拒否・全成功後公開を確認します]
    #   処理: [1: 一時dataのbody_bashへ付与を追加し、Lv6/7と不正初期状態からの再開始を観測します]
    #   引数: [self: Applicationと正規習得の接続を検証するテストケース]
    #   戻り値: [result: なし（None）。正規data/実セーブは編集しません]
    # }
    def test_application_learning_legacy_and_atomic_failure_retry(self):
        # 一時dataコピーだけを改変し、正規習得Lv6/7と通常物理の付与拒否を同時に確認します。
        mod = self.folder / "mod"
        shutil.copytree(self.content / "data", mod / "data")
        path = mod / "data/skills/skills.json"
        skills = json.loads(path.read_text(encoding="utf-8"))
        next(item for item in skills["skills"] if item["id"] == "body_bash")["status_effect"] = {"id": "bleeding", "chance": 1}
        path.write_text(json.dumps(skills), encoding="utf-8")
        cases = [preflight_case(joined=True, project_root=str(mod), records={
            side: [combatant.record("same", "slime", level=level)] for side in ("allies", "enemies")},
            initial_statuses={side: {"same": []} for side in ("allies", "enemies")},
            steps=[{"operation": "next"}, {"operation": "inspect", "target": TARGET, "skill_id": "body_bash"},
                   {"operation": "ordinary_action", "target": TARGET, "skill_id": "body_bash",
                    "extra": {"critical_roll": 0.5, "variance": 1}}]) for level in (6, 7)]
        valid = copy.deepcopy(cases[1])
        invalid = copy.deepcopy(valid)
        invalid["initial_statuses"] = {"allies": {}, "enemies": {}}
        invalid["steps"] = [{"operation": "start", "input": valid}, *valid["steps"]]
        cases += [invalid, {**valid, "legacy": True}]
        actual = self.observe({"cases": cases})["results"]
        self.assertEqual(actual[0]["steps"][1]["result"]["reason"], "skill_not_learned")
        self.assertTrue(actual[1]["steps"][1]["result"]["ok"])
        self.assertFalse(actual[1]["steps"][-1]["result"]["ok"])
        self.assertFalse(actual[2]["started"]["ok"])
        self.assertTrue(actual[2]["steps"][0]["result"]["ok"])
        self.assertTrue(actual[2]["steps"][2]["result"]["ok"])
        self.assertEqual(actual[3]["steps"][1]["result"]["reason"], "not_initialized")
        self.assertEqual(actual[3]["statuses"], {})

    # {
    #   責務: [test_selected_definition_and_equipment_reject: 未対応の選択定義と装備効果を非消費検査の成功として扱いません]
    #   処理: [1: 正規化前の未知効果と不正付与定義/装備補正を検査し、予約と資源の保持を確認します]
    #   引数: [self: 選択対象の定義/装備の境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_selected_definition_and_equipment_reject(self):
        # 選択した定義/装備の未知効果を削除せず、拒否後の予約と資源を照合します。
        cases = []
        for field, value in (("status_effect", False), ("unknown", 0), ("all_targets", False)):
            case = preflight_case()
            case["skills"]["skills"][0][field] = value
            cases.append(case)
        case = preflight_case()
        case["teams"]["allies"][0]["equipment"] = {"allowed_species_ids": ["slime"],
            "skill_modifiers": {"mod_status_hit": {"unknown": False}}}
        cases.append(case)
        actual = self.observe({"cases": cases})["results"]
        for case in actual:
            self.assertFalse(case["steps"][-1]["result"]["ok"])
            self.assertTrue(case["steps"][-1]["unchanged"])

    # {
    #   責務: [test_eight_actors_two_rounds_and_latest_guard: 両陣営同ID八体を二ラウンド検査し、最新guardと古い予約の拒否を確認します]
    #   処理: [1: 全員の検査前後を照合し、第一行動の基本防御を第二行動で読み、次ラウンドで解除を確認します]
    #   引数: [self: 参加者/ラウンドをまたぐ非消費検査を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_eight_actors_two_rounds_and_latest_guard(self):
        case = preflight_case()
        # 両陣営に同じ四IDを置き、予約を別途完了しながら全員の検査だけを非消費で実行します。
        templates = copy.deepcopy(case["teams"])
        case["teams"] = {side: [] for side in ("allies", "enemies")}
        case["initial_statuses"] = {side: {} for side in case["teams"]}
        case["order"], case["steps"] = [], []
        for side in case["teams"]:
            for index in range(4):
                member = copy.deepcopy(templates[side][0])
                member["snapshot"]["identity"]["id"] = str(index)
                case["teams"][side].append(member)
                case["initial_statuses"][side][str(index)] = ["poison"]
                case["order"].append(normal.key(side, str(index)))
        # guardの設定はSessionへ明示し、敵側の検査と次ラウンドの解除を読み取ります。
        observed = []
        for round_number in (1, 2):
            if round_number == 2:
                case["steps"].append({"operation": "begin", "order": case["order"]})
            for index, actor in enumerate(case["order"]):
                side = "enemies" if actor["side"] == "allies" else "allies"
                case["steps"].append({"operation": "next"})
                observed.append(len(case["steps"]))
                case["steps"] += [{"operation": "inspect", "target": normal.key(side, "0")},
                                  {"operation": "claim"}]
                if round_number == 1 and index == 0:
                    case["steps"].append({"operation": "defend", "value": 0.5})
                case["steps"].append({"operation": "finish"})
        actual = self.observe({"cases": [case]})["results"][0]
        for position in observed:
            step = actual["steps"][position]
            with self.subTest(position=position):
                self.assertTrue(step["result"]["ok"])
                self.assertTrue(step["unchanged"])
        self.assertEqual(actual["steps"][observed[4]]["result"]["target_guard"], 0.5)
        self.assertEqual(actual["steps"][observed[12]]["result"]["target_guard"], 1)
        self.assertEqual(actual["numeric"]["round"], 2)
        self.assertEqual(actual["numeric"]["phase"], "round_finished")

    # {
    #   責務: [test_dead_selected_target_missing_statuses_and_empty_teams: 他の敵が生存しても死んだ指定敵を拒否し、初期状態欠落と空参加者を区別します]
    #   処理: [1: 敵二体の片方だけを倒して検査し、空陣営の設定と初期状態不正後の再試行を確認します]
    #   引数: [self: 指定敵生存と開始状態の境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_dead_selected_target_missing_statuses_and_empty_teams(self):
        case = preflight_case()
        # 戦闘継続中でも死んだ指定対象を拒否し、生存する別対象への再検査は許可します。
        friend = copy.deepcopy(case["teams"]["enemies"][0])
        friend["snapshot"]["identity"]["id"] = "other"
        case["teams"]["enemies"].append(friend)
        case["initial_statuses"]["enemies"]["other"] = []
        case["order"].append(normal.key("enemies", "other"))
        case["steps"] = [{"operation": "next"}, {"operation": "damage", "actor": TARGET, "value": 100},
                         {"operation": "inspect", "target": TARGET},
                         {"operation": "inspect", "target": normal.key("enemies", "other")}]
        invalid = preflight_case(action_statuses={"allies": {}, "enemies": {}}, steps=[
            {"operation": "configure"}, {"operation": "begin", "order": [ACTOR, TARGET]}, {"operation": "next"},
            {"operation": "inspect", "target": TARGET}])
        empty = preflight_case(teams={"allies": [], "enemies": []}, initial_statuses={"allies": {}, "enemies": {}}, order=[],
                               steps=[{"operation": "next"}])
        actual = self.observe({"cases": [case, invalid, empty]})["results"]
        self.assertEqual(actual[0]["steps"][2]["result"]["reason"], "target_not_alive")
        self.assertTrue(actual[0]["steps"][3]["result"]["ok"])
        self.assertTrue(actual[0]["steps"][2]["unchanged"])
        self.assertFalse(actual[1]["configured"]["ok"])
        self.assertTrue(actual[1]["steps"][0]["result"]["ok"])
        self.assertTrue(actual[1]["steps"][-1]["result"]["ok"])
        self.assertTrue(actual[2]["configured"]["ok"])
        self.assertEqual(actual[2]["numeric"]["phase"], "stopped")

    # {
    #   責務: [test_preflight_benchmark_rejects_fast_failure_and_changed_owners: 少量の実Godot計測と固定結果照合を確認し、欠落/高速拒否/正本変更を不合格にします]
    #   処理: [1: 共用起動基底だけを一時importし、観測改変を専用性能validatorへ渡します]
    #   引数: [self: 非消費検査性能の実結果とvalidatorを確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_preflight_benchmark_rejects_fast_failure_and_changed_owners(self):
        # 少量でも実際に成功検査を測り、固定結果や正本保持を欠く高速観測はvalidatorで拒否します。
        result = self.observe({"performance": True, "iterations": 20, "samples": 3, "warmup": 2})
        folder = self.content / "tools/performance-check/script"
        shared_spec = importlib.util.spec_from_file_location("check_gdscript_status_cure", folder / "check_gdscript_status_cure.py")
        shared = importlib.util.module_from_spec(shared_spec)
        shared_spec.loader.exec_module(shared)
        spec = importlib.util.spec_from_file_location("status_physical_preflight_checker", folder / "check_gdscript_status_physical.py")
        module = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {"check_gdscript_status_cure": shared}):
            spec.loader.exec_module(module)
        checker = module.StatusPhysicalBenchmark("unused", argparse.Namespace(iterations=20, samples=3, warmup=2, preflight=True))
        self.assertTrue(checker.valid_result(result), result)
        for field, value in (("checked", {"ok": False}), ("actors", 7), ("definitions", 999), ("numeric", {}),
                             ("statuses", {}), ("session_preserved", False), ("input_preserved", False),
                             ("microseconds", -1), ("microseconds", 3001), ("iterations", 19)):
            damaged = copy.deepcopy(result)
            damaged[field] = value
            self.assertFalse(checker.valid_result(damaged), field)
