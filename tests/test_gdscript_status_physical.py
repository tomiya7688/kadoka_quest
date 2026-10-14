"""非致死の付与付き物理予測を実Python/Godotで比較します。実セーブを使わず、正規JSONも保持します。"""
# {
#   責務: [test_gdscript_status_physical: 定義/準備/結果と非致死条件・拒否/独立性・性能の実結果を検証します]
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

import test_gdscript_normal_attack_action as normal
import test_gdscript_physical_skill as physical
import test_gdscript_status_cure as fixture
import test_gdscript_turn_order as turn
from kadoka_quest.core.status_effects import status_stat_multiplier


# {
#   責務: [definition: 固定の物理数値とネスト付き出血定義を持つ、独立MODスキルを作ります]
#   処理: [1: 原本を共有しない定義へケース別の上書きを加えます]
#   引数: [changes: ケース別の対応/不正フィールドを上書きする値]
#   戻り値: [result: 独立した付与付きphysical定義（dict）]
# }
def definition(**changes):
    return {"id": "mod_status_hit", "display_name": "試験付与打撃", "kind": "physical", "mp_cost": 3,
            "status_effect": {"id": " bleeding ", "display_name": "出血", "chance": 0.4,
                              "metadata": {"deck": [1, {"kept": True}]}}, **changes}


# {
#   責務: [request: 既存物理の基準数値へ明示状態一覧/耐性/付与判定値を追加します]
#   処理: [1: 個体やAIを持たない独立した数値要求を作ります]
#   引数: [changes: ケース別の能力/資源/状態/判定値を上書きする値]
#   戻り値: [result: 純粋統合予測の要求（dict）]
# }
def request(**changes):
    return {**physical.PhysicalSkillQuoteTests.quote_request(), "status_effects": ["poison"],
            "status_resistance_level": "normal", "status_roll": 0.2, **changes}


