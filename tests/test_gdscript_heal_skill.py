"""単体HP回復の純粋予測を実GodotとPython正本で比較します。実セーブは使用しません。"""
# {
#   責務: [test_gdscript_heal_skill: HP回復上限・MP・厳密拒否・非破壊境界を検証します]
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
#   責務: [HealSkillBoundaryTests: 回復予測の純粋な依存とSession/画面への未接続を確認します]
#   フィールド: []
# }
class HealSkillBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_prediction_does_not_update_resources_or_depend_on_io: 保存・UI・AI・乱数・実資源更新への依存を拒否します]
    #   処理: [1: 純粋契約の禁止依存とapplicationの未接続を確認します]
    #   引数: [self: 予測の依存境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_prediction_does_not_update_resources_or_depend_on_io(self):
        # 数値成功は実回復・AI選択・復活・Scene接続の証拠ではない。
        source = (fixture.ROOT / "gdscript/engine/heal_skill_contract.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                          "battle_session", ".pay_mp(", ".heal(", "randf(", "RandomNumberGenerator"):
            self.assertNotIn(forbidden, source)
        for name in ("field_application", "battle_session_application"):
            source = (fixture.ROOT / f"gdscript/application/{name}.gd").read_text(encoding="utf-8")
            self.assertNotIn("heal_skill_contract", source)


# {
#   責務: [HealSkillQuoteTests: 共用fixtureの専用一時領域とPython比較先でHP回復の予測を確認します]
#   フィールド: [
#     folder: 共用fixtureが作る専用要求JSONの一時領域（Path）
#     document: 共用fixtureが読み取る正規スキル一覧のコピー（dict）
#     definitions: 正規定義をIDで検索する辞書（dict）
#     engine: 学習を無効にした実Python比較先（BattleEngine）
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real heal-skill probes")
class HealSkillQuoteTests(unittest.TestCase):
    # {
    #   責務: [setUp: 専用要求領域と学習しないPython比較先の準備を共用fixtureへ委譲します]
    #   処理: [1: 魔法予測fixtureの初期化を呼び、実セーブを使わない環境を保持します]
    #   引数: [self: 一時領域と比較先の所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        # 起動用fixtureを共用し、魔法予測のテスト自体は継承して再実行しない。
        magic_fixture.MagicSkillQuoteTests.setUp(self)

    # {
    #   責務: [run_probe: 共用プローブの起動・診断・要求JSONのbyte不変確認へ委譲します]
    #   処理: [1: 専用要求を共用fixtureに渡し、実Godotの観測を返します]
    #   引数: [
    #     self: 専用一時領域の所有者
    #     payload: ケースまたは計測条件（dict）
    #   ]
    #   戻り値: [result: 実Godotの観測結果（dict）]
    # }
    def run_probe(self, payload):
        return magic_fixture.MagicSkillQuoteTests.run_probe(self, payload)

    # {
    #   責務: [quote_case: HP回復契約を選択した独立要求を作ります]
    #   処理: [1: 定義コピーと基準資源へ個別変更を加えます]
    #   引数: [
    #     definition: 検証するHP回復定義（dict）
    #     changes: 基準資源から変える値（dict）
    #   ]
    #   戻り値: [result: 共用プローブのHP回復要求（dict）]
    # }
    @staticmethod
    def quote_case(definition, **changes):
        return {"heal": True, "operation": "quote", "definition": copy.deepcopy(definition),
                "request": {"current_mp": 10, "target_hp": 70, "target_max_hp": 100, **changes}}

    # {
    #   責務: [python_result: 実_take_actionのMP支払いとHP回復を呼び、元個体・AIと定義の不変を確認します]
    #   処理: [
    #     1: 元個体と独立した術者・対象を作ります
    #     2: 選択だけを固定して実HP回復処理を呼びます
    #     3: HP/MPと、学習・乱数が呼ばれないことを確認します
    #   ]
    #   引数: [
    #     self: Python比較先の所有者
    #     case: 明示したHP回復定義と資源（dict）
    #   ]
    #   戻り値: [result: 実回復量healed・残HP・消費後MP（dict）]
    # }
    def python_result(self, case):
        # 数値比較の対象は一体だけ。自動対象選択や死亡対象の許可は移植済みと扱わない。
        definition, request = case["definition"], case["request"]
        records = [MonsterRecord({"id": str(index), "name": "比較", "species_id": "slime"}, {"keep": [index]})
                   for index in range(2)]
        before = copy.deepcopy((records, definition))
        stats = {key: 1 for key in STAT_KEYS}
        stats.update(hp=51, mp=request["current_mp"], magic=999)
        actor = Combatant(records[0], stats, [definition], {}, equipment={"fixed_bonus_damage": 99})
        target = Combatant(records[1], {**stats, "hp": request["target_max_hp"]}, [], {"physical": "immune"})
        target.hp = request["target_hp"]
        target.guard = 0.5
        self.engine.inference.choose = mock.Mock(return_value=definition)
        self.engine.rng = mock.Mock()
        self.engine.log.clear()
        # 回復計算・支払いをmockへ置き換えず、治療対象の状態異常は与えない。
        self.engine._take_action(actor, [], [target])
        self.engine.inference.choose.assert_called_once()
        self.engine.learning.learn.assert_not_called()
        self.engine.rng.random.assert_not_called()
        self.engine.rng.uniform.assert_not_called()
        self.assertEqual((records, definition), before)
        return {"healed": target.hp - request["target_hp"], "remaining_hp": target.hp, "remaining_mp": actor.mp}

    # {
    #   責務: [test_canonical_and_mod_recovery_matches_python: 正規2スキルと有限MOD回復率のHP/MPを実Pythonと比較します]
    #   処理: [1: HP上限・回復率・MP境界の組合せを作り、実結果と非破壊予測を照合します]
    #   引数: [self: 回復互換性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_canonical_and_mod_recovery_matches_python(self):
        # HP0も数値比較に含めるが、Sessionでの復活や死亡対象選択を保証しない。
        cases = []
        for skill_id, maximum, position, extra_mp in itertools.product(
            ("small_heal", "healy"), (1, 19, 100, 1000), ("zero", "one", "almost", "full"), (0, 11),
        ):
            definition = self.definitions[skill_id]
            hp = {"zero": 0, "one": 1, "almost": maximum - 1, "full": maximum}[position]
            cases.append(self.quote_case(definition, target_max_hp=maximum, target_hp=hp,
                                         current_mp=definition["mp_cost"] + extra_mp))
        for ratio, hp, cost in itertools.product((-0.3, 0, 0.019, 0.33, 1.8, "0.22"), (0, 70, 100), (1.9, "2")):
            definition = {"id": "mod_heal", "display_name": "MOD回復", "kind": "heal", "heal_ratio": ratio, "mp_cost": cost}
            cases.append(self.quote_case(definition, target_hp=hp))
        cases.append(self.quote_case({"id": "default_heal", "display_name": "既定回復", "kind": "heal", "mp_cost": 2}))
        # 小数部分がない資源値は整数化できるが、文字列資源は別の拒否テストで禁止する。
        cases.append(self.quote_case(self.definitions["healy"], target_hp=70.0, target_max_hp=100.0, current_mp=10.0))
        observations = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        for case, observation in zip(cases, observations):
            with self.subTest(case=case):
                result = observation["result"]
                self.assertTrue(result["ok"], result)
                self.assertEqual({field: result[field] for field in ("healed", "remaining_hp", "remaining_mp")},
                                 self.python_result(case))
                expected_limit = max(1, int(case["request"]["target_max_hp"] * float(case["definition"].get("heal_ratio", 0.15))))
                self.assertEqual(result["heal_amount"], expected_limit)
                self.assertEqual(result["mp_cost"], int(case["definition"]["mp_cost"]))
                self.assertEqual(result["scope"], "heal_skill_quote")
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_prepare_validates_selection_and_supported_effects: 一意な選択と治療・他区分・未知効果の拒否を確認します]
    #   処理: [1: 正規・MOD・不正な一覧のprepareと、未知効果の直接quoteを照合します]
    #   引数: [self: 定義と一覧を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_prepare_validates_selection_and_supported_effects(self):
        # 正規一覧の未選択スキルを拒否せず、選択IDだけを検証する。
        cases = [{"heal": True, "operation": "prepare", "document": self.document, "skill_id": skill_id}
                 for skill_id in ("small_heal", "healy", "spirit_recover", "weaken", "possess", "attack", "missing")]
        for document in (None, [], {}, {"schema_version": True, "skills": []}, {"schema_version": 2, "skills": []},
                         {"schema_version": 1, "skills": {}},
                         {"schema_version": 1, "skills": [self.definitions["healy"], self.definitions["healy"]]}):
            cases.append({"heal": True, "operation": "prepare", "document": document, "skill_id": "healy"})
        for changes in ({"id": ""}, {"id": 2}, {"id": "defend"}, {"display_name": ""}, {"description": 1},
                        {"kind": "magic"}, {"mp_cost": 0}, {"mp_cost": -1}, {"mp_cost": 0.9},
                        {"mp_cost": True}, {"mp_cost": "1.9"}, {"heal_ratio": True}, {"heal_ratio": "no"}):
            definition = {**self.definitions["healy"], **changes}
            cases.append({"heal": True, "operation": "prepare", "document": {"schema_version": 1, "skills": [definition]},
                          "skill_id": definition["id"]})
        for field, value in itertools.product(("status_cure_chance", "power", "element", "target", "all_targets", "status_effect"),
                                              (False, 0, "", {}, [])):
            cases.append(self.quote_case({**self.definitions["healy"], field: value}))
        for index, observation in enumerate(self.run_probe({"cases": cases})["results"]):
            with self.subTest(case=cases[index]):
                result = observation["result"]
                self.assertEqual(result["ok"], index < 2, result)
                if index < 2:
                    self.assertEqual(result["skill"], self.definitions[cases[index]["skill_id"]])
                else:
                    self.assertIn("reason", result)
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_invalid_resources_numbers_and_unknown_requests_are_rejected: 不正資源・非有限値・未知要求・必要な積の精度超過を拒否します]
    #   処理: [1: 型・範囲・未知キー・native NaN/Infを注入し、拒否と入力不変を確認します]
    #   引数: [self: 不正数値と要求を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_resources_numbers_and_unknown_requests_are_rejected(self):
        cases = []
        for field, value in itertools.product(("current_mp", "target_hp", "target_max_hp"),
                                              (None, True, "10", -1, 1.5, 2**53)):
            cases.append(self.quote_case(self.definitions["healy"], **{field: value}))
        cases += [self.quote_case(self.definitions["healy"], target_max_hp=0),
                  self.quote_case(self.definitions["healy"], target_hp=101)]
        for field, value in itertools.product(("magic", "guard", "variance", "target_resistances", "equipment", "status_cure_chance"),
                                              (False, 0, {}, [])):
            cases.append(self.quote_case(self.definitions["healy"], **{field: value}))
        for target, fields in (("definition", ("mp_cost", "heal_ratio")),
                              ("request", ("current_mp", "target_hp", "target_max_hp"))):
            for field, value in itertools.product(fields, ("nan", "inf")):
                case = self.quote_case(self.definitions["healy"])
                case["special"] = [{"target": target, "field": field, "value": value}]
                cases.append(case)
        for field in ("mp_cost", "heal_ratio"):
            cases.append(self.quote_case({**self.definitions["healy"], field: 2**53}))
        for hp in (0, 2**52):
            cases.append(self.quote_case({**self.definitions["healy"], "heal_ratio": 2}, target_max_hp=2**52, target_hp=hp))
        for resource in (None, []):
            case = self.quote_case(self.definitions["healy"])
            case["request"] = resource
            cases.append(case)
        for field in ("current_mp", "target_hp", "target_max_hp"):
            case = self.quote_case(self.definitions["healy"])
            del case["request"][field]
            cases.append(case)
        case = self.quote_case(self.definitions["healy"])
        case["definition"] = None
        cases.append(case)
        for observation in self.run_probe({"cases": cases})["results"]:
            with self.subTest(result=observation):
                self.assertFalse(observation["result"]["ok"])
                self.assertIn("reason", observation["result"])
                self.assertTrue(observation["input_preserved"])

    # {
    #   責務: [test_mp_caps_precision_and_contract_routing: MP不足・上限近傍加算・他契約の拒否・区分同時指定を確認します]
    #   処理: [1: 資源境界と共用プローブの区分要求を用意し、期待結果を照合します]
    #   引数: [self: 境界と契約選択を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_mp_caps_precision_and_contract_routing(self):
        maximum = 2**53 - 1
        cases = [self.quote_case(self.definitions["small_heal"], current_mp=5),
                 self.quote_case(self.definitions["small_heal"], current_mp=6, target_hp=99),
                 self.quote_case(self.definitions["small_heal"], current_mp=6, target_hp=100),
                 self.quote_case({**self.definitions["small_heal"], "heal_ratio": 1},
                                 target_max_hp=maximum, target_hp=maximum - 1, current_mp=maximum)]
        for flag in (None, "self_damage", "drain_mp"):
            case = self.quote_case(self.definitions["healy"])
            del case["heal"]
            if flag:
                case[flag] = True
            cases.append(case)
        for flag in ("self_damage", "drain_mp"):
            cases.append({**self.quote_case(self.definitions["healy"]), flag: True})
        results = [entry["result"] for entry in self.run_probe({"cases": cases})["results"]]
        self.assertEqual(results[0]["reason"], "insufficient_mp")
        self.assertEqual((results[1]["healed"], results[1]["remaining_mp"]), (1, 0))
        self.assertEqual((results[2]["healed"], results[2]["heal_amount"], results[2]["remaining_mp"]), (0, 22, 0))
        self.assertEqual((results[3]["remaining_hp"], results[3]["healed"], results[3]["remaining_mp"]),
                         (maximum, 1, maximum - 6))
        for result in results[4:]:
            self.assertFalse(result["ok"], result)
        for flag in ("self_damage", "drain_mp"):
            result = self.run_probe({"performance": True, "heal": True, flag: True})
            self.assertEqual(result["reason"], "invalid_probe_contract")

    # {
    #   責務: [test_performance_probe_checks_capped_recovery_and_unchanged_inputs: 共用測定が正常な回復予測と入力保持を返すことを確認します]
    #   処理: [1: 小さい反復数で実Godotを測定し、回復上限量・実回復量・残資源を照合します]
    #   引数: [self: 回復性能プローブを検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_performance_probe_checks_capped_recovery_and_unchanged_inputs(self):
        result = self.run_probe({"performance": True, "heal": True, "iterations": 100, "samples": 3, "warmup": 10})
        self.assertTrue(result["input_preserved"])
        self.assertGreaterEqual(result["microseconds"], 0)
        self.assertEqual((result["current_mp"], result["target_hp"]), (10, 900))
        self.assertTrue(result["quote"]["ok"])
        self.assertEqual((result["quote"]["heal_amount"], result["quote"]["healed"],
                          result["quote"]["remaining_hp"], result["quote"]["remaining_mp"]), (220, 100, 1000, 4))
