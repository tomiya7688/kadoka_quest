"""治療付き回復の開始情報・習得/装備選択・初期状態一致を実Godotで検証します。実セーブは使いません。"""
# {
#   責務: [test_gdscript_cure_heal_context: 準備の厳密拒否・正規Lv別習得・定義選択・独立コピーと保存境界を検証します]
#   フィールド: []
# }
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import itertools
import json
import unittest

import test_gdscript_combatant as combatant_fixture
import test_gdscript_normal_attack_action as normal
import test_gdscript_status_cure as fixture


# {
#   責務: [context_case: 同じIDを持つ両陣営に独立した開始資源・習得・明示初期状態を用意します]
#   処理: [1: 既存の数値fixtureを使い、正規スキル一覧と参加者別初期状態・選択列を作ります]
#   引数: []
#   戻り値: [result: 実保存から独立した両陣営の準備要求（dict）]
# }
def context_case():
    document = json.loads((fixture.godot_fixture.ROOT / "data/skills/skills.json").read_text(encoding="utf-8"))
    teams = {side: [{"snapshot": normal.member("same"), "skill_ids": ["spirit_recover", "small_heal"], "equipment": {}}]
             for side in ("allies", "enemies")}
    statuses = {"allies": {"same": [{"id": "lock", "removable": False},
                                   {"id": "poison", "metadata": {"deck": [1, {"kept": True}]}}, "sleep"]},
                "enemies": {"same": []}}
    return {"teams": teams, "skills": document, "initial_statuses": statuses,
            "selections": [{"actor": normal.key(side, "same"), "skill_id": "spirit_recover"}
                           for side in ("allies", "enemies")]}


