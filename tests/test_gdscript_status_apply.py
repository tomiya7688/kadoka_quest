"""状態一件の付与予測を実GodotとPython正本で比較します。実セーブは使いません。"""
# {
#   責務: [test_gdscript_status_apply: 付与の確率/耐性/重複/明示判定/拒否と原本・保存ダミー不変を確認します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import base64
from contextlib import redirect_stdout
import importlib.util
import io
import itertools
import json
from types import SimpleNamespace
import unittest

import test_battle_status_cure as python_fixture
import test_gdscript_roster as godot_fixture
import test_gdscript_status_cure as cure_fixture
from kadoka_quest.core.status_effects import status_apply_chance


# {
#   責務: [StatusApplyBoundaryTests: 純粋付与が実資源/状態保持/保存/AI/乱数生成へ依存しないことを確認します]
#   フィールド: []
# }
class StatusApplyBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_pure_dependency_boundary: 付与予測と共用状態形式検査の禁止依存をソースから確認します]
    #   処理: [1: I/O/UI/AI/Session/実資源/乱数生成の依存が二つの純粋ファイルにないことを確認します]
    #   引数: [self: 純粋契約の依存境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_pure_dependency_boundary(self):
        for filename in ("status_apply_contract", "status_effect_contract"):
            source = (godot_fixture.ROOT / f"gdscript/engine/{filename}.gd").read_text(encoding="utf-8")
            for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                              "battle_session", "RandomNumberGenerator", "randf(", ".pay_mp(", ".heal("):
                self.assertNotIn(forbidden, source)


