"""速度強化の期間条件から、明示した抽選値で一期間を選ぶ純粋契約を実GodotとPython正本で比較します。"""
# {
#   責務: [test_gdscript_speed_buff_duration: 速度強化の期間選択・乱数消費の有無・厳密拒否・入力保持を検証します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import test_gdscript_roster as fixture
import test_gdscript_magic_skill as probe_fixture
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [SpeedBuffDurationBoundaryTests: 期間選択が乱数生成・I/O・実状態更新・Application接続を持たないことを確認します]
#   フィールド: []
# }
class SpeedBuffDurationBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_duration_choice_does_not_draw_random_values: 期間選択の関数本体に乱数生成と状態更新APIがないことを確認します]
    #   処理: [1: choose_durationから次の宣言コメントまでを取り出し、禁止依存を検出します]
    #   引数: [self: 期間選択の境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_duration_choice_does_not_draw_random_values(self):
        # 乱数の所有者を呼び出し側へ固定し、純粋契約が抽選を引き直す経路を作らないことを確認します。
        source = (fixture.ROOT / "gdscript/engine/speed_buff_contract.gd").read_text(encoding="utf-8")
        match = re.search(r"static func choose_duration\(.*?(?=\n# \{)", source, re.S)
        self.assertIsNotNone(match)
        # Pythonのrandintを説明するコメントと区別するため、Godotの乱数APIは呼出し形で検出します。
        for forbidden in ("randf(", "randi(", "randi_range(", "randomize(", "RandomNumberGenerator",
                          "FileAccess", "apply_multiplier", "pay_mp"):
            self.assertNotIn(forbidden, match.group(0))
        application = (fixture.ROOT / "gdscript/application/battle_session_application.gd").read_text(encoding="utf-8")
        self.assertNotIn("speed_buff_contract", application)


