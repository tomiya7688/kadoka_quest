"""付与付き物理の実行準備と種族状態耐性を実Python/Godotで比較します。実セーブは使いません。"""
# {
#   責務: [test_gdscript_status_physical_context: 開始資源・習得/許可装備・初期状態/耐性・厳密拒否と索引選択を検証します]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import itertools
import json
import sys
import unittest
from unittest import mock

import test_gdscript_combatant as combatant
import test_gdscript_normal_attack_action as normal
import test_gdscript_status_cure as fixture
import test_gdscript_status_physical as prediction
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.battle_data import BattleDataLoader
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [context_case: 同IDの両陣営へ独立資源・習得・状態耐性・明示初期状態とMOD定義を作ります]
#   処理: [1: 共用数値fixtureへ状態準備と選択要求を加え、保存から独立した要求を返します]
#   引数: []
#   戻り値: [result: 実Godotへ渡す準備/選択の専用要求（dict）]
# }
def context_case():
    # 正規定義を編集せず、状態付きMODと通常のbody_bashを同じ選択索引へ置きます。
    canonical = json.loads((fixture.godot_fixture.ROOT / "data/skills/skills.json").read_text(encoding="utf-8"))
    skill = next(item for item in canonical["skills"] if item["id"] == "body_bash")
    teams = {side: [{"snapshot": normal.member("same", hp=100),
                     "skill_ids": ["mod_status_hit", "body_bash"], "equipment": {},
                     "status_resistances": {"bleeding": "weak"}}] for side in ("allies", "enemies")}
    return {"teams": teams, "skills": {"schema_version": 1, "skills": [prediction.definition(), skill]},
            "initial_statuses": {"allies": {"same": ["poison", {"id": "mod", "metadata": {"deck": [1, True]}}]},
                                 "enemies": {"same": []}},
            "selections": [{"actor": normal.key(side, "same"), "skill_id": "mod_status_hit"}
                           for side in ("allies", "enemies")]}


# {
#   責務: [StatusPhysicalContextBoundaryTests: 実行準備の共用検証と、Session/更新/保存/AIからの分離を確認します]
#   フィールド: []
# }
class StatusPhysicalContextBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_preparation_reuses_rules_without_gameplay_mutation: 準備が既存資源/状態検査へ委譲し、実行や数値式を持たないことを確認します]
    #   処理: [1: 純粋準備の依存と禁止呼出を照合し、通常物理の専用入口固定を確認します]
    #   引数: [self: 準備の責務境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_preparation_reuses_rules_without_gameplay_mutation(self):
        root = fixture.godot_fixture.ROOT / "gdscript"
        source = (root / "engine/status_physical_skill_context.gd").read_text(encoding="utf-8")
        # 準備と実行を同一視せず、I/O/乱数源/資源更新を純粋engineへ入れません。
        for forbidden in ("FileAccess", "DirAccess", "RandomNumberGenerator", "randf(", "battle_session",
                          "res://application/", "res://data/", "res://ui/", ".pay_mp(", ".take_damage(", ".apply_status"):
            self.assertNotIn(forbidden, source)
        for shared in ("Physical.prepare(", "InitialMap.prepare(", "Resistance.validate(", "Physical.select_status_physical("):
            self.assertIn(shared, source)
        physical = (root / "engine/physical_skill_context.gd").read_text(encoding="utf-8")
        self.assertIn("return _select(context, actor, skill_id, Quote)", physical)
        self.assertIn("return _select(context, actor, skill_id, StatusQuote)", physical)


