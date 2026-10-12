"""治療付きHP回復の純粋予測を実Python行動と比較します。実保存・AI学習・画面は変更しません。"""
# {
#   責務: [test_gdscript_cure_heal_skill: 回復量・消費MP・一件治療の一致、厳密拒否と保存非変更を検証します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import itertools
import json
import unittest

import test_battle_status_cure as python_fixture
import test_gdscript_status_cure as cure_fixture


# {
#   責務: [CureHealBoundaryTests: 統合予測のI/O/実更新からの独立と、呼出調停/HPだけの数値契約による直接治療計算の未実装を確認します]
#   フィールド: []
# }
class CureHealBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_prediction_remains_separate_from_io_ai_rng_and_session: 統合予測を実更新・AI・乱数生成へ接続しないことを確認します]
    #   処理: [1: 純粋統合予測の禁止依存と、Application/HP数値契約の直接依存がないことを確認します]
    #   引数: [self: 純粋予測の境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_prediction_remains_separate_from_io_ai_rng_and_session(self):
        root = cure_fixture.godot_fixture.ROOT / "gdscript"
        source = (root / "engine/cure_heal_skill_contract.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                          "battle_session", "randf(", "RandomNumberGenerator", ".pay_mp(", ".heal("):
            self.assertNotIn(forbidden, source)
        for name in ("application/field_application", "application/battle_session_application",
                     "engine/heal_skill_contract"):
            self.assertNotIn("cure_heal_skill_contract", (root / f"{name}.gd").read_text(encoding="utf-8"))


# {
#   責務: [CureHealQuoteTests: 保存ダミー・正本定義と、実Godot/実Pythonの治療付き回復比較を所有します]
#   フィールド: [
#     folder: 共用プローブが使う専用要求領域（Path）
#     saved_files: byte不変を確認する個体・AI・items・party・stateのダミーパス（list[Path]）
#     document: 読取専用正本から取得したスキル一覧（dict）
#     definition: 正本spirit_recoverの独立コピー（dict）
#   ]
# }
@unittest.skipUnless(cure_fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real cure-heal probes")
class CureHealQuoteTests(unittest.TestCase):
    # {
    #   責務: [setUp: 共用の保存ダミー領域と正本スキルの独立コピーを用意します]
    #   処理: [1: 共用fixtureで一時領域を作り、正規JSONは読み取りだけで取得します]
    #   引数: [self: 比較用領域・保存ダミー・スキル定義の所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        cure_fixture.StatusCureQuoteTests.setUp(self)
        path = cure_fixture.godot_fixture.ROOT / "data/skills/skills.json"
        self.document = json.loads(path.read_text(encoding="utf-8"))
        self.definition = copy.deepcopy(next(skill for skill in self.document["skills"] if skill["id"] == "spirit_recover"))

    # {
    #   責務: [run_probe: コピーした要求へ統合区分を付け、共用の診断・byte保持検証を呼びます]
    #   処理: [1: 各ケースと性能要求へcure_heal=trueを付け、既存起動検証へ委譲します]
    #   引数: [
    #     self: 専用領域と保存ダミーを持つ所有者
    #     payload: prepare/quoteケース一覧または性能測定条件（dict）
    #   ]
    #   戻り値: [result: 実Godotの観測結果。原本・保存ダミーのbyte不変を検証済みです（dict）]
    # }
    def run_probe(self, payload):
        copied = copy.deepcopy(payload)
        for case in copied.get("cases", []):
            case["cure_heal"] = True
        copied["cure_heal"] = True
        return cure_fixture.StatusCureQuoteTests.run_probe(self, copied)

    # {
    #   責務: [quote_case: 正本定義と資源・状態一覧を独立コピーした統合予測要求を作ります]
    #   処理: [1: MP10/HP50/最大HP100を既定値として、指定変更をコピー要求へ反映します]
    #   引数: [
    #     self: 正本spirit_recoverを持つ所有者
    #     effects: 順序付き状態異常一覧。Noneは空一覧です（list | None）
    #     changes: 既定資源と判定値を置き換える項目（dict）
    #   ]
    #   戻り値: [result: 定義・要求をケース間で共有しないquoteケース（dict）]
    # }
    def quote_case(self, effects=None, **changes):
        request = {"current_mp": 10, "target_hp": 50, "target_max_hp": 100,
                   "status_effects": copy.deepcopy(effects or []), "roll": 0.02}
        request.update(copy.deepcopy(changes))
        return {"operation": "quote", "definition": copy.deepcopy(self.definition), "request": request}

    # {
    #   責務: [python_result: Python正本の実回復行動でHP/MP・治療・判定回数を取得し、元要求と記録/AI保持を確認します]
    #   処理: [
    #     1: コピーした独立戦闘個体と、学習なし・行動選択だけ固定したエンジンを用意します
    #     2: 実_take_actionの回復分岐を呼び、資源・状態・治療ログと乱数回数を取得します
    #   ]
    #   引数: [
    #     self: Python比較を検証するテストケース
    #     case: 正本互換の定義と、有効な資源・状態・判定値のquoteケース（dict）
    #   ]
    #   戻り値: [result: 実Pythonの消費後MP・回復後HP・一件治療・残存一覧・乱数要否（dict）]
    # }
    def python_result(self, case):
        original = copy.deepcopy(case)
        request = case["request"]
        roll = request.get("roll")
        engine = python_fixture.make_engine([] if roll is None else [roll])
        actor = python_fixture.make_combatant("actor", [copy.deepcopy(case["definition"])])
        actor.mp = request["current_mp"]
        actor.stats["mp"] = max(1, actor.mp)
        target = python_fixture.make_combatant("target", [], hp=request["target_hp"],
                                               status_effects=copy.deepcopy(request["status_effects"]))
        target.stats["hp"] = request["target_max_hp"]
        for participant in (actor, target):
            participant.record.ai["kept"] = {"deck": [1, {"nested": [2]}]}
        records = copy.deepcopy((actor.record, target.record))
        # 回復量・MP消費・治療・ログ・乱数回数をmockへ置き換えず、実行動から取得する。
        engine._take_action(actor, [], [target])
        names = [line[len("targetの"):-len("が治った。")]
                 for line in engine.log if line.startswith("targetの") and line.endswith("が治った。")]
        self.assertEqual(case, original)
        self.assertEqual((actor.record, target.record), records)
        self.assertIn(engine.rng.random_calls, (0, 1))
        return {"healed": target.hp - request["target_hp"], "remaining_hp": target.hp,
                "remaining_mp": actor.mp, "mp_cost": request["current_mp"] - actor.mp,
                "cured": bool(names), "cured_name": names[0] if names else None,
                "remaining_status_effects": target.status_effects, "roll_required": engine.rng.random_calls == 1}

    # {
    #   責務: [test_capped_healing_mp_and_single_cure_match_real_python_action: HP0/満HP・最低回復・候補順と確率境界を実Pythonへ合わせます]
    #   処理: [1: 最大HP・現在HP・回復率・確率・状態順序・判定値の組合せを実Godot/Pythonで照合します]
    #   引数: [self: 治療付き回復の互換性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_capped_healing_mp_and_single_cure_match_real_python_action(self):
        locked = {"id": "lock", "removable": False, "metadata": {"deck": [1, {"kept": [False, None]}]}}
        poison = {"id": "poison", "display_name": "毒"}
        decks = [[], [locked], [""], [{}], [locked, poison, "sleep"], [poison, poison]]
        cases = []
        for maximum, position, ratio, chance, effects, roll in itertools.product(
                (1, 19, 100, 1000), ("zero", "near", "full"), (None, 0.03, -0.2, "1.5"),
                (0, 0.03, 1), decks, (0, 0.02, 0.03)):
            hp = {"zero": 0, "near": maximum - 1, "full": maximum}[position]
            case = self.quote_case(effects, target_hp=hp, target_max_hp=maximum, roll=roll,
                                   current_mp=4 if position == "zero" else 10)
            case["definition"]["status_cure_chance"] = chance
            if ratio is None:
                case["definition"].pop("heal_ratio")
            else:
                case["definition"]["heal_ratio"] = ratio
            cases.append(case)
        results = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(results), len(cases))
        for case, observed in zip(cases, results):
            with self.subTest(case=case):
                actual = observed["result"]
                self.assertTrue(actual["ok"], actual)
                self.assertEqual(actual["scope"], "cure_heal_skill_quote")
                self.assertEqual(actual["skill_id"], "spirit_recover")
                for key, expected in self.python_result(case).items():
                    self.assertEqual(actual[key], expected, key)
                self.assertTrue(observed["input_preserved"])
                self.assertTrue(observed["result_independent"])

    # {
    #   責務: [test_candidate_free_quotes_need_no_roll_and_finite_chance_is_clamped: 候補なしの乱数不要と有限確率の0〜1制限を確認します]
    #   処理: [1: 判定値省略・nullと範囲外/文字列確率を実Pythonに照合します]
    #   引数: [self: 任意判定値と確率境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_candidate_free_quotes_need_no_roll_and_finite_chance_is_clamped(self):
        cases = []
        for chance, effects, omitted in itertools.product((-1, 2, "0.03"), ([], [{"removable": False}]), (True, False)):
            case = self.quote_case(effects, roll=None)
            case["definition"]["status_cure_chance"] = chance
            if omitted:
                case["request"].pop("roll")
            cases.append(case)
        for case, observed in zip(cases, self.run_probe({"cases": cases})["results"]):
            with self.subTest(case=case):
                result = observed["result"]
                self.assertTrue(result["ok"], result)
                self.assertEqual(result["cure_chance"], max(0, min(1, float(case["definition"]["status_cure_chance"]))))
                for key, expected in self.python_result(case).items():
                    self.assertEqual(result[key], expected, key)

    # {
    #   責務: [test_prepare_accepts_only_supported_unique_catalog_definition: 正本spirit_recoverの選択と一覧/対応効果の厳密拒否を確認します]
    #   処理: [1: 正本一覧・未知ID・重複ID・非治療回復・不正一覧をprepareへ渡します]
    #   引数: [self: 定義選択を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_prepare_accepts_only_supported_unique_catalog_definition(self):
        cases = [{"operation": "prepare", "document": self.document, "skill_id": skill_id}
                 for skill_id in ("spirit_recover", "small_heal", "healy", "attack", "missing", "", None)]
        duplicate = copy.deepcopy(self.document)
        duplicate["skills"].append(copy.deepcopy(self.definition))
        cases += [{"operation": "prepare", "document": document, "skill_id": "spirit_recover"}
                  for document in (duplicate, {}, {"schema_version": 2, "skills": [self.definition]},
                                   {"schema_version": True, "skills": [self.definition]})]
        observations = self.run_probe({"cases": cases})["results"]
        self.assertEqual(observations[0]["result"]["skill"], self.definition)
        for index, observation in enumerate(observations):
            with self.subTest(index=index):
                self.assertEqual(observation["result"]["ok"], index == 0)
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_unknown_keys_are_rejected_even_when_false_zero_or_empty: 未対応効果/要求を値によらず拒否することを確認します]
    #   処理: [1: 定義・要求に未知キーを加え、部分回復結果なしの拒否を照合します]
    #   引数: [self: 未対応キーの拒否を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_unknown_keys_are_rejected_even_when_false_zero_or_empty(self):
        cases = []
        for target, field, value in itertools.product(("definition", "request"),
                                                      ("revive", "field_only", "power", "cure_chance"),
                                                      (False, 0, [], {}, "", None)):
            case = self.quote_case()
            case[target][field] = value
            cases.append(case)
        for case, observation in zip(cases, self.run_probe({"cases": cases})["results"]):
            with self.subTest(case=case):
                result = observation["result"]
                self.assertFalse(result["ok"])
                self.assertIn(result["reason"], ("unsupported_cure_heal_skill", "unsupported_cure_heal_request"))
                self.assertNotIn("healed", result)
                self.assertTrue(observation["input_preserved"])

    # {
    #   責務: [test_invalid_numbers_states_and_missing_roll_do_not_return_partial_success: 不正定義・資源・状態・判定値を部分成功なしで拒否します]
    #   処理: [1: 型・数値・精度・状態形式とネイティブ非有限値の不正ケースを統合予測へ渡します]
    #   引数: [self: 予測の厳密拒否を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_numbers_states_and_missing_roll_do_not_return_partial_success(self):
        cases = []
        values = {"definition": {"status_cure_chance": [None, True, "nan", "inf", [], 2**53],
                                  "heal_ratio": [True, "nan", 2**53], "mp_cost": [0, -1, False, "4.5"],
                                  "kind": ["magic", "buff"], "id": ["", "attack", {}],
                                  "display_name": ["", False, []], "description": [None, {}, []]},
                  "request": {"current_mp": [True, "10", -1, 4.5, 2**53], "target_hp": [-1, 101, True, "50"],
                              "target_max_hp": [0, -1, True, "100"], "roll": [-0.1, 1, True, "0.02"],
                              "status_effects": [None, {}, [False], [{"removable": 1}], [{"id": 1}]]}}
        for target, fields in values.items():
            for field, invalid_values in fields.items():
                for value in invalid_values:
                    case = self.quote_case(["poison"])
                    case[target][field] = value
                    cases.append(case)
        for target, field in (("definition", "status_cure_chance"), ("definition", "heal_ratio"),
                              ("request", "current_mp"), ("request", "roll")):
            for value in ("nan", "inf", "object"):
                case = self.quote_case(["poison"])
                case["special"] = [{"target": target, "field": field, "value": value}]
                cases.append(case)
        for field in ("status_cure_chance", "mp_cost"):
            case = self.quote_case(["poison"])
            case["definition"].pop(field)
            cases.append(case)
        for field in ("current_mp", "target_hp", "target_max_hp", "status_effects", "roll"):
            case = self.quote_case(["poison"])
            case["request"].pop(field)
            cases.append(case)
        for target in ("definition", "request"):
            case = self.quote_case()
            case[target] = []
            cases.append(case)
        cyclic_case = self.quote_case()
        cyclic_case["operation"] = "quote_cyclic_definition"
        cases.append(cyclic_case)
        for case, observation in zip(cases, self.run_probe({"cases": cases})["results"]):
            with self.subTest(case=case):
                result = observation["result"]
                self.assertFalse(result["ok"], result)
                self.assertNotIn("healed", result)
                self.assertNotIn("remaining_mp", result)
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_numeric_definition_conversion_and_finite_chance_clamp_match_python: 定義の数値文字列・MP切捨てと候補ありの確率制限を確認します]
    #   処理: [1: MP消費4.9/文字列4と確率負値/1超を実Pythonへ照合し、回復積の精度超過は拒否します]
    #   引数: [self: 数値変換の互換範囲を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_numeric_definition_conversion_and_finite_chance_clamp_match_python(self):
        cases = []
        for cost, chance in itertools.product((4.9, "4"), (-1, 2, "0.03")):
            case = self.quote_case(["poison"], current_mp=4.0, target_hp=50.0, target_max_hp=100.0)
            case["definition"].update(mp_cost=cost, heal_ratio="0.03", status_cure_chance=chance)
            cases.append(case)
        for case, observation in zip(cases, self.run_probe({"cases": cases})["results"]):
            with self.subTest(case=case):
                self.assertTrue(observation["result"]["ok"])
                for key, expected in self.python_result(case).items():
                    self.assertEqual(observation["result"][key], expected, key)
        overflow = self.quote_case([], target_hp=100, target_max_hp=100)
        overflow["definition"]["heal_ratio"] = 9007199254740991
        result = self.run_probe({"cases": [overflow]})["results"][0]["result"]
        self.assertEqual(result, {"ok": False, "reason": "invalid_heal_numbers"})

    # {
    #   責務: [test_mp_shortage_precedes_cure_request_validation: MP不足時は治療判定値や状態不正より先に不足を拒否します]
    #   処理: [1: MP3と候補あり/不正状態・判定値省略を組み合わせ、部分回復なしのMP不足を確認します]
    #   引数: [self: 資源不足の拒否順を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_mp_shortage_precedes_cure_request_validation(self):
        cases = [self.quote_case(effects, current_mp=3, roll=None) for effects in (["poison"], [])]
        cases[1]["request"]["status_effects"] = {"invalid": True}
        for observation in self.run_probe({"cases": cases})["results"]:
            self.assertEqual(observation["result"], {"ok": False, "reason": "insufficient_mp"})
            self.assertTrue(observation["input_preserved"])

    # {
    #   責務: [test_performance_probe_executes_capped_healing_and_real_single_cure: 計測経路がHP回復・MP消費・一件治療まで実行することを確認します]
    #   処理: [1: 少数反復の統合計測で上限30・回復10・残MP6・毒一件解除と原本保持を照合します]
    #   引数: [self: 実計測ケースを確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_performance_probe_executes_capped_healing_and_real_single_cure(self):
        result = self.run_probe({"performance": True, "iterations": 20, "samples": 3, "warmup": 2})
        quote = result["quote"]
        self.assertEqual((quote["heal_amount"], quote["healed"], quote["remaining_hp"], quote["remaining_mp"]), (30, 10, 1000, 6))
        self.assertEqual((quote["candidate_index"], quote["cured"], quote["cured_name"]), (2, True, "毒"))
        self.assertEqual(len(result["original_effects"]), 4)
        self.assertEqual(quote["remaining_status_effects"], [result["original_effects"][index] for index in (0, 1, 3)])
        self.assertTrue(result["input_preserved"])
        self.assertGreaterEqual(result["microseconds"], 0)
