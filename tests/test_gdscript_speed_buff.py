"""速度強化の定義・抽選前期間・MP予測を実GodotとPython正本で比較します。"""
# {
#   責務: [test_gdscript_speed_buff: ピオラと互換MODの純粋予測・厳密拒否・コピー独立性を検証します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import importlib.util
import itertools
import json
import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import test_gdscript_roster as fixture
import test_gdscript_magic_skill as probe_fixture
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [SpeedBuffBoundaryTests: 速度強化予測にI/O・乱数・実状態更新・画面への接続がないことを確認します]
#   フィールド: []
# }
class SpeedBuffBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_prediction_remains_pure: 予測の依存と未接続境界をソースから確認します]
    #   処理: [1: 禁止依存と更新API・乱数を検出し、Applicationへの未接続を確認します]
    #   引数: [self: 純粋予測の境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_prediction_remains_pure(self):
        # 実行結果だけでは検出しにくい保存・抽選・更新の依存を禁止します。
        source = (fixture.ROOT / "gdscript/engine/speed_buff_contract.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                          "battle_session", "combatant_speed_state", ".pay_mp(", ".apply_multiplier(",
                          "randf(", "randi(", "RandomNumberGenerator"):
            self.assertNotIn(forbidden, source)
        application = (fixture.ROOT / "gdscript/application/battle_session_application.gd").read_text(encoding="utf-8")
        self.assertNotIn("speed_buff_contract", application)


# {
#   責務: [SpeedBuffQuoteTests: 専用一時領域・正規定義・Python期間比較先を所有します]
#   フィールド: [
#     folder: プローブ要求JSONだけを作る専用一時領域（Path）
#     document: 正規スキル一覧の読み取り専用コピー（dict）
#     definition: 正規ピオラ定義の独立コピー（dict）
#     engine: 期間補正の比較だけに使う学習無効のPython BattleEngine
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real speed-buff probes")
class SpeedBuffQuoteTests(unittest.TestCase):
    # {
    #   責務: [setUp: 実セーブと独立したプローブ要求先とPython期間比較先を用意します]
    #   処理: [1: 専用一時領域と正規定義コピーを作り、学習しない期間比較先を初期化します]
    #   引数: [self: 専用領域と比較先の所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        # 比較では既存のモンスター・AI・保存データを読み書きしません。
        temporary = tempfile.TemporaryDirectory(prefix="kadoka-speed-buff-quote-")
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.document = json.loads((fixture.ROOT / "data/skills/skills.json").read_text(encoding="utf-8"))
        self.definition = copy.deepcopy(next(skill for skill in self.document["skills"] if skill["id"] == "piora"))
        self.engine = BattleEngine(GameRepository(fixture.ROOT / "data"), [], [], learning_enabled=False)

    # {
    #   責務: [run_probe: 共用の実Godot起動・診断・要求JSON不変検査へ委譲します]
    #   処理: [1: 共用テスト環境に専用要求を渡し、実行観測を返します]
    #   引数: [
    #     self: 共用プローブが必要とするfolderを所有するテストケース
    #     payload: ケース一覧または性能測定条件（dict）
    #   ]
    #   戻り値: [result: 実Godotの観測結果（dict）]
    # }
    def run_probe(self, payload):
        return probe_fixture.MagicSkillQuoteTests.run_probe(self, payload)

    # {
    #   責務: [quote_case: ケース間で定義を共有しない速度強化要求を作ります]
    #   処理: [1: 独立定義と現在MP要求へケース固有の変更を加えます]
    #   引数: [
    #     self: 正規ピオラ定義の所有者
    #     definition_changes: 期間・倍率・MP消費などの変更（dict）
    #   ]
    #   戻り値: [result: 共用プローブの速度強化quote要求（dict）]
    # }
    def quote_case(self, **definition_changes):
        # ネストした期間配列もコピーし、入力破壊検査をケース間で独立させます。
        return {"operation": "quote", "speed_buff": True,
                "definition": {**copy.deepcopy(self.definition), **definition_changes},
                "request": {"current_mp": 10}}

    # {
    #   責務: [test_canonical_definition_and_period_match_python: 正規ピオラの定義・期間上下限・消費後MPを確認します]
    #   処理: [1: prepareとquoteを実Godotへ渡し、正規データとPython期間抽選の引数を照合します]
    #   引数: [self: 正規ピオラを検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_canonical_definition_and_period_match_python(self):
        cases = [{"operation": "prepare", "speed_buff": True, "document": self.document, "skill_id": "piora"},
                 self.quote_case()]
        observations = self.run_probe({"cases": cases})["results"]
        prepared, quoted = [entry["result"] for entry in observations]
        self.assertTrue(prepared["ok"], prepared)
        self.assertEqual(prepared["skill"], self.definition)
        self.assertEqual(quoted, {"ok": True, "scope": "speed_buff_quote", "skill_id": "piora",
                                 "multiplier": 1.5, "duration": {"mode": "range", "minimum": 3, "maximum": 6},
                                 "target_policy": "lowest_speed_multiplier", "mp_cost": 5, "remaining_mp": 5})
        # 乱数を実行せず、実Pythonの期間補正がrandintへ渡す上下限を照合します。
        for endpoint in (3, 6):
            self.engine.rng = mock.Mock()
            self.engine.rng.randint.return_value = endpoint
            self.assertEqual(self.engine._buff_duration(self.definition), endpoint)
            self.engine.rng.randint.assert_called_once_with(quoted["duration"]["minimum"], quoted["duration"]["maximum"])
        for observation in observations:
            self.assertTrue(observation["input_preserved"])
            self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_mod_period_normalization_matches_python: 有限MOD期間の切捨て・最低一・範囲上限補正をPythonと比較します]
    #   処理: [1: 単値と二要素範囲を実Godotへ渡し、Pythonの期間値または抽選上下限を照合します]
    #   引数: [self: 互換MOD定義を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_mod_period_normalization_matches_python(self):
        periods = [None, 0, -5, 1, 4.9, -2.8, " 4 ", 2**53 - 1, [3, 6], [6, 3], [0, -8],
                   [-1.5, 4.9], [" 2 ", "5"], [2**53 - 1, 1]]
        cases = [self.quote_case(id="mod_haste", duration=value, target="self", speed_multiplier="1.25", mp_cost=" 5 ")
                 for value in periods]
        missing = self.quote_case()
        del missing["definition"]["duration"]
        cases.append(missing)
        observations = self.run_probe({"cases": cases})["results"]
        for case, observation in zip(cases, observations):
            with self.subTest(definition=case["definition"]):
                result = observation["result"]
                self.assertTrue(result["ok"], result)
                self.assertEqual(result["skill_id"], case["definition"]["id"])
                self.assertEqual(result["target_policy"], "self" if "target" in case["definition"] else "lowest_speed_multiplier")
                self.assertEqual(result["multiplier"], float(case["definition"]["speed_multiplier"]))
                self.assertEqual(result["mp_cost"], int(case["definition"]["mp_cost"]))
                self.engine.rng = mock.Mock()
                self.engine.rng.randint.return_value = 1
                duration = self.engine._buff_duration(case["definition"])
                condition = result["duration"]
                raw = case["definition"].get("duration")
                if isinstance(raw, list):
                    self.assertEqual(condition, {"mode": "range", "minimum": max(1, int(raw[0])),
                                                 "maximum": max(1, int(raw[0]), int(raw[1]))})
                    self.engine.rng.randint.assert_called_once_with(condition["minimum"], condition["maximum"])
                elif duration is None:
                    self.assertEqual(condition, {"mode": "untimed", "minimum": None, "maximum": None})
                    self.engine.rng.randint.assert_not_called()
                else:
                    self.assertEqual(condition, {"mode": "fixed", "minimum": duration, "maximum": duration})
                    self.engine.rng.randint.assert_not_called()
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_definition_selection_and_unknown_effects_are_rejected: 不正一覧・重複・未対応効果を部分成功なしで拒否します]
    #   処理: [1: 一覧形式と定義の不正を作り、理由付き失敗と入力不変を確認します]
    #   引数: [self: 一覧選択と対応範囲を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_definition_selection_and_unknown_effects_are_rejected(self):
        # 未対応効果はfalse/0/nullでも捨てずに拒否します。
        cases = [self.quote_case(**{field: value})
                 for field, value in itertools.product(
                     ("attack_multiplier", "aoe", "status", "heal_ratio", "target_all", "element"), (None, False, 0, []))]
        for field, values in {"id": (None, "", True, "attack", "defend"), "display_name": (None, "", 1),
                              "description": (None, 1), "kind": (None, "magic"),
                              "target": (None, "ally", "all", False)}.items():
            cases.extend(self.quote_case(**{field: value}) for value in values)
        for document in (None, [], {}, {"schema_version": True, "skills": [self.definition]},
                         {"schema_version": 2, "skills": [self.definition]},
                         {"schema_version": 1, "skills": []},
                         {"schema_version": 1, "skills": [self.definition, self.definition]}):
            cases.append({"operation": "prepare", "speed_buff": True, "document": document, "skill_id": "piora"})
        for skill_id in (None, "", True, "missing"):
            cases.append({"operation": "prepare", "speed_buff": True, "document": self.document, "skill_id": skill_id})
        for observation in self.run_probe({"cases": cases})["results"]:
            with self.subTest(observation=observation):
                self.assertEqual(set(observation["result"]), {"ok", "reason"})
                self.assertFalse(observation["result"]["ok"])
                self.assertTrue(observation["input_preserved"])

    # {
    #   責務: [test_invalid_numbers_periods_and_requests_are_rejected: 非有限値・精度超過・不正期間と要求を拒否します]
    #   処理: [1: JSON形式不正とnative NaN/Infを注入し、部分成功なしの拒否を照合します]
    #   引数: [self: 数値と要求の厳密性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_numbers_periods_and_requests_are_rejected(self):
        cases = []
        for field, values in {
            "speed_multiplier": (None, False, 0, -1, [], {}, "nan", "inf", 2**53),
            "mp_cost": (None, True, 0, -1, 0.9, "1.5", [], {}, 2**53),
            "duration": (True, False, [], [1], [1, 2, 3], [None, 3], [True, 3], [1, {}],
                         {}, "1.2", "nan", "inf", 2**53, [1, 2**53]),
        }.items():
            cases.extend(self.quote_case(**{field: value}) for value in values)
        for value in (None, True, -1, "10", 1.5, 2**53, [], {}):
            case = self.quote_case()
            case["request"]["current_mp"] = value
            cases.append(case)
        for request in (None, [], {}, {"current_mp": 10, "duration": 3}, {"current_mp": 10, "speed": 1}):
            case = self.quote_case()
            case["request"] = request
            cases.append(case)
        for target, fields in (("definition", ("speed_multiplier", "mp_cost", "duration")), ("request", ("current_mp",))):
            for field, value in itertools.product(fields, ("nan", "inf")):
                case = self.quote_case()
                case["special"] = [{"target": target, "field": field, "value": value}]
                cases.append(case)
        for field in ("speed_multiplier", "mp_cost"):
            case = self.quote_case()
            del case["definition"][field]
            cases.append(case)
        for definition in (None, [], True):
            case = self.quote_case()
            case["definition"] = definition
            cases.append(case)
        for observation in self.run_probe({"cases": cases})["results"]:
            with self.subTest(observation=observation):
                self.assertFalse(observation["result"]["ok"])
                self.assertEqual(set(observation["result"]), {"ok", "reason"})
                self.assertTrue(observation["input_preserved"])

    # {
    #   責務: [test_mp_boundaries_and_existing_contract_rejections: MP境界と既存魔法・回復入口の速度強化拒否を確認します]
    #   処理: [1: 支払可否の境界と契約選択を変え、消費後MPと拒否理由を照合します]
    #   引数: [self: MP予測と入口分離を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_mp_boundaries_and_existing_contract_rejections(self):
        cases = []
        for mp in (0, 4, 5, 5.0, 2**53 - 1):
            case = self.quote_case()
            case["request"]["current_mp"] = mp
            cases.append(case)
        for flag in (None, "heal", "self_damage", "drain_mp"):
            case = self.quote_case()
            del case["speed_buff"]
            if flag:
                case[flag] = True
            cases.append(case)
        for flag in ("heal", "self_damage", "drain_mp"):
            cases.append({**self.quote_case(), flag: True})
        results = [entry["result"] for entry in self.run_probe({"cases": cases})["results"]]
        self.assertEqual([result["reason"] for result in results[:2]], ["insufficient_mp"] * 2)
        self.assertEqual([result["remaining_mp"] for result in results[2:5]], [0, 0, 2**53 - 6])
        for result in results[5:]:
            self.assertFalse(result["ok"])
        for flag in ("heal", "self_damage", "drain_mp"):
            self.assertEqual(self.run_probe({"performance": True, "speed_buff": True, flag: True})["reason"],
                             "invalid_probe_contract")

    # {
    #   責務: [test_performance_probe_and_strict_validator: 実予測の性能観測と、改ざん結果を拒否するCLI検証器を確認します]
    #   処理: [1: 少数回の実測を確認し、独立した合成時間で検証器の形式と失敗条件を検査します]
    #   引数: [self: 性能プローブと検証器を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_performance_probe_and_strict_validator(self):
        # 少数実測は有限の非負時間と正常予測の証拠であり、標準性能CLIの代用ではありません。
        result = self.run_probe({"performance": True, "speed_buff": True, "iterations": 100, "samples": 3, "warmup": 10})
        path = fixture.ROOT / "tools/performance-check/script/check_gdscript_speed_buff.py"
        spec = importlib.util.spec_from_file_location("speed_buff_benchmark", path)
        module = importlib.util.module_from_spec(spec)
        with mock.patch.object(sys, "path", [str(path.parent), *sys.path]):
            spec.loader.exec_module(module)
        self.assertTrue(module.validate_result(result, {"iterations": 100, "samples": 3, "warmup": 10}, check_time=False))
        # 合成時間は検証器の文法検査だけに使用し、速度の実測値として報告しません。
        reference = copy.deepcopy(result)
        reference["microseconds"] = 1000
        configuration = {"iterations": 100, "samples": 3, "warmup": 10}
        self.assertTrue(module.validate_result(reference, configuration))
        for field, value in (("microseconds", float("nan")), ("microseconds", float("inf")),
                             ("microseconds", -1), ("microseconds", True), ("microseconds", 3001),
                             ("iterations", 101), ("input_preserved", False), ("current_mp", 5)):
            changed = {**reference, field: value}
            self.assertFalse(module.validate_result(changed, configuration), changed)
        for field, value in (("ok", False), ("multiplier", True), ("remaining_mp", 10),
                             ("duration", {"mode": "range", "minimum": 1, "maximum": 6}),
                             ("target_policy", "self"), ("unexpected", 0)):
            changed = copy.deepcopy(reference)
            changed["quote"][field] = value
            self.assertFalse(module.validate_result(changed, configuration), changed)
        for changed in (None, {}, {"quote": []}):
            self.assertFalse(module.validate_result(changed, configuration))