# {
#   責務: [CureHealContextBoundaryTests: 実行準備をHP/MP・状態の実更新・Session・保存・AIから分離する境界を確認します]
#   フィールド: []
# }
class CureHealContextBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_preparation_does_not_add_runtime_mutation_or_io: 準備契約に実更新や保存・画面依存を追加しないことを確認します]
    #   処理: [1: 純粋準備の禁止依存と、既存行動/applicationへの未接続を確認します]
    #   引数: [self: 準備契約の依存を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_preparation_does_not_add_runtime_mutation_or_io(self):
        root = fixture.godot_fixture.ROOT / "gdscript"
        source = (root / "engine/cure_heal_skill_context.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                          "battle_session", "RandomNumberGenerator", "randf(", ".pay_mp(", ".heal(", ".cure("):
            self.assertNotIn(forbidden, source)
        for name in ("engine/heal_skill_action", "engine/battle_session", "application/battle_session_application"):
            self.assertNotIn("cure_heal_skill_context", (root / f"{name}.gd").read_text(encoding="utf-8"))


# {
#   責務: [CureHealContextTests: 共用要求/保存ダミー領域と実Godotの準備・選択検証を所有します]
#   フィールド: [
#     folder: 共用プローブに渡す専用要求の領域（Path）
#     saved_files: byte不変を確認する個体・AI・items・party・stateの保存ダミー（list[Path]）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real cure-heal preparation")
class CureHealContextTests(unittest.TestCase):
    # {
    #   責務: [setUp: 実保存から独立した共用の要求領域と保存ダミーを用意します]
    #   処理: [1: 既存治療fixtureへ専用領域の作成を委譲します]
    #   引数: [self: 専用領域と保存ダミーの所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        fixture.StatusCureQuoteTests.setUp(self)

    # {
    #   責務: [run_probe: 準備専用区分を付け、共用の実Godot起動/診断/保存保持検査へ委譲します]
    #   処理: [1: コピー要求にcure_context=trueを付け、要求と保存ダミーのbyte不変を確認します]
    #   引数: [
    #     self: 要求領域と保存ダミーの所有者
    #     payload: 準備ケース一覧または計測条件（dict）
    #   ]
    #   戻り値: [result: 診断なしで観測した実Godot結果（dict）]
    # }
    def run_probe(self, payload):
        return fixture.StatusCureQuoteTests.run_probe(self, {**copy.deepcopy(payload), "cure_context": True})

    # {
    #   責務: [test_independent_preparation_side_identity_and_separate_heal_entries: 同IDの両陣営を分離し、準備/選択の独立性と専用入口を確認します]
    #   処理: [1: 両陣営の初期状態・数値六キー・正規定義選択と、通常HP回復の治療拒否を照合します]
    #   引数: [self: 開始情報の独立性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_independent_preparation_side_identity_and_separate_heal_entries(self):
        case = context_case()
        case["selections"] += [{"actor": normal.key("allies", "same"), "skill_id": "spirit_recover", "normal_heal": True},
                               {"actor": normal.key("allies", "same"), "skill_id": "small_heal", "normal_heal": True}]
        observed = self.run_probe({"cases": [case]})["results"][0]
        self.assertTrue(observed["prepared"]["ok"])
        self.assertEqual(observed["prepared"]["initial_statuses"], case["initial_statuses"])
        for side in ("allies", "enemies"):
            snapshot = observed["prepared"]["snapshots"][side][0]
            self.assertEqual(set(snapshot), {"identity", "stats", "hp", "mp", "fled", "alive"})
            self.assertEqual(snapshot, case["teams"][side][0]["snapshot"])
        selections = observed["selections"]
        self.assertTrue(all(item["result"]["ok"] for item in selections[:2]))
        self.assertFalse(selections[2]["result"]["ok"])
        self.assertTrue(selections[3]["result"]["ok"])
        self.assertTrue(all(item["independent"] for item in selections))
        self.assertTrue(observed["source_independent"])
        self.assertTrue(observed["input_preserved"])

    # {
    #   責務: [test_canonical_hero_level_learning_and_canonical_data_are_preserved: 正規HeroのLv59/60で習得差を再構築し、正規JSONのbyte不変を確認します]
    #   処理: [1: 読取専用Builderの再構築を使い、spirit_recoverの未習得/習得を照合します]
    #   引数: [self: 正規Lv別習得と保存境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_canonical_hero_level_learning_and_canonical_data_are_preserved(self):
        root = fixture.godot_fixture.ROOT / "data"
        before = {path: hashlib.sha256(path.read_bytes()).digest() for path in root.rglob("*.json")}
        cases = []
        for level in (59, 60):
            case = context_case()
            case["records"] = {side: [combatant_fixture.record("same", "hero", level=level)] for side in ("allies", "enemies")}
            case["project_root"] = str(fixture.godot_fixture.ROOT)
            cases.append(case)
        for level, observed in zip((59, 60), self.run_probe({"cases": cases})["results"]):
            with self.subTest(level=level):
                self.assertTrue(observed["prepared"]["ok"], observed)
                for item in observed["selections"]:
                    self.assertEqual(item["result"]["ok"], level == 60)
                    if level == 59:
                        self.assertEqual(item["result"]["reason"], "skill_not_learned")
                self.assertTrue(observed["source_independent"])
                self.assertTrue(observed["input_preserved"])
        self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).digest() for path in before})

    # {
    #   責務: [test_empty_sides_and_unknown_status_metadata_remain_independent: 空陣営と明示した空状態を受理し、未知状態/重複/ネスト情報を保持します]
    #   処理: [1: 空開始と未知状態を実Godotへ渡し、値の保持と入力/結果の独立性を確認します]
    #   引数: [self: 明示空状態とMOD情報を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_empty_sides_and_unknown_status_metadata_remain_independent(self):
        empty = context_case()
        empty.update(teams={"allies": [], "enemies": []}, initial_statuses={"allies": {}, "enemies": {}}, selections=[])
        unknown = context_case()
        unknown["initial_statuses"]["allies"]["same"] = ["mod_status", "mod_status", {},
            {"id": "custom", "removable": False, "metadata": {"deck": [None, False, {"kept": 0}]}}]
        unknown["teams"]["allies"][0]["equipment"] = {"allowed_species_ids": ["slime"],
            "skill_modifiers": {"spirit_recover": {"power_multiplier": 1}}}
        for case, observed in zip((empty, unknown), self.run_probe({"cases": [empty, unknown]})["results"]):
            self.assertTrue(observed["prepared"]["ok"], observed)
            self.assertEqual(observed["prepared"]["initial_statuses"], case["initial_statuses"])
            self.assertTrue(observed["input_preserved"])
            self.assertTrue(observed["source_independent"])

    # {
    #   責務: [test_invalid_initial_maps_and_effects_reject_without_partial_preparation: 初期状態の欠落/余分・不正型・非有限/Object/循環を部分成功なしで拒否します]
    #   処理: [1: 初期状態と参加者の不一致、不正状態のケースを実Godotへ渡し、準備情報を返さないことを確認します]
    #   引数: [self: 初期状態の厳密一致を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_initial_maps_and_effects_reject_without_partial_preparation(self):
        cases = []
        invalid = [None, [], False, {}, {"allies": {}, "enemies": {}},
                   {"allies": {"other": []}, "enemies": {"same": []}},
                   {"allies": {"same": [], "extra": []}, "enemies": {"same": []}}]
        for value in invalid:
            case = context_case()
            case["initial_statuses"] = value
            cases.append(case)
        for value in (False, 0, [], {}):
            case = context_case()
            case["initial_statuses"]["extra"] = value
            cases.append(case)
        for effects in (None, {}, "poison", [0], [None], [{"id": None}], [{"removable": 1}], [{"metadata": 2**53}]):
            case = context_case()
            case["initial_statuses"]["allies"]["same"] = effects
            cases.append(case)
        nested = 1
        for _ in range(33):
            nested = [nested]
        case = context_case()
        case["initial_statuses"]["allies"]["same"] = [{"metadata": nested}]
        cases.append(case)
        for value in ("nan", "inf", "object", "cycle"):
            case = context_case()
            case["special"] = {"side": "allies", "id": "same", "value": value}
            cases.append(case)
        observations = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        for index, observed in enumerate(observations):
            with self.subTest(index=index):
                self.assertFalse(observed["prepared"]["ok"], observed)
                self.assertNotIn("context", observed["prepared"])
                self.assertNotIn("snapshots", observed["prepared"])
                self.assertTrue(observed["input_preserved"])

    # {
    #   責務: [test_invalid_fresh_resources_learned_skills_and_permissions_reject: 不正開始資源・不正習得・種族不許可装備を共用検証で拒否します]
    #   処理: [1: 消費済み/不正資源・重複/参加数超過・不正習得/装備の開始ケースを確認します]
    #   引数: [self: 共用開始検証を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_fresh_resources_learned_skills_and_permissions_reject(self):
        cases = []
        for field, value in (("hp", 1), ("mp", -1), ("fled", True), ("extra", False)):
            case = context_case()
            case["teams"]["allies"][0]["snapshot"][field] = value
            cases.append(case)
        for ids in (None, [None], [""], [False]):
            case = context_case()
            case["teams"]["allies"][0]["skill_ids"] = ids
            cases.append(case)
        for item in ({"allowed_species_ids": []}, {"allowed_species_ids": ["ghost"]},
                     {"allowed_species_ids": ["slime"], "skill_modifiers": []}, {"extra": False}):
            case = context_case()
            case["teams"]["allies"][0]["equipment"] = item
            cases.append(case)
        for count in (2, 5):
            case = context_case()
            case["teams"]["allies"] *= count
            cases.append(case)
        for observed in self.run_probe({"cases": cases})["results"]:
            self.assertFalse(observed["prepared"]["ok"], observed)
            self.assertTrue(observed["input_preserved"])

    # {
    #   責務: [test_definition_and_equipment_selection_rejects_unimplemented_effects: 治療付き専用入口の定義一意性・必須確率・未知効果/装備拒否を確認します]
    #   処理: [1: 正規定義の改変と選択IDの不正装備をケース化し、選択拒否と準備の保持を確認します]
    #   引数: [self: 選択対応範囲を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_definition_and_equipment_selection_rejects_unimplemented_effects(self):
        cases = []
        for field, value in itertools.product(("extra", "self_damage_ratio", "target", "element", "heal_ratio_multiplier"), (False, 0, "")):
            case = context_case()
            next(item for item in case["skills"]["skills"] if item["id"] == "spirit_recover")[field] = value
            cases.append(case)
        for chance in (None, False, "nan", 2**53):
            case = context_case()
            next(item for item in case["skills"]["skills"] if item["id"] == "spirit_recover")["status_cure_chance"] = chance
            cases.append(case)
        for modifier in (None, [], {"extra": False}, {"heal_ratio_multiplier": 0}, {"power_multiplier": True}):
            case = context_case()
            case["teams"]["allies"][0]["equipment"] = {"allowed_species_ids": ["slime"], "skill_modifiers": {"spirit_recover": modifier}}
            case["selections"] = case["selections"][:1]
            cases.append(case)
        duplicate = context_case()
        duplicate["skills"]["skills"].append(copy.deepcopy(next(item for item in duplicate["skills"]["skills"] if item["id"] == "spirit_recover")))
        cases.append(duplicate)
        for index, observed in enumerate(self.run_probe({"cases": cases})["results"]):
            with self.subTest(index=index):
                self.assertTrue(observed["prepared"]["ok"], observed)
                for item in observed["selections"]:
                    self.assertFalse(item["result"]["ok"], observed)
                    self.assertTrue(item["independent"])
                self.assertTrue(observed["source_independent"])
                self.assertTrue(observed["input_preserved"])
        valid = context_case()
        valid["teams"]["allies"][0]["equipment"] = {"allowed_species_ids": ["slime"], "fixed_bonus_damage": 11,
            "skill_modifiers": {"spirit_recover": {"power_multiplier": 99}, "other": {"unimplemented": True}}}
        valid["skills"]["skills"] += [{"id": "other"}, {"id": "other"}]
        self.assertTrue(self.run_probe({"cases": [valid]})["results"][0]["selections"][0]["result"]["ok"])

    # {
    #   責務: [test_invalid_actor_context_and_unlearned_id_do_not_raise_or_mutate: 不正参加者/開始情報・未習得/不正IDを診断なしで拒否します]
    #   処理: [1: 専用選択入口へ不正値を渡し、共用Godot診断検査とcontext保持を確認します]
    #   引数: [self: 選択要求の厳密拒否を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_actor_context_and_unlearned_id_do_not_raise_or_mutate(self):
        case = context_case()
        base = {"actor": normal.key("allies", "same"), "skill_id": "spirit_recover"}
        case["selections"] = [{**base, "actor": actor} for actor in (None, {}, False, [], normal.key("other", "same"),
                                normal.key("allies", "missing"), {**normal.key("allies", "same"), "extra": False})]
        case["selections"] += [{**base, "skill_id": value} for value in (None, False, "", "attack", "defend", "small_heal", "not_learned")]
        case["selections"] += [{**base, "context_override": value} for value in (None, [], False, {}, {"members": {}, "definitions": {}})]
        for item in self.run_probe({"cases": [case]})["results"][0]["selections"]:
            self.assertFalse(item["result"]["ok"], item)
            self.assertTrue(item["independent"])

    # {
    #   責務: [test_context_benchmark_checks_successful_definition_selection: 計測経路とCLIが八体・千定義・正規化選択・原本保持を照合することを確認します]
    #   処理: [1: 少数反復の実Godot結果をCLIへ照合し、拒否/誤定義/入力改変の観測を不合格にします]
    #   引数: [self: 定義選択の性能検査を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_context_benchmark_checks_successful_definition_selection(self):
        result = self.run_probe({"performance": True, "iterations": 20, "samples": 3, "warmup": 2})
        path = fixture.godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_status_cure.py"
        spec = importlib.util.spec_from_file_location("kadoka_cure_context_benchmark", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        checker = module.StatusCureBenchmark("unused", argparse.Namespace(iterations=20, samples=3, warmup=2, cure_context=True))
        self.assertTrue(checker._valid_context_result(result), result)
        for field, value in (("selected", {"ok": False}), ("actors", 7), ("definitions", 999), ("prepared_preserved", False), ("microseconds", 3001)):
            damaged = {**result, field: value}
            self.assertFalse(checker._valid_context_result(damaged), field)