# {
#   責務: [SpeedBuffDurationTests: 専用一時領域・正規ピオラ定義・Python期間抽選の比較先を所有します]
#   フィールド: [
#     folder: プローブ要求JSONだけを作る専用一時領域（Path）
#     definition: 正規ピオラ定義の独立コピー（dict）
#     engine: 期間抽選の比較だけに使う学習無効のPython BattleEngine
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real speed-buff duration probes")
class SpeedBuffDurationTests(unittest.TestCase):
    # {
    #   責務: [setUp: 実セーブと独立したプローブ要求先とPython期間比較先を用意します]
    #   処理: [1: 専用一時領域と正規ピオラ定義のコピーを作り、学習しない比較先を初期化します]
    #   引数: [self: 専用領域と比較先の所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        # 比較では既存のモンスター・AI・保存データを読み書きしません。
        temporary = tempfile.TemporaryDirectory(prefix="kadoka-speed-buff-duration-")
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        document = json.loads((fixture.ROOT / "data/skills/skills.json").read_text(encoding="utf-8"))
        self.definition = copy.deepcopy(next(skill for skill in document["skills"] if skill["id"] == "piora"))
        self.engine = BattleEngine(GameRepository(fixture.ROOT / "data"), [], [], learning_enabled=False)

    # {
    #   責務: [run_probe: 共用の実Godot起動・診断・要求JSON不変検査へ委譲します]
    #   処理: [1: 共用テスト環境に専用要求を渡し、実行観測を返します]
    #   引数: [
    #     self: 共用プローブが必要とするfolderを所有するテストケース
    #     payload: ケース一覧を持つ要求（dict）
    #   ]
    #   戻り値: [result: 実Godotの観測結果（dict）]
    # }
    def run_probe(self, payload):
        return probe_fixture.MagicSkillQuoteTests.run_probe(self, payload)

    # {
    #   責務: [choose_case: ケース間で条件を共有しない期間選択要求を作ります]
    #   処理: [1: 期間条件と要求を独立コピーし、速度強化の期間選択操作へ包みます]
    #   引数: [
    #     condition: quote_buffが返す形式の期間条件、または不正条件（Any）
    #     request: duration_rollを持つ要求、または不正要求（Any）
    #   ]
    #   戻り値: [result: 共用プローブの速度強化choose_duration要求（dict）]
    # }
    @staticmethod
    def choose_case(condition, request):
        # 入力保持の検査がケース間で干渉しないよう、ネストした値もコピーします。
        return {"operation": "choose_duration", "speed_buff": True,
                "condition": copy.deepcopy(condition), "request": copy.deepcopy(request)}

    # {
    #   責務: [python_duration: 実Pythonの_buff_durationへ明示した抽選戻り値を渡し、期間とrandint呼出しを返します]
    #   処理: [1: 乱数源を記録用の代役へ差し替え、期間と抽選上下限の呼出し一覧を返します]
    #   引数: [
    #     self: Python比較先のengineを所有するテストケース
    #     definition: 期間を持つ速度強化定義（dict）
    #     roll: randintが返す明示値。範囲以外では呼ばれないことを確認します（int | None）
    #   ]
    #   戻り値: [result: Pythonの期間（int | None）とrandintへ渡された引数一覧の組（tuple）]
    # }
    def python_duration(self, definition, roll):
        # 実乱数を使わず、Pythonが乱数を消費する条件と結果だけを観測します。
        self.engine.rng = mock.Mock()
        self.engine.rng.randint.return_value = roll
        duration = self.engine._buff_duration(definition)
        return duration, [tuple(call.args) for call in self.engine.rng.randint.call_args_list]

    # {
    #   責務: [test_quoted_conditions_choose_the_same_duration_as_python: 予測した期間条件と明示値からの期間選択をPythonと照合します]
    #   処理: [
    #     1: 正規ピオラと互換MOD期間を予測し、期間条件を得ます
    #     2: 範囲は上下限と内側の値、固定・無期限は抽選値なしで期間を選びます
    #     3: Pythonの期間とrandintの呼出し有無・上下限を照合します
    #   ]
    #   引数: [self: 期間選択の正常系を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_quoted_conditions_choose_the_same_duration_as_python(self):
        periods = [[3, 6], None, 0, -5, 1, 4.9, " 4 ", [6, 3], [0, -8], [-1.5, 4.9], [" 2 ", "5"], [4, 4]]
        definitions = [{**copy.deepcopy(self.definition), "duration": value} for value in periods]
        quotes = self.run_probe({"cases": [
            {"operation": "quote", "speed_buff": True, "definition": definition, "request": {"current_mp": 10}}
            for definition in definitions]})["results"]
        cases, expectations = [], []
        for definition, quoted in zip(definitions, quotes):
            condition = quoted["result"]["duration"]
            # 範囲は上下限の両端と中間を選び、上端を含む抽選範囲をPythonのrandintと一致させます。
            if condition["mode"] == "range":
                rolls = sorted({condition["minimum"], (condition["minimum"] + condition["maximum"]) // 2,
                                condition["maximum"]})
                for roll in rolls:
                    cases.append(self.choose_case(condition, {"duration_roll": roll}))
                    expectations.append((definition, roll))
            else:
                cases.append(self.choose_case(condition, {}))
                expectations.append((definition, None))
        observations = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        for case, (definition, roll), observation in zip(cases, expectations, observations):
            with self.subTest(condition=case["condition"], roll=roll):
                result = observation["result"]
                duration, randint_calls = self.python_duration(definition, roll)
                self.assertEqual(result, {"ok": True, "scope": "speed_buff_duration",
                                          "mode": case["condition"]["mode"], "duration": duration})
                if case["condition"]["mode"] == "range":
                    self.assertEqual(randint_calls, [(case["condition"]["minimum"], case["condition"]["maximum"])])
                else:
                    self.assertEqual(randint_calls, [])
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_rolls_are_required_only_for_ranges: 範囲だけが抽選値を要求し、範囲外や不要な抽選値を引き直しなしで拒否することを確認します]
    #   処理: [1: 欠落・範囲外・不正型・非有限・不要な抽選値を渡し、理由付き拒否と入力保持を照合します]
    #   引数: [self: 抽選値の厳密性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_rolls_are_required_only_for_ranges(self):
        piora = {"mode": "range", "minimum": 3, "maximum": 6}
        fixed = {"mode": "fixed", "minimum": 4, "maximum": 4}
        untimed = {"mode": "untimed", "minimum": None, "maximum": None}
        expected = [(self.choose_case(piora, {}), "missing_speed_buff_duration_roll")]
        for roll in (2, 7, 2.0, 7.0, 4.5, True, False, None, "4", [4], {}, -1, 2**53):
            expected.append((self.choose_case(piora, {"duration_roll": roll}), "invalid_speed_buff_duration_roll"))
        for condition in (fixed, untimed):
            for roll in (4, None):
                expected.append((self.choose_case(condition, {"duration_roll": roll}),
                                 "unexpected_speed_buff_duration_roll"))
        for request in (None, [], 4, "4"):
            expected.append((self.choose_case(piora, request), "invalid_duration_request"))
        for request in ({"duration_roll": 4, "duration": 4}, {"roll": 4}, {"current_mp": 10}):
            expected.append((self.choose_case(piora, request), "unsupported_duration_request"))
        # JSONで表せない非有限の抽選値は、共用プローブの注入で確認します。
        for value in ("nan", "inf"):
            case = self.choose_case(piora, {"duration_roll": 4})
            case["special"] = [{"target": "request", "field": "duration_roll", "value": value}]
            expected.append((case, "invalid_speed_buff_duration_roll"))
        observations = self.run_probe({"cases": [case for case, _ in expected]})["results"]
        for (case, reason), observation in zip(expected, observations):
            with self.subTest(case=case):
                self.assertEqual(observation["result"], {"ok": False, "reason": reason})
                self.assertTrue(observation["input_preserved"])

    # {
    #   責務: [test_forged_conditions_are_rejected: quote_buffが返さない期間条件を、部分成功なしで拒否することを確認します]
    #   処理: [1: 形式・mode・上下限の組み合わせを壊した条件を渡し、理由付き拒否と入力保持を照合します]
    #   引数: [self: 期間条件の再検証を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_forged_conditions_are_rejected(self):
        conditions = [None, [], {}, "range", {"mode": "range", "minimum": 3},
                      {"mode": "range", "minimum": 3, "maximum": 6, "roll": 4},
                      {"mode": "random", "minimum": 3, "maximum": 6}, {"mode": None, "minimum": 3, "maximum": 6},
                      {"mode": "untimed", "minimum": 1, "maximum": None},
                      {"mode": "untimed", "minimum": None, "maximum": 0},
                      {"mode": "fixed", "minimum": 3, "maximum": 6}, {"mode": "fixed", "minimum": 0, "maximum": 0},
                      {"mode": "fixed", "minimum": None, "maximum": None},
                      {"mode": "range", "minimum": 6, "maximum": 3}, {"mode": "range", "minimum": 0, "maximum": 3},
                      {"mode": "range", "minimum": -1, "maximum": 3},
                      {"mode": "range", "minimum": 1.5, "maximum": 3}, {"mode": "range", "minimum": "3", "maximum": 6},
                      {"mode": "range", "minimum": True, "maximum": 6},
                      {"mode": "range", "minimum": 3, "maximum": 2**53}]
        cases = []
        for condition in conditions:
            # 不正条件では、抽選値の有無より先に条件の拒否が返ることを確認します。
            request = {"duration_roll": 4} if isinstance(condition, dict) and condition.get("mode") == "range" else {}
            cases.append(self.choose_case(condition, request))
        for field, value in (("minimum", "nan"), ("maximum", "inf")):
            case = self.choose_case({"mode": "range", "minimum": 3, "maximum": 6}, {"duration_roll": 4})
            case["special"] = [{"target": "condition", "field": field, "value": value}]
            cases.append(case)
        for case, observation in zip(cases, self.run_probe({"cases": cases})["results"]):
            with self.subTest(condition=case["condition"]):
                self.assertEqual(observation["result"], {"ok": False, "reason": "invalid_speed_buff_duration_condition"})
                self.assertTrue(observation["input_preserved"])


if __name__ == "__main__":
    unittest.main()