# {
#   責務: [StatusApplyQuoteTests: 独立した要求領域と実Godot/Pythonの付与比較を所有します]
#   フィールド: [
#     folder: 共用fixtureが作る専用要求/保存ダミー領域（Path）
#     saved_files: 毎起動後にbyte不変を確認する五種類の保存ダミー（list[Path]）
#   ]
# }
@unittest.skipUnless(godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real status-apply probes")
class StatusApplyQuoteTests(unittest.TestCase):
    setUp = cure_fixture.StatusCureQuoteTests.setUp

    # {
    #   責務: [observe: 共用実Godot起動fixtureへ付与専用区分を渡し、保存ダミーと要求のbyte不変も検査します]
    #   処理: [1: ケース一覧または性能条件を付与プローブ区分へ指定して実結果を返します]
    #   引数: [
    #     self: 専用領域と保存ダミーを持つテストケース
    #     payload: casesまたは性能条件を指定する辞書（dict）
    #   ]
    #   戻り値: [result: 診断/ファイル不変を確認済みのGodot観測結果（dict）]
    # }
    def observe(self, payload):
        return cure_fixture.StatusCureQuoteTests.run_probe(self, {"status_apply": True, **payload})

    # {
    #   責務: [case: 他ケースとコンテナを共有しない付与要求を作ります]
    #   処理: [1: effectとstatus_effectsを深くコピーし、耐性と判定値を明示します]
    #   引数: [
    #     effect: chance等を含む新規状態定義（dict）
    #     effects: 現在付与済みの順序付き状態一覧（list）
    #     resistance: 新規状態に対応する耐性名（str）
    #     roll: 明示判定値。Noneは未指定です
    #   ]
    #   戻り値: [result: quote操作と独立したrequestの辞書（dict）]
    # }
    @staticmethod
    def case(effect, effects, resistance="normal", roll=0):
        return {"operation": "quote", "request": {"effect": copy.deepcopy(effect),
                "status_effects": copy.deepcopy(effects), "resistance_level": resistance, "roll": roll}}

    # {
    #   責務: [python_result: コピー個体へ実Python付与を実行し、結果一覧/成功名/乱数要否を観測します]
    #   処理: [1: 実_try_apply_statusを固定乱数で呼び、原要求・個体記録/AI・HPMPの不変を確認します]
    #   引数: [
    #     self: 正本の副作用範囲を検査するテストケース
    #     request: 型検査済み互換範囲の効果/一覧/耐性/roll（dict）
    #   ]
    #   戻り値: [result: Godotと比較するapplied/applied_name/roll_required/resulting_status_effects（dict）]
    # }
    def python_result(self, request):
        before = copy.deepcopy(request)
        values = [] if request.get("roll") is None else [request["roll"]]
        engine = python_fixture.make_engine(values)
        target = python_fixture.make_combatant("target", [], status_effects=copy.deepcopy(request["status_effects"]))
        identifier = request["effect"].get("id", "").strip()
        target.status_resistances = {identifier: request.get("resistance_level", "normal")}
        target.record.ai["kept"] = {"deck": [1, 2]}
        record_before = copy.deepcopy(target.record)
        resources = (target.hp, target.mp)
        # 状態の付与・重複・乱数要否をmockへ置換せず、実Pythonの処理を比較します。
        applied = engine._try_apply_status(target, request["effect"])
        name = None
        if applied:
            name = request["effect"].get("display_name") or identifier
        self.assertEqual(request, before)
        self.assertEqual(target.record, record_before)
        self.assertEqual((target.hp, target.mp), resources)
        return {"applied": applied, "applied_name": name,
                "roll_required": engine.rng.random_calls == 1, "resulting_status_effects": target.status_effects}

    # {
    #   責務: [test_probability_resistance_duplicate_and_metadata_match_python: 耐性六段階/禁止値/未知値・重複・確率境界と拡張情報を正本に照合します]
    #   処理: [1: 正常型の直積ケースを実Godot/Pythonで比較し、入力と深い返却コピーの独立性を確認します]
    #   引数: [self: 互換範囲の付与予測を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_probability_resistance_duplicate_and_metadata_match_python(self):
        decks = [[], ["poison"], [{"id": "bleeding", "metadata": {"deck": [1]}}],
                 ["bleeding"], [{"id": " bleeding "}], ["sleep", {"id": "lock", "removable": False}]]
        cases = [self.case({"id": " bleeding ", "display_name": "出血", "chance": chance,
                            "metadata": {"deck": [1, {"kept": [True, None]}]}}, deck, resistance, roll)
                 for chance, deck, resistance, roll in itertools.product(
                     (-1, 0, 0.4, 1, 2, "0.4"), decks,
                     ("very_weak", "weak", "normal", "resist", "strong", "immune", "absorb", "reflect", "mod", ""),
                     (0, 0.2, 0.4, 0.5, 0.999999))]
        observations = self.observe({"cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        for case, observation in zip(cases, observations):
            with self.subTest(request=case["request"]):
                result = observation["result"]
                self.assertTrue(result["ok"], result)
                self.assertEqual({key: result[key] for key in ("applied", "applied_name", "roll_required", "resulting_status_effects")},
                                 self.python_result(case["request"]))
                self.assertEqual(result["scope"], "status_apply_quote")
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_defaults_missing_id_names_and_roll_requirements: 定義省略値・表示名・ID欠落と判定不要/必要を確認します]
    #   処理: [1: 省略/空ID/確率0/重複/無効と確率1を正本で比較し、必要roll欠落だけを拒否します]
    #   引数: [self: 省略値と判定要否を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_defaults_missing_id_names_and_roll_requirements(self):
        cases = [self.case(effect, [], roll=roll) for effect, roll in (
            ({}, None), ({"id": " \t ", "chance": 1}, None), ({"id": "mod"}, None),
            ({"id": "mod", "chance": -1}, None), ({"id": "mod", "chance": 1}, 0),
            ({"id": "\u3000\u00a0mod\u0085", "chance": 1}, 0),
            ({"id": "mod", "display_name": "", "removable": False, "chance": 1}, 0))]
        cases += [self.case({"id": "mod", "chance": 1}, ["mod"], roll=None),
                  self.case({"id": "mod", "chance": 1}, [], "immune", None)]
        for case, observed in zip(cases, self.observe({"cases": cases})["results"]):
            result = observed["result"]
            self.assertTrue(result["ok"], result)
            self.assertEqual({key: result[key] for key in ("applied", "applied_name", "roll_required", "resulting_status_effects")},
                             self.python_result(case["request"]))
        missing = self.case({"id": "mod", "chance": 1}, [], roll=None)
        self.assertEqual(self.observe({"cases": [missing]})["results"][0]["result"],
                         {"ok": False, "reason": "missing_status_apply_roll"})
        missing["operation"] = "prepare"
        missing["request"].pop("roll")
        prepared = self.observe({"cases": [missing]})["results"][0]
        self.assertTrue(prepared["result"]["roll_required"])
        self.assertTrue(prepared["input_preserved"])
        self.assertTrue(prepared["result_independent"])
        # 同値rollは失敗し、確率1でも判定値が必要です。
        equal = self.case({"id": "mod", "chance": 0.4}, [], roll=0.4)
        self.assertFalse(self.observe({"cases": [equal]})["results"][0]["result"]["applied"])

    # {
    #   責務: [test_malformed_requests_and_native_values_fail_without_partial_result: 型/未知要求/非有限/非JSON/循環/深さの不正を部分成功なしで拒否します]
    #   処理: [1: 不正要求とnative値を実Godotへ渡し、全拒否と原本不変を確認します]
    #   引数: [self: 厳密な拒否境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_malformed_requests_and_native_values_fail_without_partial_result(self):
        cases = [{"operation": "quote", "request": request} for request in (None, [], {}, {"effect": {}})]
        for field, values in (("effect", (None, [], "poison")),
                              ("status_effects", (None, {}, [None], [[]], [1])),
                              ("resistance_level", (None, True, 1, {}, [])),
                              ("roll", (True, "0", -1, 1, 2, {}, []))):
            for value in values:
                case = self.case({"id": "mod", "chance": 1}, [])
                case["request"][field] = value
                cases.append(case)
        for field, values in (("id", (None, True, 1, [])), ("display_name", (None, True, 1, {})),
                              ("removable", (None, "false", 0, 1)),
                              ("chance", (None, True, [], {}, "nan", "inf", "no", 2**53))):
            for value in values:
                cases.append(self.case({"id": "mod", "chance": 1, field: value}, []))
        for field, value in itertools.product(("all_targets", "target", "duration", "remaining_status_effects"), (False, 0, "", [], {})):
            case = self.case({"id": "mod", "chance": 1}, [])
            case["request"][field] = value
            cases.append(case)
        for target, field, value in itertools.product(("effect", "request"), ("chance", "roll"), ("nan", "inf", "object")):
            if (target, field) not in (("effect", "chance"), ("request", "roll")):
                continue
            case = self.case({"id": "mod", "chance": 1}, [])
            case["special"] = [{"target": target, "field": field, "value": value}]
            cases.append(case)
        for value in ("nan", "inf", "object", "non_string_key"):
            case = self.case({"id": "mod", "chance": 1}, [])
            case["special"] = [{"target": "effect", "field": "metadata", "value": value}]
            cases.append(case)
        cyclic = self.case({"id": "mod", "chance": 1}, [])
        cyclic["special"] = "cycle"
        cases.append(cyclic)
        nested = "leaf"
        for _ in range(31):
            nested = [nested]
        cases.append(self.case({"id": "mod", "chance": 1, "metadata": nested}, []))
        for observed in self.observe({"cases": cases})["results"]:
            with self.subTest(result=observed):
                self.assertFalse(observed["result"]["ok"])
                self.assertEqual(set(observed["result"]), {"ok", "reason"})
                self.assertTrue(observed["input_preserved"])
        # 判定不要でも指定済み不正rollを黙って受理しません。
        for effect in ({}, {"id": "mod", "chance": 0}):
            invalid = self.case(effect, [], roll=True)
            self.assertEqual(self.observe({"cases": [invalid]})["results"][0]["result"]["reason"],
                             "invalid_status_apply_roll")

    # {
    #   責務: [test_native_roll_and_depth_32_are_accepted: JSON丸めに依存しない1未満rollと、許容深さ32の拡張情報を受理します]
    #   処理: [1: native判定値と上限ネストで付与成功/コピー独立性を確認します]
    #   引数: [self: 正常入力の上限を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_native_roll_and_depth_32_are_accepted(self):
        nested = "leaf"
        for _ in range(30):
            nested = [nested]
        case = self.case({"id": "mod", "chance": 1, "metadata": nested}, [])
        case["special"] = [{"field": "roll", "value": "next_below_one"}]
        observed = self.observe({"cases": [case]})["results"][0]
        self.assertTrue(observed["result"]["applied"])
        self.assertTrue(observed["result_independent"])

    # {
    #   責務: [test_canonical_species_resistance_and_no_standard_infliction_skill: 正規四種の出血無効と現行スキルの付与定義なしを確認します]
    #   処理: [1: 正規JSONをread-onlyで読み、出血確率が0かつ判定不要の予測を確認します]
    #   引数: [self: 正規データの対応範囲を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_canonical_species_resistance_and_no_standard_infliction_skill(self):
        cases = []
        for species in ("ghost", "maru", "kadoka", "metal_slime"):
            path = godot_fixture.ROOT / f"data/species/{species}/species.json"
            definition = json.loads(path.read_text(encoding="utf-8-sig"))
            resistance = definition["status_resistances"]["bleeding"]
            self.assertEqual(resistance, "immune")
            cases.append(self.case({"id": "bleeding", "chance": 1}, [], resistance, None))
        skills = json.loads((godot_fixture.ROOT / "data/skills/skills.json").read_text(encoding="utf-8-sig"))["skills"]
        self.assertFalse(any("status_effect" in skill for skill in skills))
        for observed in self.observe({"cases": cases})["results"]:
            self.assertEqual((observed["result"]["apply_chance"], observed["result"]["roll_required"],
                              observed["result"]["applied"]), (0, False, False))
        self.assertEqual(status_apply_chance(0.4, "weak"), 0.5)

    # {
    #   責務: [test_checker_rejects_fast_failed_or_incomplete_predictions: 性能CLIが時間だけ良い拒否/欠落/付与不一致を通過させないことを確認します]
    #   処理: [1: 実Godotの正常計測結果と改変コピーをCLIへ渡し、正常だけ成功0になることを確認します]
    #   引数: [self: 性能検査の結果照合を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_checker_rejects_fast_failed_or_incomplete_predictions(self):
        path = godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_status_cure.py"
        spec = importlib.util.spec_from_file_location("status_apply_performance", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        benchmark = module.StatusCureBenchmark(str(godot_fixture.GODOT), SimpleNamespace(
            iterations=100, samples=3, warmup=10, status_apply=True))
        result = self.observe({"performance": True, "iterations": 100, "samples": 3, "warmup": 10})
        invalid = [{"ok": False, "reason": "rejected"}, {}, {**result, "input_preserved": False}]
        for field, value in (("applied", False), ("apply_chance", 0), ("resulting_status_effects", [])):
            changed = copy.deepcopy(result)
            changed["quote"][field] = value
            invalid.append(changed)
        changed = copy.deepcopy(result)
        changed["original_request"]["effect"]["chance"] = 0
        invalid.append(changed)
        # 予測の拒否や欠落を0usの高速な成功に置換しません。
        for observation, expected in [(result, 0), *((value, 1) for value in invalid)]:
            encoded = base64.b64encode(json.dumps(observation).encode()).decode()
            with redirect_stdout(io.StringIO()):
                status = benchmark._check_output("KADOKA_STATUS_CURE_RESULT=" + encoded)
            self.assertEqual(status, expected)

    # {
    #   責務: [test_performance_measures_successful_nonstacking_prediction: 性能プローブが四件の元一覧を保持し、五件目の出血を成功予測することを確認します]
    #   処理: [1: 少量反復で確率0.5/roll0.49・原本保持と付与結果を照合します]
    #   引数: [self: 性能ケースの実結果を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_performance_measures_successful_nonstacking_prediction(self):
        result = self.observe({"performance": True, "iterations": 100, "samples": 3, "warmup": 10})
        self.assertGreaterEqual(result["microseconds"], 0)
        self.assertTrue(result["input_preserved"])
        original = result["original_request"]
        quote = result["quote"]
        self.assertTrue(quote["applied"])
        self.assertEqual((quote["apply_chance"], quote["roll_required"], quote["applied_name"]), (0.5, True, "出血"))
        expected = {**original["effect"], "removable": True}
        expected.pop("chance")
        self.assertEqual(quote["resulting_status_effects"], [*original["status_effects"], expected])