# {
#   責務: [StatusPhysicalContextTests: 専用要求/保存ダミーと読取専用正規JSON・実Godotの準備比較を所有します]
#   フィールド: [
#     folder: 共用fixtureの要求/保存ダミー領域（Path）
#     saved_files: 毎起動後にbyte保持を確認する五種類の保存ダミー（list[Path]）
#     content: 正規dataを読取専用で参照する実チェックアウト（Path）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for status physical preparation")
class StatusPhysicalContextTests(unittest.TestCase):
    # {
    #   責務: [setUp: 共用保存ダミーを作り、正規JSONのbyte保持を終了時に検査する準備をします]
    #   処理: [1: 共用fixtureへ一時領域を委譲し、正規JSONハッシュと終了時検査を登録します]
    #   引数: [self: 専用領域と正規JSONの保持確認を所有するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        # 正規JSONは読取専用にし、AI/items/party/state等は共用の保存ダミーだけを使います。
        fixture.StatusCureQuoteTests.setUp(self)
        self.content = fixture.godot_fixture.ROOT
        hashes = {path: hashlib.sha256(path.read_bytes()).digest() for path in (self.content / "data").rglob("*.json")}
        self.addCleanup(self.check_canonical, hashes)

    # {
    #   責務: [check_canonical: 登録済み正規JSONのハッシュを再取得し、検証開始時と一致するか確認します]
    #   処理: [1: JSONパス別の現在ハッシュを開始前の値と照合します]
    #   引数: [
    #     self: 正規JSONの保持を確認するテストケース
    #     hashes: 開始時のJSONパス別ハッシュ（dict）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def check_canonical(self, hashes):
        # 読取専用の正規JSONへテストが副作用を残していないことを確認します。
        self.assertEqual(hashes, {path: hashlib.sha256(path.read_bytes()).digest() for path in hashes})

    # {
    #   責務: [observe: 専用区分を付け、共用のGodot起動/診断・要求と保存ダミーのbyte検査へ委譲します]
    #   処理: [1: 独立コピー要求へstatus_physical_contextを加え、実Godot結果を返します]
    #   引数: [
    #     self: 要求領域と保存ダミーの所有者
    #     payload: 準備ケースまたは性能条件（dict）
    #   ]
    #   戻り値: [result: 診断とファイル保持を確認した実観測（dict）]
    # }
    def observe(self, payload):
        # 起動と保存ダミーの検査を共用し、実セーブを開く独自経路を作りません。
        return fixture.StatusCureQuoteTests.run_probe(self, {**copy.deepcopy(payload), "status_physical_context": True})

    # {
    #   責務: [test_independent_preparation_and_normal_physical_rejection: 同IDの陣営を分離し、付与/通常物理の選択とコピー独立性を確認します]
    #   処理: [1: 数値六キー・状態/耐性・装備補正を照合し、通常物理の付与拒否を確認します]
    #   引数: [self: 成功準備と専用入口を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_independent_preparation_and_normal_physical_rejection(self):
        case = context_case()
        # 選択IDの補正だけを使い、他IDの未知補正や属性段階を状態耐性へ混ぜません。
        case["teams"]["allies"][0]["equipment"] = {
            "allowed_species_ids": ["slime"], "fixed_bonus_damage": 3, "resistance_steps": {"bleeding": 100},
            "skill_modifiers": {"mod_status_hit": {"power_multiplier": 2}, "other": {"unknown": False}}}
        case["teams"]["enemies"][0]["status_resistances"] = {"bleeding": "immune", "custom": "future"}
        case["selections"] += [
            {"actor": normal.key("allies", "same"), "skill_id": "mod_status_hit", "normal_physical": True},
            {"actor": normal.key("allies", "same"), "skill_id": "body_bash", "normal_physical": True},
            {"actor": normal.key("allies", "same"), "skill_id": "body_bash"}]
        actual = self.observe({"cases": [case]})["results"][0]
        prepared = actual["prepared"]
        self.assertTrue(prepared["ok"], actual)
        self.assertEqual(prepared["initial_statuses"], case["initial_statuses"])
        for side in ("allies", "enemies"):
            self.assertEqual(prepared["snapshots"][side][0], case["teams"][side][0]["snapshot"])
            self.assertEqual(len(prepared["snapshots"][side][0]), 6)
            self.assertEqual(prepared["context"]["members"][side]["same"]["status_resistances"],
                             case["teams"][side][0]["status_resistances"])
        results = [item["result"] for item in actual["selections"]]
        self.assertEqual([item["ok"] for item in results], [True, True, False, True, False])
        self.assertEqual(results[0]["equipment"], {"power_multiplier": 2, "fixed_bonus_damage": 3})
        self.assertEqual(results[-1]["reason"], "status_effect_required")
        self.assertTrue(all(item["independent"] for item in actual["selections"]))
        self.assertTrue(actual["source_independent"] and actual["input_preserved"])

    # {
    #   責務: [test_canonical_learning_and_species_status_resistances_match_python: 正規八種族の状態耐性/資源とスライムLv6/7の習得差を実Pythonへ照合します]
    #   処理: [1: 読取専用BuilderとBattleDataLoaderの結果を比較し、選択条件と入力保持を確認します]
    #   引数: [self: 正規Lv別習得と種族/装備境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_canonical_learning_and_species_status_resistances_match_python(self):
        loader = BattleDataLoader(GameRepository(self.content / "data"))
        cases, expectations = [], []
        # 正規定義をファイルへ書かず、比較用body_bashへ状態効果を加えた互換MODだけを使用します。
        for species, equipment in itertools.product(
            ("hero", "slime", "ball_slime", "metal_slime", "ghost", "maru", "kadoka", "dice_slime"), (None, "ken", "light_cloth")
        ):
            case = context_case()
            case["project_root"] = str(self.content)
            case["records"] = {side: [combatant.record("same", species, level=100, equipment_id=equipment)]
                               for side in ("allies", "enemies")}
            cases.append(case)
            raw = case["records"]["allies"][0]
            expectations.append(loader.build_combatant(MonsterRecord(raw["monster"], raw["ai"])))
        for level in (6, 7):
            case = context_case()
            case["project_root"] = str(self.content)
            case["records"] = {side: [combatant.record("same", "slime", level=level)] for side in ("allies", "enemies")}
            base = copy.deepcopy(next(item for item in case["skills"]["skills"] if item["id"] == "body_bash"))
            base["status_effect"] = prediction.definition()["status_effect"]
            case["skills"]["skills"] = [base]
            case["selections"] = [{"actor": normal.key("allies", "same"), "skill_id": "body_bash"}]
            cases.append(case)
            raw = case["records"]["allies"][0]
            expectations.append(loader.build_combatant(MonsterRecord(raw["monster"], raw["ai"])))
        observations = self.observe({"cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        for index, (observed, expected) in enumerate(zip(observations, expectations)):
            with self.subTest(index=index):
                self.assertTrue(observed["prepared"]["ok"], observed)
                actual = observed["prepared"]["context"]["members"]["allies"]["same"]
                self.assertEqual(actual["status_resistances"], expected.status_resistances)
                self.assertEqual(actual["skill_ids"], [item["id"] for item in expected.skills])
                self.assertEqual(observed["prepared"]["snapshots"]["allies"][0]["stats"], expected.stats)
                self.assertEqual(actual["equipment"], expected.equipment or {})
                self.assertTrue(observed["source_independent"] and observed["input_preserved"])
        self.assertEqual([row["selections"][0]["result"]["ok"] for row in observations[-2:]], [False, True])

    # {
    #   責務: [test_empty_teams_and_unknown_state_metadata_are_preserved: 空開始と未知状態/重複/拡張情報を受理し、明示一覧と耐性名を保持します]
    #   処理: [1: 空陣営と未知状態の要求を実Godotへ渡し、値とコピー独立性を照合します]
    #   引数: [self: 明示空状態とMOD情報の境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_empty_teams_and_unknown_state_metadata_are_preserved(self):
        empty, unknown = context_case(), context_case()
        empty.update(teams={"allies": [], "enemies": []}, initial_statuses={"allies": {}, "enemies": {}}, selections=[])
        unknown["initial_statuses"]["allies"]["same"] = ["mod", "mod", {}, {"metadata": {"deck": [None, False, 0]}}]
        for case, actual in zip((empty, unknown), self.observe({"cases": [empty, unknown]})["results"]):
            self.assertTrue(actual["prepared"]["ok"], actual)
            self.assertEqual(actual["prepared"]["initial_statuses"], case["initial_statuses"])
            self.assertTrue(actual["input_preserved"] and actual["source_independent"])

    # {
    #   責務: [test_invalid_fresh_resources_initial_maps_and_native_values_reject: 不正資源/初期状態/耐性・Object/循環/非有限/過深を部分成功なしで拒否します]
    #   処理: [1: 不正準備とnative値のケースを実Godotへ渡し、要求保持と診断なし拒否を確認します]
    #   引数: [self: 厳密な開始条件を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_fresh_resources_initial_maps_and_native_values_reject(self):
        cases = []
        # 不正な開始資源/習得/許可装備は、共用の物理準備と同じ条件で拒否します。
        for field, value in (("hp", 1), ("mp", -1), ("fled", True), ("extra", False)):
            case = context_case()
            case["teams"]["allies"][0]["snapshot"][field] = value
            cases.append(case)
        for field, value in (("skill_ids", [None]), ("equipment", {"allowed_species_ids": ["ghost"]}),
                             ("status_resistances", None), ("status_resistances", {"bleeding": False})):
            case = context_case()
            case["teams"]["allies"][0][field] = value
            cases.append(case)
        missing = context_case()
        del missing["teams"]["allies"][0]["status_resistances"]
        cases.append(missing)
        for count in (2, 5):
            case = context_case()
            case["teams"]["allies"] *= count
            cases.append(case)
        for value in (None, [], {}, {"allies": {}, "enemies": {}},
                      {"allies": {"same": [], "other": []}, "enemies": {"same": []}}):
            case = context_case()
            case["initial_statuses"] = value
            cases.append(case)
        for field_value in (False, 0, [], {}):
            case = context_case()
            case["initial_statuses"]["extra"] = field_value
            cases.append(case)
        for value in (None, {}, [None], [{"id": None}], [{"removable": 1}], [{"metadata": 2**53}]):
            case = context_case()
            case["initial_statuses"]["allies"]["same"] = value
            cases.append(case)
        # JSONで運べない値は専用プローブ内で注入し、深いコピーの前に拒否することを確認します。
        paths = [["teams", "allies", 0, "snapshot", "stats", "attack"],
                 ["teams", "allies", 0, "status_resistances", "bleeding"],
                 ["skills", "skills", 0, "status_effect", "metadata"],
                 ["initial_statuses", "allies", "same", 1, "metadata"]]
        for path, value in itertools.product(paths, ("nan", "inf", "object", "cycle", "non_string_key")):
            case = context_case()
            case["special"] = {"path": path, "value": value}
            cases.append(case)
        nested = 1
        for _ in range(33):
            nested = [nested]
        case = context_case()
        case["skills"]["skills"][0]["status_effect"]["metadata"] = nested
        cases.append(case)
        # 初期辞書の挿入順と参加者順が違っても、共用前と同じ先頭参加者の拒否を返します。
        ordered = context_case()
        second = copy.deepcopy(ordered["teams"]["allies"][0])
        second["snapshot"]["identity"]["id"] = "second"
        ordered["teams"]["allies"].append(second)
        ordered["initial_statuses"]["allies"] = {"second": [None], "same": [None]}
        cases.append(ordered)
        observations = self.observe({"cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        for index, observed in enumerate(observations):
            with self.subTest(index=index):
                self.assertFalse(observed["prepared"]["ok"], observed)
                self.assertNotIn("context", observed["prepared"])
                self.assertNotIn("snapshots", observed["prepared"])
                self.assertTrue(observed["input_preserved"])
        self.assertEqual(observations[-1]["prepared"]["id"], "same")

    # {
    #   責務: [test_selection_rejects_unknown_definitions_modifiers_and_bad_actors: 不正参加者/未習得/重複定義・未知効果/装備補正を非破壊的に拒否します]
    #   処理: [1: 専用選択の拒否と準備context/要求/返却ネストの保持を確認します]
    #   引数: [self: 定義と装備選択の対応範囲を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_selection_rejects_unknown_definitions_modifiers_and_bad_actors(self):
        cases = []
        for field, value in itertools.product(("target", "self_damage_ratio", "element", "mode"), (False, 0, {}, [])):
            case = context_case()
            case["skills"]["skills"][0][field] = value
            cases.append(case)
        for value in (None, [], {"extra": False}, {"power_multiplier": True}):
            case = context_case()
            case["teams"]["allies"][0]["equipment"] = {"allowed_species_ids": ["slime"],
                "skill_modifiers": {"mod_status_hit": value}}
            case["selections"] = case["selections"][:1]
            cases.append(case)
        duplicate = context_case()
        duplicate["skills"]["skills"].append(copy.deepcopy(duplicate["skills"]["skills"][0]))
        cases.append(duplicate)
        # contextは編集可能な通常データなので、不正な外形は診断ではなく理由付きで拒否します。
        bad = context_case()
        base = {"actor": normal.key("allies", "same"), "skill_id": "mod_status_hit"}
        bad["selections"] = [{**base, "actor": value} for value in
                             (None, {}, False, [], normal.key("allies", "missing"), {**base["actor"], "extra": 0})]
        bad["selections"] += [{**base, "skill_id": value} for value in (None, False, "", "attack", "defend", "not_learned")]
        bad["selections"] += [{**base, "context_override": value} for value in
                             (None, [], False, {}, {"members": {}, "definitions": {}})]
        cases.append(bad)
        for observed in self.observe({"cases": cases})["results"]:
            self.assertTrue(observed["prepared"]["ok"], observed)
            self.assertTrue(observed["source_independent"] and observed["input_preserved"])
            for selected in observed["selections"]:
                self.assertFalse(selected["result"]["ok"], observed)
                self.assertTrue(selected["independent"])

    # {
    #   責務: [test_status_resistance_defaults_preserve_strings_and_reject_bad_maps: 種族の省略耐性/未知名/吸収/反射を保持し、不正な辞書や値を拒否します]
    #   処理: [1: 装備を受け取らない純粋種族契約へ、正常/不正な状態耐性定義を渡します]
    #   引数: [self: 属性と状態耐性の分離を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_status_resistance_defaults_preserve_strings_and_reject_bad_maps(self):
        maps = [{}, {"bleeding": "immune"}, {"mod": "future", "poison": "absorb", "sleep": "reflect"}]
        bad = [None, [], False, {"status_resistances": None}, {"status_resistances": []},
               {"status_resistances": {"": "normal"}}, {"status_resistances": {"bleeding": 0}}]
        cases = [{}, *[{"status_resistances": item} for item in maps], *bad]
        actual = self.observe({"species": cases})["resistances"]
        self.assertEqual([item["status_resistances"] for item in actual[:4]], [{}, *maps])
        self.assertTrue(all(not item["ok"] for item in actual[4:]))

    # {
    #   責務: [test_context_benchmark_rejects_fast_failure_and_corrupted_preparation: 性能検査が八体/千定義・正常選択/状態耐性/原本を固定期待値で確認します]
    #   処理: [1: 少量の実Godot計測は通過し、拒否/欠落/誤状態/原本改変の観測を不合格にします]
    #   引数: [self: 選択性能の実条件を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_context_benchmark_rejects_fast_failure_and_corrupted_preparation(self):
        result = self.observe({"performance": True, "iterations": 20, "samples": 3, "warmup": 2})
        folder = self.content / "tools/performance-check/script"
        # 共用CLIのimportだけを一時登録し、他のテストや通常起動の検索パスを変えません。
        shared_spec = importlib.util.spec_from_file_location("check_gdscript_status_cure", folder / "check_gdscript_status_cure.py")
        shared = importlib.util.module_from_spec(shared_spec)
        shared_spec.loader.exec_module(shared)
        spec = importlib.util.spec_from_file_location("status_physical_context_checker", folder / "check_gdscript_status_physical.py")
        module = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {"check_gdscript_status_cure": shared}):
            spec.loader.exec_module(module)
        checker = module.StatusPhysicalBenchmark("unused", argparse.Namespace(iterations=20, samples=3, warmup=2, context=True))
        self.assertTrue(checker.valid_result(result), result)
        for field, value in (("selected", {"ok": False}), ("actors", 7), ("definitions", 999), ("member", {}),
                             ("snapshot", {}), ("initial_statuses", []), ("prepared_preserved", False),
                             ("input_preserved", False), ("microseconds", -1), ("microseconds", 3001), ("iterations", 19)):
            damaged = copy.deepcopy(result)
            damaged[field] = value
            self.assertFalse(checker.valid_result(damaged), field)
