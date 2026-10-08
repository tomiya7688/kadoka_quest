"""吸MP付き単体魔法の純粋予測を実GodotとPython正本で比較します。実セーブは使用しません。"""
# {
#   責務: [test_gdscript_drain_mp_skill: 敵HP・敵MP喪失・術者MP回復・厳密拒否・入力不変を検証します]
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
#   責務: [DrainMpBoundaryTests: 吸MP予測が実資源更新・AI・I/O・画面から独立しているか確認します]
#   フィールド: []
# }
class DrainMpBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_prediction_has_no_state_or_scene_dependency: 純粋予測のI/O不使用と、applicationが数値計算を所有しない境界を確認します]
    #   処理: [
    #     1: 吸MP契約の禁止依存を確認します
    #     2: 呼び出し層と通常魔法契約が吸MP数値予測を直接所有していないか確認します
    #   ]
    #   引数: [self: 予測の依存境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_prediction_has_no_state_or_scene_dependency(self):
        # 予測に実資源更新や乱数源を混ぜない。
        source = (fixture.ROOT / "gdscript/engine/drain_mp_skill_contract.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                          "battle_session", ".pay_mp(", ".take_damage(", "randf(", "RandomNumberGenerator"):
            self.assertNotIn(forbidden, source)
        # 専用区分の実適用を魔法行動へ接続しても、applicationやSceneへ数値計算を移しません。
        for name in ("application/battle_session_application", "application/field_application",
                     "engine/magic_skill_contract"):
            self.assertNotIn("drain_mp_skill_contract",
                             (fixture.ROOT / f"gdscript/{name}.gd").read_text(encoding="utf-8"))


# {
#   責務: [DrainMpQuoteTests: 独立した数値要求とPython比較先を所有し、実Godotの吸MP予測を検証します]
#   フィールド: [
#     folder: 共用fixtureが作る専用要求JSONの一時領域（Path）
#     document: 正規スキル一覧の読み取り専用コピー（dict）
#     definitions: 正規スキル定義をIDで検索する辞書（dict）
#     engine: AI学習を無効にした一時BattleEngine
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real drain-MP probes")
class DrainMpQuoteTests(unittest.TestCase):
    # {
    #   責務: [setUp: 実セーブを使用せず、共用fixtureで専用一時領域とPython比較先を用意します]
    #   処理: [1: 通常魔法fixtureの環境作成だけを共用します]
    #   引数: [self: 専用領域と比較先の所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        # fixtureクラスを継承せず、通常魔法のテスト自体は再登録しない。
        magic_fixture.MagicSkillQuoteTests.setUp(self)

    # {
    #   責務: [run_probe: コピーした専用要求で吸MP契約を選択し、共用の実Godot観測へ委譲します]
    #   処理: [1: 性能要求または各ケースへ吸MP契約選択を加えて実Godotを呼びます]
    #   引数: [
    #     self: 専用一時領域の所有者
    #     payload: ケース配列または性能測定条件（dict）
    #   ]
    #   戻り値: [result: 診断と入力ファイル不変を確認したGodot観測結果（dict）]
    # }
    def run_probe(self, payload):
        # 呼出元のpayloadを変更せず、プローブの種類だけを指定する。
        selected = copy.deepcopy(payload)
        if selected.get("performance"):
            selected["drain_mp"] = True
        for case in selected.get("cases", []):
            case["drain_mp"] = True
        return magic_fixture.MagicSkillQuoteTests.run_probe(self, selected)

    # {
    #   責務: [quote_request: ケース間でMP資源と耐性を共有しない基準要求を作ります]
    #   処理: [1: 基準要求へケース固有の変更を重ねます]
    #   引数: [changes: 魔力・資源・耐性・揺らぎの変更値（dict）]
    #   戻り値: [result: 独立した吸MP数値要求（dict）]
    # }
    @staticmethod
    def quote_request(**changes):
        # 毎回新しい耐性辞書を作り、術者の現在MPと最大MPを分離する。
        return {"magic": 100, "target_hp": 700, "target_max_hp": 1000,
                "current_mp": 100, "actor_max_mp": 100, "target_mp": 80,
                "target_resistances": {}, "variance": 1.0, **changes}

    # {
    #   責務: [python_result: MP支払い後の一時個体に実Python攻撃を適用し、HPとMP移転を比較値として返します]
    #   処理: [
    #     1: 予測用のMP消費量を引いた独立戦闘個体を作ります
    #     2: 明示した揺らぎで実Pythonの吸MP攻撃を呼びます
    #     3: HP・敵MP喪失・術者MP回復と元個体/AIの不変を確認します
    #   ]
    #   引数: [
    #     self: Python比較先の所有者
    #     definition: 有限値を持つ吸MP付き魔法定義（dict）
    #     request: 比較する魔力・HP/MP・耐性・揺らぎ（dict）
    #   ]
    #   戻り値: [result: 実攻撃後HP/MPと予測用の支払い直後MP（dict）。実行動のMP支払いは検証対象外です]
    # }
    def python_result(self, definition, request):
        # MP支払いの実行動は呼ばず、既存_attackへ渡す支払い後の数値を作る。
        records = [MonsterRecord({"id": str(index), "name": "比較", "species_id": "slime"}, {"keep": [index]})
                   for index in range(2)]
        before = copy.deepcopy(records)
        stats = {key: 1 for key in STAT_KEYS}
        stats.update(magic=int(request["magic"]), mp=request["actor_max_mp"])
        paid_mp = request["current_mp"] - int(definition["mp_cost"])
        equipment = {"fixed_bonus_damage": request.get("fixed_bonus_damage", 0),
                     "skill_modifiers": {definition["id"]: {"power_multiplier": 99}}}
        actor = Combatant(records[0], stats, [], {}, equipment=equipment)
        target = Combatant(records[1], {**stats, "hp": request["target_max_hp"], "defense": 999999},
                           [], request.get("target_resistances", {}))
        actor.mp = paid_mp
        target.hp, target.mp = request["target_hp"], request["target_mp"]
        target.guard = request.get("guard", 1.0)
        self.engine.rng = mock.Mock()
        self.engine.rng.uniform.return_value = request["variance"]
        self.engine.log.clear()
        # 数値計算をmockへ置き換えず、反撃・学習・保存だけを比較対象から外す。
        self.engine._attack(actor, target, definition, allow_counter=False)
        self.engine.rng.random.assert_not_called()
        if target.resistances.get(definition.get("element", "physical")) == "immune":
            self.engine.rng.uniform.assert_not_called()
        else:
            self.engine.rng.uniform.assert_called_once_with(0.92, 1.08)
        self.engine.learning.learn.assert_not_called()
        self.assertEqual(records, before)
        return {"dealt": request["target_hp"] - target.hp, "remaining_hp": target.hp,
                "mp_after_payment": paid_mp, "remaining_mp": actor.mp, "remaining_target_mp": target.mp,
                "drained_mp": request["target_mp"] - target.mp, "recovered_mp": actor.mp - paid_mp}

    # {
    #   責務: [assert_matches_python: 実Godotの吸MP予測をPython数値と比較し、入力と返却値の独立性を確認します]
    #   処理: [1: 各ケースの成功・数値一致・コピー独立性を確認します]
    #   引数: [
    #     self: 数値比較を実行するテストケース
    #     cases: 吸MP定義と数値要求の配列（list[dict]）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def assert_matches_python(self, cases):
        # 成功件数だけでなく、敵の損失と術者の回復を別々に照合する。
        observed = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(observed), len(cases))
        for case, entry in zip(cases, observed):
            with self.subTest(definition=case["definition"], request=case["request"]):
                quote = entry["result"]
                self.assertTrue(quote["ok"], quote)
                self.assertTrue(entry["input_preserved"])
                self.assertTrue(entry["result_independent"])
                self.assertEqual(quote["scope"], "drain_mp_skill_quote")
                for key, value in self.python_result(case["definition"], case["request"]).items():
                    self.assertEqual(quote[key], value, key)

    # {
    #   責務: [test_resistance_resource_matrix_matches_python: 耐性・倒れる敵・MP上限・揺らぎ・装備加算を実Pythonと比較します]
    #   処理: [1: 正規possessの組合せを作り、HP/MP予測を実Pythonへ照合します]
    #   引数: [self: 組合せ比較を実行するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_resistance_resource_matrix_matches_python(self):
        # HP0でも吸MPは発生する。無効/吸収は支払い後のMPを回復しない。
        cases = []
        for resistance, hp, target_mp, current_mp, variance, bonus in itertools.product(
            ("normal", "weak", "strong", "immune", "absorb", "mod_unknown", None),
            (0, 1, 700, 1000), (0, 1, 7, 80), (5, 90, 100), (0.92, 1.08), (0, 11),
        ):
            request = self.quote_request(target_hp=hp, target_mp=target_mp, current_mp=current_mp,
                                         variance=variance, fixed_bonus_damage=bonus, guard=0.5,
                                         target_resistances={} if resistance is None else {"mental": resistance})
            cases.append({"operation": "quote", "definition": self.definitions["possess"], "request": request})
        self.assert_matches_python(cases)

    # {
    #   責務: [test_mod_defaults_and_mp_capacity_match_python: 既定値・文字列数値・最低1MP吸収・術者の回復上限を照合します]
    #   処理: [
    #     1: MODの有限係数と既定値の組合せを比較します
    #     2: 敵から14MP奪って術者が5MPだけ回復する満タンケースを確認します
    #   ]
    #   引数: [self: MOD数値とMP上限を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_mod_defaults_and_mp_capacity_match_python(self):
        # 負/0係数でも最低1MP。耐性倍率・防御倍率・揺らぎはMP量に掛けない。
        cases = []
        for mp_power, magic, power in itertools.product((None, -0.5, 0, 0.14, "0.2", 1.2), (-10, 0, 17, "100"), (-1, 0.25)):
            definition = {"id": "mod_drain", "display_name": "MOD吸MP", "kind": "drain_mp", "mp_cost": "2", "power": power}
            if mp_power is not None:
                definition["mp_power"] = mp_power
            cases.append({"operation": "quote", "definition": definition,
                          "request": self.quote_request(magic=magic, guard=0.2, variance=1.08)})
        # 省略したpower/elementもPythonと同じ既定値を使う。MP消費は0方向へ切り捨てる。
        cases.append({"operation": "quote", "definition": {"id": "defaults", "display_name": "既定吸MP",
                      "kind": "drain_mp", "mp_cost": 1.9}, "request": self.quote_request(current_mp=1)})
        self.assert_matches_python(cases)
        quote = self.run_probe({"cases": [{"operation": "quote", "definition": self.definitions["possess"],
                                          "request": self.quote_request()}]})["results"][0]["result"]
        self.assertEqual((quote["drained_mp"], quote["recovered_mp"], quote["remaining_mp"], quote["remaining_target_mp"]),
                         (14, 5, 100, 66))

    # {
    #   責務: [test_definition_selection_and_unsupported_effects: 一意な吸MP選択と、未対応効果/不正な定義の拒否を検証します]
    #   処理: [
    #     1: 正規possessの独立定義を確認します
    #     2: 未対応区分・未知キー・不正数値・一覧不整合を拒否するか確認します
    #   ]
    #   引数: [self: 定義の対応境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_definition_selection_and_unsupported_effects(self):
        # 既存スキルの追加効果を捨てて、吸MPとして成功させない。
        good = self.definitions["possess"]
        success = self.run_probe({"cases": [{"operation": "prepare", "document": self.document, "skill_id": "possess"}]})["results"][0]
        self.assertTrue(success["result"]["ok"])
        self.assertEqual(success["result"]["skill"]["kind"], "drain_mp")
        self.assertEqual(success["result"]["skill"]["mp_power"], 0.14)
        self.assertTrue(success["input_preserved"] and success["result_independent"])
        definitions = [None, [], {}, self.definitions["weaken"], self.definitions["metal_burst"],
                       {**good, "kind": False}, {**good, "id": "attack"}, {**good, "display_name": ""},
                       {**good, "description": False}, {**good, "element": ""}, {**good, "mp_cost": 0}]
        definitions += [{**good, key: value} for key in ("self_damage_ratio", "status_effects", "target_all", "unknown")
                        for value in (0, False, "", [])]
        definitions += [{**good, "mp_power": value} for value in (None, True, [], {}, "NaN", "Inf", 2**53)]
        cases = [{"operation": "quote", "definition": definition, "request": self.quote_request()} for definition in definitions]
        cases += [{"operation": "prepare", "document": document, "skill_id": skill_id}
                  for document, skill_id in ((self.document, "missing"), (self.document, ""),
                                             ({**self.document, "schema_version": True}, "possess"),
                                             ({"schema_version": 1, "skills": [good, good]}, "possess"))]
        for value in ("nan", "inf"):
            cases.append({"operation": "quote", "definition": good, "request": self.quote_request(),
                          "special": [{"target": "definition", "field": "mp_power", "value": value}]})
        for entry in self.run_probe({"cases": cases})["results"]:
            with self.subTest(result=entry):
                self.assertFalse(entry["result"]["ok"])
                self.assertTrue(entry["result"]["reason"])
                self.assertTrue(entry["input_preserved"] and entry["result_independent"])
        # 通常魔法/自傷契約は吸MPを受け入れない。区分の同時指定も拒否する。
        results = magic_fixture.MagicSkillQuoteTests.run_probe(self, {"cases": [
            {"operation": "quote", "definition": {**good, "mp_power": 0}, "request": self.quote_request()},
            {"operation": "quote", "self_damage": True, "definition": good, "request": self.quote_request()},
            {"operation": "quote", "self_damage": True, "drain_mp": True, "definition": good, "request": self.quote_request()},
        ]})["results"]
        self.assertTrue(all(not entry["result"]["ok"] for entry in results))

    # {
    #   責務: [test_invalid_resources_and_unknown_requests_are_rejected: 不正MP・未対応要求・MP不足・非有限入力を拒否するか確認します]
    #   処理: [1: 資源と未対応フィールドの不正ケースを作り、理由付き拒否と入力不変を確認します]
    #   引数: [self: 数値要求の境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_resources_and_unknown_requests_are_rejected(self):
        # MPは能力値の文字列変換とは区別し、現在値/最大値とも正規整数に限定する。
        requests = [None, [], self.quote_request(current_mp=101), self.quote_request(current_mp=4),
                    self.quote_request(current_mp=0, actor_max_mp=0)]
        for field in ("current_mp", "actor_max_mp", "target_mp"):
            requests += [self.quote_request(**{field: value}) for value in (-1, True, None, "5", 1.5, 2**53)]
            missing = self.quote_request()
            missing.pop(field)
            requests.append(missing)
        for field in ("actor_hp", "target_max_mp", "alive", "equipment", "critical", "unknown"):
            requests += [self.quote_request(**{field: value}) for value in (0, False, "", [])]
        requests += [self.quote_request(**{field: value}) for field, value in (
            ("guard", "NaN"), ("variance", "Inf"), ("magic", True), ("target_hp", -1),
            ("target_resistances", {"mental": 0}), ("fixed_bonus_damage", 2**53))]
        cases = [{"operation": "quote", "definition": self.definitions["possess"], "request": request} for request in requests]
        for field, value in itertools.product(("current_mp", "actor_max_mp", "target_mp", "guard", "variance", "magic"), ("nan", "inf")):
            cases.append({"operation": "quote", "definition": self.definitions["possess"], "request": self.quote_request(),
                          "special": [{"target": "request", "field": field, "value": value}]})
        for entry in self.run_probe({"cases": cases})["results"]:
            with self.subTest(result=entry):
                self.assertFalse(entry["result"]["ok"])
                self.assertTrue(entry["result"]["reason"])
                self.assertTrue(entry["input_preserved"] and entry["result_independent"])

    # {
    #   責務: [test_exact_integer_limits_and_blocked_transfer: 精度上限内の回復加算と、無効/吸収で未使用のMP積を計算しない契約を確認します]
    #   処理: [
    #     1: 最大MP近傍で術者回復だけを先に制限するケースをPythonと比較します
    #     2: 必要なMP積の精度超過を拒否し、無効/吸収では未使用積を計算しないか確認します
    #   ]
    #   引数: [self: 演算精度と耐性による分岐を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_exact_integer_limits_and_blocked_transfer(self):
        # 支払い後MPと敵喪失量を先に足すと精度超過するが、回復上限の適用後は正確に表せる。
        maximum = 2**53 - 1
        self.assert_matches_python([{"operation": "quote", "definition": self.definitions["possess"],
                                     "request": self.quote_request(current_mp=maximum, actor_max_mp=maximum, target_mp=maximum)}])
        definition = {**self.definitions["possess"], "mp_power": maximum}
        cases = [{"operation": "quote", "definition": definition,
                  "request": self.quote_request(target_resistances={"mental": resistance})}
                 for resistance in ("normal", "immune", "absorb")]
        results = self.run_probe({"cases": cases})["results"]
        self.assertEqual(results[0]["result"], {"ok": False, "reason": "invalid_drain_mp_numbers"})
        for case, entry in zip(cases[1:], results[1:]):
            with self.subTest(resistance=case["request"]["target_resistances"]):
                self.assertTrue(entry["result"]["mp_drain_blocked"])
                self.assertEqual(entry["result"]["mp_drain_limit"], 0)
                for key, value in self.python_result(case["definition"], case["request"]).items():
                    self.assertEqual(entry["result"][key], value)

    # {
    #   責務: [test_performance_probe_measures_real_transfer: 小規模反復で計測経路が吸MPを含む成功予測と入力保持を観測するか確認します]
    #   処理: [1: 小規模の実Godot計測を呼び、HP975・術者MP19・敵MP66と元資源保持を確認します]
    #   引数: [self: 計測経路を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_performance_probe_measures_real_transfer(self):
        # 時間の短い拒否や、MP移転を省いた予測を正常性能として扱わない。
        result = self.run_probe({"performance": True, "iterations": 100, "samples": 3, "warmup": 10})
        quote = result["quote"]
        self.assertTrue(quote["ok"] and result["input_preserved"])
        self.assertEqual((quote["remaining_hp"], quote["remaining_mp"], quote["remaining_target_mp"]), (975, 19, 66))
        self.assertEqual((quote["drained_mp"], quote["recovered_mp"], quote["mp_after_payment"]), (14, 14, 5))
        self.assertEqual((result["current_mp"], result["actor_max_mp"], result["target_mp"]), (10, 30, 80))
        self.assertGreaterEqual(result["microseconds"], 0)


if __name__ == "__main__":
    unittest.main()