# {
#   責務: [StatusPhysicalBoundaryTests: 専用予測が既存数値/状態契約を共用し、実資源/予約/AI/画面から分離するか確認します]
#   フィールド: []
# }
class StatusPhysicalBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_uses_existing_rules_without_gameplay_or_io: 計算の共用と純粋な依存境界・従来入口の維持を確認します]
    #   処理: [1: 禁止依存/規則重複と、通常物理の付与キー未対応をソースから確認します]
    #   引数: [self: 予測の責務境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_uses_existing_rules_without_gameplay_or_io(self):
        root = fixture.godot_fixture.ROOT / "gdscript"
        source = (root / "engine/status_physical_skill_contract.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "RandomNumberGenerator", "randf(", "battle_session",
                          "res://application/", "res://data/", "res://ui/", "MULTIPLIERS", ".pay_mp(", ".take_damage("):
            self.assertNotIn(forbidden, source)
        self.assertIn("Physical.quote_damage(", source)
        self.assertIn("Status.quote_application(", source)
        self.assertNotIn("status_effect", (root / "engine/physical_skill_contract.gd").read_text(encoding="utf-8").split("const QUOTE_FIELDS")[0])


# {
#   責務: [StatusPhysicalTests: 専用要求/保存ダミー・読取専用データ・実Python/Godot比較を所有します]
#   フィールド: [
#     folder: 共用fixtureの要求/保存ダミー領域（Path）
#     saved_files: 毎起動後にbyte保持を確認する五種類の保存ダミー（list[Path]）
#     content: 正規JSONを読取専用で参照するチェックアウト（Path）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for status physical predictions")
class StatusPhysicalTests(unittest.TestCase):
    # {
    #   責務: [setUp: 共用保存ダミーを作り、正規JSONを検証終了時のbyte照合対象にします]
    #   処理: [1: 専用領域へ委譲し、正規JSONの開始時ハッシュと終了時比較を登録します]
    #   引数: [self: 比較環境と原本保持確認の所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        fixture.StatusCureQuoteTests.setUp(self)
        self.content = fixture.godot_fixture.ROOT
        hashes = {path: hashlib.sha256(path.read_bytes()).digest() for path in (self.content / "data").rglob("*.json")}
        self.addCleanup(self.check_canonical, hashes)

    # {
    #   責務: [check_canonical: 正規JSONが検証前のbyteのままかを終了時に確認します]
    #   処理: [1: 登録済みJSONのハッシュを再取得して開始前と比較します]
    #   引数: [
    #     self: 正規データの保持を確認するテストケース
    #     hashes: 開始前のJSONパス別ハッシュ（dict）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def check_canonical(self, hashes):
        self.assertEqual(hashes, {path: hashlib.sha256(path.read_bytes()).digest() for path in hashes})

    # {
    #   責務: [observe: 専用区分で共用の実Godot起動/診断/要求/保存ダミー保持へ委譲します]
    #   処理: [1: 専用コピー要求へstatus_physical=trueを加え、実観測を取得します]
    #   引数: [
    #     self: 専用領域の所有者
    #     payload: casesまたは性能条件（dict）
    #   ]
    #   戻り値: [result: 診断/原本保持を確認したGodot観測（dict）]
    # }
    def observe(self, payload):
        return fixture.StatusCureQuoteTests.run_probe(self, {**copy.deepcopy(payload), "status_physical": True})

    # {
    #   責務: [python_attack: 状態付与をmock化せず、明示乱数だけを固定して実Python攻撃を比較します]
    #   処理: [1: 独立個体へ実攻撃を行い、HP/付与/乱数要否とレコード/AI/要求不変を確認します]
    #   引数: [
    #     self: 読取専用の正規JSONを参照するテストケース
    #     skill: 比較する対応物理/状態定義（dict）
    #     values: 補正済み防御/HP/状態/耐性と明示乱数（dict）
    #     base_defense: Python個体が状態補正を行う前の基礎防御力。予測入力とは区別します（int）
    #   ]
    #   戻り値: [result: 実dealt/残HP/状態一覧/付与乱数要否（dict）]
    # }
    def python_attack(self, skill, values, base_defense=50):
        # 保存/学習を行わず、正規データ読取と独立個体の再構築は共用fixtureへ任せます。
        ally, enemy = normal.member("ally", hp=1000), normal.member("enemy", hp=max(1, values["target_hp"]))
        ally["stats"]["attack"] = values["attack"]
        enemy["stats"]["defense"] = base_defense
        enemy["hp"] = values["target_hp"]
        engine = turn.GDScriptTurnTests.engine(self, [ally], [enemy])
        actor, target = engine.allies[0], engine.enemies[0]
        actor.attack_multiplier = values.get("attack_multiplier", 1)
        target.guard = values.get("guard", 1)
        target.status_effects = copy.deepcopy(values["status_effects"])
        target.status_resistances = {skill["status_effect"].get("id", "").strip(): values.get("status_resistance_level", "normal")}
        actor.equipment = {"skill_modifiers": {skill["id"]: {"power_multiplier": values.get("power_multiplier", 1)}},
                           "fixed_bonus_damage": values.get("fixed_bonus_damage", 0)}
        preserved = copy.deepcopy([actor.record, target.record, skill, values])
        engine.learning.learn = mock.Mock()
        engine.rng = mock.Mock()
        engine.rng.random.side_effect = [values["critical_roll"], values.get("status_roll")]
        engine.rng.uniform.return_value = values["variance"]
        engine._attack(actor, target, skill, allow_counter=False)
        engine.learning.learn.assert_not_called()
        self.assertEqual([actor.record, target.record, skill, values], preserved)
        return {"dealt": values["target_hp"] - target.hp, "remaining_hp": target.hp,
                "status_effects": target.status_effects, "roll_required": engine.rng.random.call_count == 2}

    # {
    #   責務: [test_nonlethal_gate_and_numeric_status_rules_match_python: 会心/防御/装備・致死・状態/耐性/rollの予測を実Pythonへ照合します]
    #   処理: [1: 直積ケースのダメージと付与を比較し、原本/返却ネスト独立性とMP予測を確認します]
    #   引数: [self: 統合予測の数値互換を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_nonlethal_gate_and_numeric_status_rules_match_python(self):
        cases = []
        for hp, critical, resistance, roll, effects, guard in itertools.product(
            (0, 1, 1000), (0, 1 / 16), ("normal", "weak", "immune"), (0, 0.4, 0.9),
            ([], ["bleeding"], ["poison"]), (1, 0.5)
        ):
            values = request(target_hp=hp, critical_roll=critical, status_resistance_level=resistance,
                             status_roll=roll, status_effects=effects, guard=guard, power_multiplier=1.1,
                             fixed_bonus_damage=3, attack_multiplier=1.3)
            # 予測APIへ補正済み防御を渡し、Python個体が行う既存状態補正を二重に適用しません。
            values["defense"] = max(0, int(50 * status_stat_multiplier(effects, "defense")))
            cases.append({"operation": "quote", "definition": definition(), "request": values})
        actual = self.observe({"cases": cases})["results"]
        self.assertEqual(len(actual), len(cases))
        for case, observed in zip(cases, actual):
            with self.subTest(case=case):
                expected = self.python_attack(case["definition"], case["request"])
                result = observed["result"]
                self.assertTrue(result["ok"], result)
                self.assertEqual(result["scope"], "status_physical_skill_quote")
                for field in ("dealt", "remaining_hp"):
                    self.assertEqual(result["physical"][field], expected[field])
                self.assertEqual(result["physical"]["remaining_mp"], case["request"]["current_mp"] - 3)
                self.assertEqual(result["status"]["resulting_status_effects"], expected["status_effects"])
                self.assertEqual(result["status"]["roll_required"], expected["roll_required"])
                self.assertEqual(result["status_eligible"], expected["dealt"] > 0 and expected["remaining_hp"] > 0)
                self.assertTrue(observed["input_preserved"] and observed["result_independent"])

    # {
    #   責務: [test_preparation_roll_rules_and_lethal_roll_validation: 非致死準備では必要判定を返し、致死では不要とし、不正指定値は常に拒否します]
    #   処理: [1: 準備/予測のroll条件と欠落/不正、状態なし/重複/無効を確認します]
    #   引数: [self: 判定準備と結果予測の区別を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_preparation_roll_rules_and_lethal_roll_validation(self):
        cases = []
        for hp, effects, resistance in itertools.product((1, 1000), ([], ["bleeding"]), ("normal", "immune")):
            values = request(target_hp=hp, status_effects=effects, status_resistance_level=resistance)
            values.pop("status_roll")
            cases += [{"operation": "prepare_quote", "definition": definition(), "request": values},
                      {"operation": "quote", "definition": definition(), "request": values}]
        results = self.observe({"cases": cases})["results"]
        self.assertEqual(len(results), len(cases))
        for index in range(0, len(cases), 2):
            prepared, quoted = results[index]["result"], results[index + 1]["result"]
            self.assertTrue(prepared["ok"], prepared)
            if prepared["status"]["roll_required"]:
                self.assertEqual(quoted["reason"], "missing_status_apply_roll")
            else:
                self.assertTrue(quoted["ok"] and not quoted["status"]["applied"])
        bad = [{"operation": "quote", "definition": definition(), "request": request(target_hp=1, status_roll=value)}
               for value in (-1, 1, True, [], {}, "0")]
        bad.append({"operation": "prepare_quote", "definition": definition(), "request": request(status_roll=None)})
        for observed in self.observe({"cases": bad})["results"]:
            self.assertFalse(observed["result"]["ok"])

    # {
    #   責務: [test_catalog_defaults_rejection_and_canonical_coverage: 付与定義を保存した独立準備・重複/不正拒否・正規データの未対応範囲を確認します]
    #   処理: [1: MODの既定値と選択を確認し、従来物理入口を緩めず正規スキルのbyteを保持します]
    #   引数: [self: 定義選択と対応範囲を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_catalog_defaults_rejection_and_canonical_coverage(self):
        skill = definition(mp_cost="3")
        catalog = {"schema_version": 1, "skills": [{"id": "unselected", "kind": "magic", "extra": False}, skill]}
        cases = [{"operation": "prepare", "document": catalog, "skill_id": skill["id"]}]
        cases.append({"operation": "prepare", "document": {"schema_version": 1, "skills": [skill, skill]}, "skill_id": skill["id"]})
        cases += [{"operation": "prepare", "document": catalog, "skill_id": value} for value in (None, False, 0, "", "missing")]
        observed = self.observe({"cases": cases})["results"]
        self.assertEqual(len(observed), len(cases))
        self.assertTrue(observed[0]["result"]["ok"])
        prepared = observed[0]["result"]["skill"]
        self.assertEqual(prepared["status_effect"], skill["status_effect"])
        self.assertEqual((prepared["mp_cost"], prepared["power"], prepared["critical_multiplier"]), (3, 1, 1))
        self.assertTrue(observed[0]["input_preserved"] and observed[0]["result_independent"])
        self.assertTrue(all(not result["result"]["ok"] for result in observed[1:]))
        canonical = json.loads((self.content / "data/skills/skills.json").read_text(encoding="utf-8"))
        self.assertFalse(any("status_effect" in row for row in canonical["skills"]))
        canonical_cases = [{"operation": "prepare", "document": canonical, "skill_id": identifier}
                           for identifier in ("body_bash", "roll", "poke")]
        for row in self.observe({"cases": canonical_cases})["results"]:
            self.assertEqual(row["result"]["reason"], "status_effect_required")

    # {
    #   責務: [test_unknown_invalid_native_values_and_mp_priority: 不正な定義/数値/状態/判定値を部分成功なしで拒否し、MP不足の拒否順を保持します]
    #   処理: [1: false/0/空の未知キーとnative非JSON値・循環を指定し、診断なし拒否/要求保持を確認します]
    #   引数: [self: 厳密拒否と安全なコピーを確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_unknown_invalid_native_values_and_mp_priority(self):
        cases = [{"operation": "quote", "definition": value, "request": request()} for value in (None, False, [], {})]
        cases += [{"operation": "quote", "definition": definition(status_effect=value), "request": request()} for value in (None, False, [], 0)]
        cases += [{"operation": "quote", "definition": definition(**{field: value}), "request": request()}
                  for field, value in itertools.product(("element", "target", "self_damage_ratio", "mode"), (False, 0, [], {}))]
        cases += [{"operation": "quote", "definition": definition(), "request": request(**{field: value})}
                  for field, value in itertools.product(("effect", "applied", "mode", "mp_cost", "roll"), (False, 0, [], {}))]
        for target, field, value in itertools.product(("effect", "request"), ("metadata",), ("nan", "inf", "object", "cycle", "non_string_key")):
            cases.append({"operation": "quote", "definition": definition(), "request": request(),
                          "special": {"target": target, "field": field if target == "effect" else "attack", "value": value}})
        for value in ("nan", "inf", "object", "cycle"):
            cases.append({"operation": "quote", "definition": definition(), "request": request(target_hp=1),
                          "special": {"target": "request", "field": "status_roll", "value": value}})
        for value in ("nan", "inf", "object", "cycle"):
            cases.append({"operation": "prepare", "document": {"schema_version": 1, "skills": [definition()]}, "skill_id": "mod_status_hit",
                          "special": {"field": "metadata", "value": value}})
        for observed in self.observe({"cases": cases})["results"]:
            self.assertFalse(observed["result"]["ok"], observed)
            self.assertNotIn("physical", observed["result"])
            self.assertTrue(observed["input_preserved"] and observed["result_independent"])
        shortage = {"operation": "quote", "definition": definition(), "request": request(current_mp=2, status_effects=False, status_roll=True)}
        self.assertEqual(self.observe({"cases": [shortage]})["results"][0]["result"]["reason"], "insufficient_mp")

    # {
    #   責務: [test_benchmark_checks_fixed_nonlethal_damage_and_status_success: 性能検査は実予測/原本/非致死/付与成功を固定期待値で確認します]
    #   処理: [1: 少量測定は通過し、高速拒否/欠落/対象死亡/状態不成功/原本改変を排除します]
    #   引数: [self: 性能結果の実条件を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_benchmark_checks_fixed_nonlethal_damage_and_status_success(self):
        result = self.observe({"performance": True, "iterations": 20, "samples": 3, "warmup": 2})
        folder = self.content / "tools/performance-check/script"
        shared_spec = importlib.util.spec_from_file_location("check_gdscript_status_cure", folder / "check_gdscript_status_cure.py")
        shared = importlib.util.module_from_spec(shared_spec)
        shared_spec.loader.exec_module(shared)
        spec = importlib.util.spec_from_file_location("status_physical_checker", folder / "check_gdscript_status_physical.py")
        module = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {"check_gdscript_status_cure": shared}):
            spec.loader.exec_module(module)
        checker = module.StatusPhysicalBenchmark("unused", argparse.Namespace(iterations=20, samples=3, warmup=2))
        self.assertTrue(checker.valid_result(result), result)
        for field, value in (("definition", {}), ("request", {}), ("quote", {}), ("input_preserved", False),
                             ("microseconds", -1), ("microseconds", 3001), ("iterations", 19)):
            changed = copy.deepcopy(result)
            changed[field] = value
            self.assertFalse(checker.valid_result(changed), field)
        for field, value in (("remaining_hp", 0), ("dealt", 0), ("remaining_mp", 100)):
            changed = copy.deepcopy(result)
            changed["quote"]["physical"][field] = value
            self.assertFalse(checker.valid_result(changed), field)
