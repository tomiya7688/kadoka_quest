"""状態一覧の治療予測を実GodotとPython正本で比較します。実セーブは使用しません。"""
# {
#   責務: [test_gdscript_status_cure: 候補順序・判定境界・拒否・独立コピーと保存非変更を検証します]
#   フィールド: []
# }
from __future__ import annotations

import base64
import copy
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import test_battle_status_cure as python_fixture
import test_gdscript_roster as godot_fixture


# {
#   責務: [StatusCureBoundaryTests: 治療予測の純粋な依存と、Session/画面への未接続を確認します]
#   フィールド: []
# }
class StatusCureBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_prediction_has_no_io_rng_ai_or_state_mutation_dependency: 治療計算へ保存・乱数生成・AI・実資源更新を持ち込まないことを確認します]
    #   処理: [1: 純粋契約の禁止依存と、application/既存回復APIへの未接続を確認します]
    #   引数: [self: 純粋計算の依存境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_prediction_has_no_io_rng_ai_or_state_mutation_dependency(self):
        # 治療予測を実治療・状態異常の付与・継続効果や戦闘画面の証拠にしない。
        source = (godot_fixture.ROOT / "gdscript/engine/status_cure_contract.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                          "battle_session", "randf(", "RandomNumberGenerator", ".pay_mp(", ".heal("):
            self.assertNotIn(forbidden, source)
        for name in ("application/field_application", "application/battle_session_application",
                     "engine/heal_skill_contract", "engine/heal_skill_action"):
            source = (godot_fixture.ROOT / f"gdscript/{name}.gd").read_text(encoding="utf-8")
            self.assertNotIn("status_cure_contract", source)


# {
#   責務: [StatusCureQuoteTests: 専用要求領域・保存ダミーと実Godot/Python比較を所有します]
#   フィールド: [
#     folder: 要求JSONと保存ダミーを置く専用一時領域（Path）
#     saved_files: 内容不変を毎回確認する保存ダミーのパス一覧（list[Path]）
#   ]
# }
@unittest.skipUnless(godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real status-cure probes")
class StatusCureQuoteTests(unittest.TestCase):
    # {
    #   責務: [setUp: 実セーブから独立した要求領域と個体・AI・items・party・stateの保存ダミーを用意します]
    #   処理: [1: 専用一時領域へ内容保持を確認するJSONだけを作ります]
    #   引数: [self: 専用領域とダミーパスの所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kadoka-status-cure-")
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.saved_files = []
        # 正規data/assetsや利用者保存先を出力先にせず、ネストのある保持用ダミーを作る。
        for relative in ("monsters/m01/monster.json", "monsters/m01/ai.json", "items/items.json",
                         "parties/p01.json", "state.json"):
            path = self.folder / "savedata/probe" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"kept": {"deck": [relative, 1]}}, ensure_ascii=False), encoding="utf-8")
            self.saved_files.append(path)

    # {
    #   責務: [run_probe: 実Godotの治療プローブを呼び、診断と要求/保存ダミーのbyte不変を確認します]
    #   処理: [
    #     1: 専用要求を書き、確認対象ファイルのハッシュを取得します
    #     2: 実Godotを起動して解析・実行診断と結果を確認します
    #     3: 要求と保存ダミーが一つも変化しないことを確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域と保持用ダミーの所有者
    #     payload: ケース一覧または性能測定条件（dict）
    #   ]
    #   戻り値: [result: 実Godotの観測結果（dict）]
    # }
    def run_probe(self, payload):
        path = self.folder / "request.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        before = {file: hashlib.sha256(file.read_bytes()).digest() for file in [path, *self.saved_files]}
        process = subprocess.run(
            [str(godot_fixture.GODOT), "--headless", "--path", str(godot_fixture.ROOT / "gdscript"),
             "--script", "res://tests/run_status_cure_probe.gd", "--", str(path)],
            cwd=self.folder, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        # 正常なJSON結果があっても、Godotの解析・実行エラーを成功と扱わない。
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        self.assertNotIn("SCRIPT ERROR", process.stderr)
        self.assertNotIn("ERROR:", process.stderr)
        self.assertEqual(before, {file: hashlib.sha256(file.read_bytes()).digest() for file in before})
        for line in process.stdout.splitlines():
            if line.startswith("KADOKA_STATUS_CURE_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(process.stderr + process.stdout)

    # {
    #   責務: [quote_case: ケース間で状態辞書を共有しない治療要求を作ります]
    #   処理: [1: 一覧を深くコピーし、明示確率と任意判定値を付けます]
    #   引数: [
    #     effects: 予測する順序付き状態異常一覧（list）
    #     chance: 0〜1に制限して使う有限成功確率。数値文字列も許可します
    #     roll: 候補がある場合に必要な0以上1未満の明示判定値。Noneは未指定です
    #   ]
    #   戻り値: [result: 専用プローブのquote要求（dict）]
    # }
    @staticmethod
    def quote_case(effects, chance=0.03, roll=None):
        return {"operation": "quote", "request": {"status_effects": copy.deepcopy(effects),
                                                   "cure_chance": chance, "roll": roll}}

    # {
    #   責務: [python_result: 実Pythonの治療処理を独立戦闘個体で呼び、残存一覧・表示名・乱数要否を取得します]
    #   処理: [1: 固定乱数とコピー個体で_try_cure_statusを呼び、元要求と個体/AIの不変も確認します]
    #   引数: [
    #     self: Python比較結果を検証するテストケース
    #     request: 明示状態一覧・確率・判定値（dict）
    #   ]
    #   戻り値: [result: 治療名・残存一覧と、実Pythonの乱数呼び出し有無（dict）]
    # }
    def python_result(self, request):
        original = copy.deepcopy(request)
        engine = python_fixture.make_engine([] if request.get("roll") is None else [request["roll"]])
        target = python_fixture.make_combatant("target", [], status_effects=copy.deepcopy(request["status_effects"]))
        target.record.ai["kept"] = {"deck": [1, 2]}
        record_before = copy.deepcopy(target.record)
        # 候補選択・表示名・実除去・乱数呼び出しはmockへ置き換えず、Python正本を使う。
        name = engine._try_cure_status(target, float(request["cure_chance"]))
        self.assertEqual(request, original)
        self.assertEqual(target.record, record_before)
        return {"cured": name is not None, "cured_name": name,
                "remaining_status_effects": target.status_effects, "roll_required": engine.rng.random_calls == 1}

    # {
    #   責務: [test_order_defaults_names_and_probability_boundaries_match_python: 混在一覧の先頭候補・一件治療・表示名と確率境界を実Pythonに合わせます]
    #   処理: [1: 順序・解除可否・未知ID・重複・確率の組合せを実Godot/Pythonで照合します]
    #   引数: [self: 治療互換性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_order_defaults_names_and_probability_boundaries_match_python(self):
        locked = {"id": "special_lock", "removable": False, "metadata": {"deck": [1, {"kept": [False, None]}]}}
        poison = {"id": "poison", "display_name": "毒", "removable": True}
        decks = [[], [locked], ["sleep"], [""], [{}], [{"id": "mod_status"}],
                 [{"id": "curse", "display_name": ""}], [{"id": "", "display_name": ""}],
                 [locked, poison, "sleep"], [poison, poison, "sleep"], ["sleep", poison],
                 [{"id": "poison", "display_name": "毒", "metadata": {"deck": ["x", {"value": 4}]}}],
                 ["poison", "paralysis", "sleep", "confusion", "bind", "curse_bind", "curse", "bleeding"]]
        cases = [self.quote_case(deck, chance, roll) for deck, chance, roll in itertools.product(
            decks, (-1, 0, 0.03, 0.5, 1, 2, "0.03", " 0 "), (0, 0.02, 0.03, 0.5, 0.999999))]
        observations = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        for case, observation in zip(cases, observations):
            with self.subTest(request=case["request"]):
                result = observation["result"]
                self.assertTrue(result["ok"], result)
                self.assertEqual({key: result[key] for key in ("cured", "cured_name", "remaining_status_effects", "roll_required")},
                                 self.python_result(case["request"]))
                self.assertEqual(result["scope"], "status_cure_quote")
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_native_exclusive_roll_and_depth_boundary: 1未満のnative小数とJSON再帰深さ32/33の境界を確認します]
    #   処理: [1: JSONの丸めに依存しない判定値と、許容上限内外のネストを実Godotで照合します]
    #   引数: [self: 判定値と拡張情報の境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_native_exclusive_roll_and_depth_boundary(self):
        cases = []
        for chance in (0.03, 1):
            case = self.quote_case(["poison"], chance, 0.9999999999999999)
            case["special"] = [{"field": "roll", "value": "next_below_one"}]
            cases.append(case)
        # 一覧0→状態辞書1→metadata2から、子を深さ32/33まで配置する。
        for count in (30, 31):
            nested = "leaf"
            for _ in range(count):
                nested = [nested]
            cases.append(self.quote_case([{"id": "mod", "metadata": nested}], 1, 0))
        observations = self.run_probe({"cases": cases})["results"]
        for case, observation in zip(cases[:2], observations[:2]):
            result = observation["result"]
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["cured"], self.python_result(case["request"])["cured"])
        self.assertTrue(observations[2]["result"]["ok"])
        self.assertEqual(observations[3]["result"]["reason"], "invalid_status_effects")

    # {
    #   責務: [test_candidate_selection_and_roll_requirements: 解除不可を飛ばした候補位置と、確率0/1でも必要な判定値を確認します]
    #   処理: [1: 先頭/後続/候補なしと省略/nullの判定値を照合します]
    #   引数: [self: 候補選択と乱数取得前の契約を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_candidate_selection_and_roll_requirements(self):
        locked = {"id": "lock", "removable": False, "metadata": {"deck": [1]}}
        decks = [[], [locked], [locked, "sleep", "poison"], ["sleep", locked]]
        selected = self.run_probe({"cases": [{"operation": "select", "effects": deck} for deck in decks]})["results"]
        for deck, index, observation in zip(decks, (-1, -1, 1, 0), selected):
            with self.subTest(deck=deck):
                result = observation["result"]
                self.assertEqual((result["effects"], result["candidate_index"], result["roll_required"]), (deck, index, index >= 0))
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])
        cases = [self.quote_case(deck, chance) for deck, chance in itertools.product(decks, (-1, 0, 0.03, 1, 2))]
        cases += [{"operation": "quote", "request": {"status_effects": deck, "cure_chance": 0}} for deck in decks]
        for case, observation in zip(cases, self.run_probe({"cases": cases})["results"]):
            with self.subTest(case=case):
                result = observation["result"]
                expected_index = next((index for index, effect in enumerate(case["request"]["status_effects"])
                                       if python_fixture.BattleEngine._status_is_removable(effect)), -1)
                self.assertEqual(result["ok"], expected_index < 0)
                if expected_index < 0:
                    self.assertEqual(result["candidate_index"], -1)
                    self.assertEqual(self.python_result(case["request"])["roll_required"], False)
                else:
                    self.assertEqual(result["reason"], "missing_cure_roll")

    # {
    #   責務: [test_malformed_effects_known_fields_and_nested_values_are_rejected: 状態の形式・認識キーの型・深さと非JSON拡張値を拒否します]
    #   処理: [1: 配列以外・不正状態・bool以外の解除可否・過深な拡張情報をselect/quoteへ渡します]
    #   引数: [self: 一覧と状態形式を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_malformed_effects_known_fields_and_nested_values_are_rejected(self):
        invalid = [None, {}, "poison", [None], [True], [1], [[]]]
        for field, value in itertools.product(("id", "display_name"), (None, True, 1, [], {})):
            invalid.append([{field: value}])
        invalid.extend([[{"id": "lock", "removable": value}] for value in (None, 0, 1, "false", [], {})])
        nested = []
        for _ in range(34):
            nested = [nested]
        invalid.extend([[{"id": "mod", "metadata": nested}], [{"id": "mod", "metadata": 2**53}]])
        cases = [{"operation": "select", "effects": effects} for effects in invalid]
        cases += [self.quote_case(effects, 1, 0) for effects in invalid]
        for observation in self.run_probe({"cases": cases})["results"]:
            with self.subTest(result=observation):
                self.assertEqual(observation["result"], {"ok": False, "reason": "invalid_status_effects"})
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_invalid_requests_numbers_and_native_non_json_values_are_rejected: 不正確率・判定値・未知要求とnative非有限/Objectを厳密に拒否します]
    #   処理: [1: 候補の有無にかかわらず型・範囲・未知キーと非JSON値の拒否を確認します]
    #   引数: [self: 明示入力の拒否境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_requests_numbers_and_native_non_json_values_are_rejected(self):
        cases = []
        for deck in ([], ["poison"]):
            # chanceのNoneは不正。rollのNoneは候補がない場合の省略と区別して別テストで確認する。
            for chance in (None, True, [], {}, "no", "nan", "inf", 2**53):
                cases.append(self.quote_case(deck, chance, 0))
            for roll in (True, [], {}, "0.02", -0.01, 1, 2):
                cases.append(self.quote_case(deck, 1, roll))
            for field, value in itertools.product(("status_cure_chance", "all_targets", "duration", "target"), (False, 0, "", [], {})):
                case = self.quote_case(deck, 1, 0)
                case["request"][field] = value
                cases.append(case)
            for field, special in itertools.product(("cure_chance", "roll"), ("nan", "inf")):
                case = self.quote_case(deck, 1, 0)
                case["special"] = [{"field": field, "value": special}]
                cases.append(case)
        for special in ("nan", "inf", "object"):
            case = self.quote_case([{"id": "poison"}], 1, 0)
            case["special"] = [{"status_index": 0, "field": "metadata", "value": special}]
            cases.append(case)
        cases += [{"operation": "quote", "request": value} for value in (None, [], {}, {"status_effects": []}, {"cure_chance": 1})]
        for observation in self.run_probe({"cases": cases})["results"]:
            with self.subTest(result=observation):
                self.assertFalse(observation["result"]["ok"])
                self.assertIn("reason", observation["result"])
                self.assertTrue(observation["input_preserved"])

    # {
    #   責務: [test_performance_probe_measures_real_cure_without_changing_originals: 性能プローブが最初の解除可能な毒だけを治療し元一覧を保持することを確認します]
    #   処理: [1: 少数反復で実Godotを測り、候補位置・治療名・順序と元一覧を照合します]
    #   引数: [self: 性能計測用のケースを検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_performance_probe_measures_real_cure_without_changing_originals(self):
        result = self.run_probe({"performance": True, "iterations": 100, "samples": 3, "warmup": 10})
        self.assertGreaterEqual(result["microseconds"], 0)
        self.assertTrue(result["input_preserved"])
        quote = result["quote"]
        self.assertTrue(quote["ok"])
        self.assertEqual((quote["candidate_index"], quote["cured"], quote["cured_name"], quote["roll_required"]), (2, True, "毒", True))
        original = result["original_effects"]
        self.assertEqual(original[2]["id"], "poison")
        self.assertEqual(quote["remaining_status_effects"], [original[0], original[1], original[3]])
