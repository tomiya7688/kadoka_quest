"""自傷付き魔法の純粋予測を実GodotとPython正本で比較します。実セーブは使用しません。"""
# {
#   責務: [test_gdscript_self_damage_magic: 敵への魔法効果・術者のHP代償・入力保持・拒否境界を検証します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import itertools
import unittest
from unittest import mock

import test_gdscript_magic_skill as magic_fixture
import test_gdscript_roster as fixture
from kadoka_quest.core.combatant import Combatant
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.repository import STAT_KEYS


# {
#   責務: [SelfDamageMagicBoundaryTests: 自傷予測へSession更新・I/O・AI・画面依存を持ち込まないことを確認します]
#   フィールド: []
# }
class SelfDamageMagicBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_prediction_has_no_io_or_state_mutation: 自傷予測が資源更新やI/Oを行わず、画面からも直接呼ばれないことを確認します]
    #   処理: [
    #     1: 予測処理の禁止依存を検査します
    #     2: applicationと画面が数値予測を直接呼ばないことを確認します
    #   ]
    #   引数: [self: 純粋計算の責務境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_prediction_has_no_io_or_state_mutation(self):
        # 数値予測を、実資源更新・乱数生成・永続化の処理にしない。
        source = (fixture.ROOT / "gdscript/engine/self_damage_magic_contract.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                          "battle_session", ".pay_mp(", ".take_damage(", "randf(", "RandomNumberGenerator"):
            self.assertNotIn(forbidden, source)
        # 行動処理からの予測利用は許可するが、applicationや画面へ計算責務を移さない。
        for name in ("application/battle_session_application", "application/field_application"):
            source = (fixture.ROOT / f"gdscript/{name}.gd").read_text(encoding="utf-8")
            self.assertNotIn("self_damage_magic_contract", source)


# {
#   責務: [SelfDamageMagicQuoteTests: 専用JSONと実Godotプローブ、学習しないPython比較先を所有します]
#   フィールド: [
#     folder: 実セーブから独立した要求JSONの専用一時領域（Path）
#     document: 正規スキル一覧の読み取りコピー（dict）
#     definitions: IDから正規定義を検索する辞書（dict）
#     engine: AI学習を無効にした数値比較用BattleEngine
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real self-damage magic probes")
class SelfDamageMagicQuoteTests(unittest.TestCase):
    # {
    #   責務: [setUp: 既存の魔法fixtureで一時領域・定義・Python比較先を用意します]
    #   処理: [1: 専用領域と読み取りコピーの生成を共用fixtureへ委譲します]
    #   引数: [self: 検証環境を所有するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        # unittestクラスを継承して通常魔法の全テストを重複実行せず、準備処理だけを共用する。
        magic_fixture.MagicSkillQuoteTests.setUp(self)

    # {
    #   責務: [run_probe: 自傷契約を指定したケースを、既存の実Godot起動と診断検証へ渡します]
    #   処理: [1: 契約選択を独立コピーへ加えます, 2: 共有プローブで結果と要求ファイル不変を確認します]
    #   引数: [
    #     self: 専用領域の所有者
    #     payload: ケース配列または性能条件（dict）
    #   ]
    #   戻り値: [result: 実Godotの観測結果（dict）]
    # }
    def run_probe(self, payload):
        # 呼出元の要求は変更せず、契約選択はテストプローブ内だけで使用する。
        selected = copy.deepcopy(payload)
        selected["self_damage"] = True
        for case in selected.get("cases", []):
            case["self_damage"] = True
        return magic_fixture.MagicSkillQuoteTests.run_probe(self, selected)

    # {
    #   責務: [quote_request: 術者HPを含み、ケース間で可変値を共有しない基準要求を作ります]
    #   処理: [1: 基準HP/MP・耐性・揺らぎへケース固有の値を重ねます]
    #   引数: [changes: 基準数値を置き換えるケース固有の値（dict）]
    #   戻り値: [result: 独立した数値予測要求（dict）]
    # }
    @staticmethod
    def quote_request(**changes):
        # 代償が現在HPではなく最大HPを基準にするよう、異なる値を使う。
        return {"magic": 100, "current_mp": 100, "actor_hp": 70, "actor_max_hp": 123,
                "target_hp": 700, "target_max_hp": 1000, "target_resistances": {}, "variance": 1.0, **changes}

    # {
    #   責務: [python_hp_result: 実Pythonの攻撃処理で対象HPと術者HPを計算し、元個体とAIの保持を確認します]
    #   処理: [
    #     1: 元レコードから独立した比較用戦闘個体を作ります
    #     2: 揺らぎと反撃条件を固定して実攻撃を呼びます
    #     3: 対象HP・術者HPと入力保持を確認します
    #   ]
    #   引数: [
    #     self: 学習しない比較先の所有者
    #     definition: 自傷付き魔法定義（dict）
    #     request: 比較する数値要求（dict）
    #   ]
    #   戻り値: [result: 対象のdealt/remaining_hpと術者のself_damage/self_dealt/remaining_actor_hp（dict）]
    # }
    def python_hp_result(self, definition, request):
        # 元個体/AIと戦闘中のHPは独立し、利用者の保存先を使用しない。
        records = [MonsterRecord({"id": str(index), "name": "比較", "species_id": "slime"}, {"keep": [index]})
                   for index in range(2)]
        before = copy.deepcopy(records)
        actor_stats = {key: 1 for key in STAT_KEYS}
        actor_stats.update(hp=request["actor_max_hp"], mp=request["current_mp"], magic=int(request["magic"]))
        equipment = {"fixed_bonus_damage": request.get("fixed_bonus_damage", 0),
                     "skill_modifiers": {definition["id"]: {"power_multiplier": 99}}}
        actor = Combatant(records[0], actor_stats, [], {}, equipment=equipment)
        target = Combatant(records[1], {**actor_stats, "hp": request["target_max_hp"], "defense": 999999},
                           [], request.get("target_resistances", {}))
        actor.hp = request["actor_hp"]
        target.hp = request["target_hp"]
        target.guard = request.get("guard", 1.0)
        self.engine.rng = mock.Mock()
        self.engine.rng.uniform.return_value = request["variance"]
        self.engine.log.clear()
        # 攻撃計算そのものはmockへ置き換えない。MP実支払い・回避・反撃はこの比較の範囲外。
        self.engine._attack(actor, target, definition, allow_counter=False)
        self.engine.rng.random.assert_not_called()
        if target.resistances.get(definition.get("element", "physical")) == "immune":
            self.engine.rng.uniform.assert_not_called()
        else:
            self.engine.rng.uniform.assert_called_once_with(0.92, 1.08)
        self.engine.learning.learn.assert_not_called()
        self.assertEqual(records, before)
        self.assertEqual(actor.mp, request["current_mp"])
        # ログにはHP下限で制限する前の代償量が記録されるため、実減少とは別に観測する。
        cost_lines = [line for line in self.engine.log if "代償としてHPを" in line]
        cost = int(cost_lines[0].split("代償としてHPを")[1].split("消耗")[0]) if cost_lines else 0
        return {"dealt": request["target_hp"] - target.hp, "remaining_hp": target.hp,
                "self_damage": cost, "self_dealt": request["actor_hp"] - actor.hp, "remaining_actor_hp": actor.hp}

    # {
    #   責務: [test_resistance_and_hp_matrix_matches_python: 自傷と敵への効果を耐性・HP・揺らぎの組合せで実Pythonと比較します]
    #   処理: [1: 組合せを作ります, 2: 実GodotとPythonの数値および入力保持を照合します]
    #   引数: [self: 正規metal_burstの数値を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_resistance_and_hp_matrix_matches_python(self):
        # 無効・吸収でも代償は発生し、HP1と満HPの境界も比較する。
        definition = self.definitions["metal_burst"]
        cases = []
        for resistance, hp, actor_hp, guard, variance, bonus in itertools.product(
            ("normal", "weak", "strong", "immune", "absorb", "mod_unknown", None),
            (0, 700, 1000), (1, 7, 123), (1.0, 0.5), (0.92, 1.0, 1.08), (0, 3),
        ):
            request = self.quote_request(target_hp=hp, actor_hp=actor_hp, guard=guard, variance=variance,
                                         fixed_bonus_damage=bonus,
                                         target_resistances={} if resistance is None else {"metal": resistance})
            cases.append({"operation": "quote", "definition": definition, "request": request})
        observations = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        for case, observation in zip(cases, observations):
            with self.subTest(request=case["request"]):
                result = observation["result"]
                self.assertTrue(result["ok"], result)
                for field, value in self.python_hp_result(definition, case["request"]).items():
                    self.assertEqual(result[field], value)
                self.assertEqual(result["remaining_mp"], 82)
                self.assertEqual(result["scope"], "self_damage_magic_quote")
                self.assertEqual(result["applied_guard"], 1.0)
                self.assertEqual(result["healed"], max(0, -result["dealt"]))
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_mod_ratios_and_prepared_string_zero_match_python: 有限MODの自傷率と文字列0の真偽判定を実Pythonと比較します]
    #   処理: [1: MOD定義の選択結果を取得します, 2: 選択後の予測を実Pythonと照合します]
    #   引数: [self: 自傷率の変換互換性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_mod_ratios_and_prepared_string_zero_match_python(self):
        # 数値0は無効、文字列0と負の率はPython正本で最低1の代償になる。
        definitions = [{**self.definitions["metal_burst"], "self_damage_ratio": ratio, "power": -1.2}
                       for ratio in (-0.1, 0, -0.0, 0.0001, 0.1, 1, 2, "0", "0.0", "-0.1", " 0.1 ")]
        prepared = self.run_probe({"cases": [
            {"operation": "prepare", "document": {"schema_version": 1, "skills": [definition]},
             "skill_id": "metal_burst"} for definition in definitions]})["results"]
        cases = []
        for definition, observation in zip(definitions, prepared):
            self.assertTrue(observation["result"]["ok"], observation)
            self.assertEqual(observation["result"]["skill"]["self_damage_ratio"], definition["self_damage_ratio"])
            self.assertTrue(observation["input_preserved"])
            self.assertTrue(observation["result_independent"])
            for hp, maximum, resistance in itertools.product((1, 8), (9, 999), ("normal", "immune", "absorb")):
                cases.append({"operation": "quote", "definition": observation["result"]["skill"],
                              "request": self.quote_request(actor_hp=hp, actor_max_hp=maximum,
                                                            target_resistances={"metal": resistance})})
        for case, observation in zip(cases, self.run_probe({"cases": cases})["results"]):
            with self.subTest(case=case):
                result = observation["result"]
                self.assertTrue(result["ok"], result)
                for field, value in self.python_hp_result(case["definition"], case["request"]).items():
                    self.assertEqual(result[field], value)
                self.assertEqual(result["self_damage_enabled"], bool(case["definition"]["self_damage_ratio"]))

    # {
    #   責務: [test_selection_and_unsupported_effects_are_rejected: 一覧形式・定義の一意性・自傷以外の未対応効果を検証します]
    #   処理: [1: 正規と不正の定義を用意します, 2: 選択結果と拒否および入力保持を確認します]
    #   引数: [self: 定義検証のテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_selection_and_unsupported_effects_are_rejected(self):
        # 自傷以外の効果がfalse・0・空でも、効果を捨てて成功にしない。
        definition = self.definitions["metal_burst"]
        cases = [{"operation": "prepare", "document": self.document, "skill_id": "metal_burst"}]
        cases += [{"operation": "prepare", "document": self.document, "skill_id": skill_id}
                  for skill_id in ("missing", "weaken", "possess", "dice_magic", "attack", None, True, "")]
        cases += [{"operation": "prepare", "document": document, "skill_id": "metal_burst"} for document in (
            None, [], {}, {"schema_version": True, "skills": [definition]},
            {"schema_version": 2, "skills": [definition]}, {"schema_version": 1, "skills": {}},
            {"schema_version": 1, "skills": [definition, definition]},
        )]
        for field, value in itertools.product(("status_effect", "target", "all_targets", "critical_multiplier"), (False, 0, {})):
            cases.append({"operation": "quote", "definition": {**definition, field: value}, "request": self.quote_request()})
        for change in ({"id": "attack"}, {"kind": "physical"}, {"mp_cost": 0}, {"display_name": ""}, {"element": []}):
            cases.append({"operation": "quote", "definition": {**definition, **change}, "request": self.quote_request()})
        for definition in (None, [], {}, self.definitions["weaken"]):
            cases.append({"operation": "quote", "definition": definition, "request": self.quote_request()})
        observations = self.run_probe({"cases": cases})["results"]
        self.assertTrue(observations[0]["result"]["ok"])
        self.assertEqual(observations[0]["result"]["skill"], self.definitions["metal_burst"])
        for observation in observations[1:]:
            with self.subTest(result=observation):
                self.assertFalse(observation["result"]["ok"])
                self.assertIn("reason", observation["result"])
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_invalid_resources_ratios_and_nonfinite_values_are_rejected: 不正資源・自傷率・未知要求・NaN/Inf・演算精度超過を拒否します]
    #   処理: [1: 不正型と境界外の要求を作ります, 2: 非有限値を注入します, 3: 拒否と入力保持を確認します]
    #   引数: [self: 不正入力のテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_resources_ratios_and_nonfinite_values_are_rejected(self):
        # 術者HP0を復活予測へ変換せず、不正な数値を暗黙に切り捨てない。
        definition = self.definitions["metal_burst"]
        changes = [{field: value} for field, values in (
            ("actor_hp", (None, True, "1", 0, -1, 1.5, 124, 2**53)),
            ("actor_max_hp", (None, True, "123", 0, -1, 1.5, 2**53)),
            ("current_mp", (None, True, "100", -1, 1.5, 2**53)),
            ("target_hp", (None, -1, 1001)), ("variance", (None, 0.919, 1.081)),
            ("target_resistances", (None, {"metal": False})),
        ) for value in values]
        changes += [{field: False} for field in ("evade_element", "counter_ready", "equipment", "actor_alive", "target_mp")]
        cases = [{"operation": "quote", "definition": definition, "request": self.quote_request(**change)} for change in changes]
        cases += [{"operation": "quote", "definition": definition, "request": request} for request in (None, [], {})]
        for ratio in (None, True, False, "", "no", "NaN", "Infinity", [], {}, 2**53):
            cases.append({"operation": "quote", "definition": {**definition, "self_damage_ratio": ratio},
                          "request": self.quote_request()})
        for target, field in (("definition", "self_damage_ratio"), ("request", "actor_hp"), ("request", "actor_max_hp")):
            for value in ("nan", "inf"):
                cases.append({"operation": "quote", "definition": definition, "request": self.quote_request(),
                              "special": [{"target": target, "field": field, "value": value}]})
        # 入力は精度範囲内でも、最大HPと率の積が範囲を超えたら拒否する。
        cases.append({"operation": "quote", "definition": {**definition, "self_damage_ratio": 2},
                      "request": self.quote_request(actor_max_hp=2**52)})
        for observation in self.run_probe({"cases": cases})["results"]:
            with self.subTest(result=observation):
                self.assertFalse(observation["result"]["ok"])
                self.assertIn("reason", observation["result"])
                self.assertTrue(observation["input_preserved"])

    # {
    #   責務: [test_mp_boundary_and_exact_hp_limits: MP不足・ちょうどの消費予測・術者HP1と精度上限を確認します]
    #   処理: [
    #     1: 消費MP18の前後と術者HP1・整数精度上限の要求を用意します
    #     2: 自傷魔法の予測値と要求・結果のコピー独立性を確認します
    #   ]
    #   引数: [self: 数値境界のテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_mp_boundary_and_exact_hp_limits(self):
        # HPが代償未満でも使用予測は成立し、術者の生存HP1を保持する。
        cases = [{"operation": "quote", "definition": self.definitions["metal_burst"],
                  "request": self.quote_request(current_mp=mp, actor_hp=1)} for mp in (17, 18)]
        for ratio in (0, "0", 1):
            cases.append({"operation": "quote", "definition": {**self.definitions["metal_burst"], "self_damage_ratio": ratio},
                          "request": self.quote_request(actor_hp=2**53-1, actor_max_hp=2**53-1, current_mp=18)})
        observations = self.run_probe({"cases": cases})["results"]
        self.assertEqual(observations[0]["result"]["reason"], "insufficient_mp")
        self.assertEqual((observations[1]["result"]["remaining_mp"], observations[1]["result"]["remaining_actor_hp"]), (0, 1))
        self.assertEqual(observations[1]["result"]["self_dealt"], 0)
        for case, observation in zip(cases[2:], observations[2:]):
            self.assertTrue(observation["result"]["ok"], observation)
            for field, value in self.python_hp_result(case["definition"], case["request"]).items():
                self.assertEqual(observation["result"][field], value)
        for observation in observations:
            self.assertTrue(observation["input_preserved"])
            self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_performance_probe_measures_real_nonmutating_quote: 共用性能ループが自傷付きの正常予測を測ることを確認します]
    #   処理: [
    #     1: 自傷予測の共用プローブを少数反復で実Godotから実行します
    #     2: 時間値・敵HP800/術者HP80/残MP2の予測と元資源の保持を確認します
    #   ]
    #   引数: [self: 性能プローブのテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_performance_probe_measures_real_nonmutating_quote(self):
        # 時間値だけでなく、HP代償20を含む実際の予測が成立したことも検査する。
        result = self.run_probe({"performance": True, "iterations": 100, "samples": 3, "warmup": 10})
        self.assertGreaterEqual(result["microseconds"], 0)
        self.assertTrue(result["input_preserved"])
        self.assertEqual((result["current_mp"], result["target_hp"], result["actor_hp"]), (20, 1000, 100))
        quote = result["quote"]
        self.assertTrue(quote["ok"], quote)
        self.assertEqual((quote["remaining_mp"], quote["remaining_hp"], quote["remaining_actor_hp"]), (2, 800, 80))
        self.assertEqual((quote["self_damage"], quote["self_dealt"]), (20, 20))
