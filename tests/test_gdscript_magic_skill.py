"""単体魔法の純粋予測を実GodotとPython正本で比較します。実セーブは使用しません。"""
# {
#   責務: [test_gdscript_magic_skill: 属性耐性・MP予測・未対応効果の拒否・入力不変を検証します]
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
from unittest import mock

import test_gdscript_roster as fixture
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.combatant import Combatant
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.repository import GameRepository, STAT_KEYS


# {
#   責務: [MagicSkillBoundaryTests: 魔法予測が保存・AI・Session更新・画面に依存しないことを確認します]
#   フィールド: []
# }
class MagicSkillBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_prediction_is_pure_and_not_connected_to_scene: 計算の依存と画面への未接続を確認します]
    #   処理: [
    #     1: 純粋計算の禁止依存を確認します
    #     2: applicationからの未接続を確認します
    #   ]
    #   引数: [self: 依存境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_prediction_is_pure_and_not_connected_to_scene(self):
        # 数値計算へ実資源更新やI/Oを紛れ込ませない。
        for name in ("magic_skill_contract", "magic_numbers"):
            source = (fixture.ROOT / f"gdscript/engine/{name}.gd").read_text(encoding="utf-8")
            for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                              "battle_session", ".pay_mp(", ".take_damage(", "randf(", "RandomNumberGenerator"):
                self.assertNotIn(forbidden, source)
        # 今回の予測を、実際の魔法行動の移植完了と取り違えない。
        for name in ("field_application", "battle_session_application"):
            source = (fixture.ROOT / f"gdscript/application/{name}.gd").read_text(encoding="utf-8")
            self.assertNotIn("magic_skill_contract", source)


# {
#   責務: [MagicSkillQuoteTests: 専用一時領域・実Godotプローブ・Python比較先を所有します]
#   フィールド: [
#     folder: プローブ要求JSONを保存する専用一時領域（Path）
#     document: 正規スキル一覧の読み取り専用コピー（dict）
#     definitions: 正規スキル定義をIDで検索する辞書（dict）
#     engine: AI学習を無効にした数値比較専用BattleEngine
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real magic-skill probes")
class MagicSkillQuoteTests(unittest.TestCase):
    # {
    #   責務: [setUp: 正規データと実セーブから独立した比較環境を作ります]
    #   処理: [
    #     1: 専用一時領域と定義コピーを作ります
    #     2: 学習しないPython比較先を用意します
    #   ]
    #   引数: [self: 専用領域と比較先の所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        # 一時要求JSON以外は書き換えない。
        temporary = tempfile.TemporaryDirectory(prefix="kadoka-magic-quote-")
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.document = json.loads((fixture.ROOT / "data/skills/skills.json").read_text(encoding="utf-8"))
        self.definitions = {entry["id"]: entry for entry in self.document["skills"]}
        # 選択・学習・MP支払いではなく、実_attackのHP計算だけを比較する。
        self.engine = BattleEngine(GameRepository(fixture.ROOT / "data"), [], [], learning_enabled=False)
        self.engine.learning.learn = mock.Mock()

    # {
    #   責務: [run_probe: 実Godotで専用要求を処理し、診断と要求ファイルの不変を確認します]
    #   処理: [
    #     1: 専用JSONを作ります
    #     2: Godotを起動して診断を確認します
    #     3: 結果とファイルの不変を確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域の所有者
    #     payload: 検証ケース配列または性能測定条件（dict）
    #   ]
    #   戻り値: [result: Godotプローブの観測結果（dict）]
    # }
    def run_probe(self, payload):
        # 正規data/assetsや利用者の保存先をプローブ出力先にしない。
        path = self.folder / "request.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        before = hashlib.sha256(path.read_bytes()).digest()
        process = subprocess.run(
            [str(fixture.GODOT), "--headless", "--path", str(fixture.ROOT / "gdscript"),
             "--script", "res://tests/run_magic_skill_probe.gd", "--", str(path)],
            cwd=self.folder, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        # 結果が出ても、解析や実行診断があれば検証失敗とする。
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        self.assertNotIn("SCRIPT ERROR", process.stderr)
        self.assertNotIn("ERROR:", process.stderr)
        self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)
        for line in process.stdout.splitlines():
            if line.startswith("KADOKA_MAGIC_SKILL_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(process.stderr + process.stdout)

    # {
    #   責務: [quote_request: ケース間で可変値を共有しない基準予測要求を作ります]
    #   処理: [1: 基準数値へケース固有の値を重ねます]
    #   引数: [changes: 基準値から変更する能力値・資源・耐性（dict）]
    #   戻り値: [result: 独立した予測要求（dict）]
    # }
    @staticmethod
    def quote_request(**changes):
        # 毎回新しい耐性辞書を作り、別ケースからの変更を防ぐ。
        return {"magic": 100, "target_hp": 700, "target_max_hp": 1000, "current_mp": 100,
                "target_resistances": {}, "variance": 1.0, **changes}

    # {
    #   責務: [python_hp_result: 実Pythonの魔法処理からHP変化を取り出し、元個体とAIの不変を確認します]
    #   処理: [
    #     1: 独立した戦闘個体を作ります
    #     2: 明示した揺らぎで実攻撃を呼びます
    #     3: HPと非呼出しを確認します
    #   ]
    #   引数: [
    #     self: Python比較先の所有者
    #     definition: 追加効果のない魔法定義（dict）
    #     request: 比較する魔力・資源・耐性・揺らぎ（dict）
    #   ]
    #   戻り値: [result: HP変化dealtと予測後HPのremaining_hp（dict）]
    # }
    def python_hp_result(self, definition, request):
        # AIと元レコードは戦闘用の一時個体とは独立している。
        records = [MonsterRecord({"id": str(index), "name": "比較", "species_id": "slime"}, {"keep": [index]})
                   for index in range(2)]
        before = copy.deepcopy(records)
        actor_stats = {key: 1 for key in STAT_KEYS}
        actor_stats.update(magic=int(request["magic"]), mp=request["current_mp"])
        target_stats = {**actor_stats, "hp": request["target_max_hp"], "defense": 999999}
        # Python魔法がスキル威力の装備倍率を使わないことも比較する。
        equipment = {"fixed_bonus_damage": request.get("fixed_bonus_damage", 0),
                     "skill_modifiers": {definition["id"]: {"power_multiplier": 99}}}
        actor = Combatant(records[0], actor_stats, [], {}, equipment=equipment)
        target = Combatant(records[1], target_stats, [], request.get("target_resistances", {}))
        target.hp = request["target_hp"]
        target.guard = request.get("guard", 1.0)
        self.engine.rng = mock.Mock()
        self.engine.rng.uniform.return_value = request["variance"]
        self.engine.log.clear()
        # 反撃とMP支払いは対象外。魔法数値はmockへ置き換えず、実処理を通す。
        self.engine._attack(actor, target, definition, allow_counter=False)
        self.engine.rng.random.assert_not_called()
        if target.resistances.get(definition.get("element", "physical")) == "immune":
            self.engine.rng.uniform.assert_not_called()
        else:
            self.engine.rng.uniform.assert_called_once_with(0.92, 1.08)
        self.engine.learning.learn.assert_not_called()
        self.assertEqual(records, before)
        self.assertEqual(actor.mp, request["current_mp"])
        return {"dealt": request["target_hp"] - target.hp, "remaining_hp": target.hp}

    # {
    #   責務: [test_resistance_matrix_matches_python: 正規魔法とMODの耐性・揺らぎ・装備・HP上限を実Pythonと比較します]
    #   処理: [
    #     1: 数値と耐性の組合せを作ります
    #     2: Godot結果をPythonと照合します
    #     3: MP予測とコピー独立性を確認します
    #   ]
    #   引数: [self: 魔法予測を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_resistance_matrix_matches_python(self):
        # 物理属性の魔法もguardを無視する。未指定・未知耐性も正本と比較する。
        definitions = [self.definitions["weaken"],
                       {"id": "mod_magic", "display_name": "MOD魔法", "kind": "magic", "mp_cost": 3, "power": 1.2}]
        cases = []
        for definition, resistance, magic, guard, variance, bonus, hp in itertools.product(
            definitions, ("normal", "weak", "strong", "immune", "absorb", "mod_unknown", None),
            (0, 17, 100), (1.0, 0.5), (0.92, 1.0, 1.08), (0, 3), (0, 700, 1000),
        ):
            element = definition.get("element", "physical")
            request = self.quote_request(magic=magic, guard=guard, variance=variance,
                                         fixed_bonus_damage=bonus, target_hp=hp,
                                         target_resistances={} if resistance is None else {element: resistance})
            cases.append({"operation": "quote", "definition": definition, "request": request})
        observations = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        # 予測後MPは計算だけであり、実MPを消費した証拠にはしない。
        for case, observation in zip(cases, observations):
            with self.subTest(definition=case["definition"], request=case["request"]):
                result = observation["result"]
                self.assertTrue(result["ok"], result)
                expected = self.python_hp_result(case["definition"], case["request"])
                for field, value in expected.items():
                    self.assertEqual(result[field], value)
                self.assertEqual(result["remaining_mp"], 100 - int(case["definition"]["mp_cost"]))
                self.assertEqual(result["applied_guard"], 1.0)
                self.assertEqual(result["healed"], max(0, -expected["dealt"]))
                self.assertEqual(result["resistance_known"],
                                 result["resistance_kind"] in ("normal", "weak", "strong", "immune", "absorb"))
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_finite_mod_values_match_python: 有限MOD数値と既定威力・属性・整数化の互換性を確認します]
    #   処理: [
    #     1: 正負の威力と魔力のケースを作ります
    #     2: 実PythonとGodotのHP変化を比較します
    #   ]
    #   引数: [self: MOD数値を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_finite_mod_values_match_python(self):
        # 負の威力でも通常耐性は最低1、吸収耐性は絶対値による回復になる。
        cases = []
        for power, magic, resistance in itertools.product((-1.1, 0, 0.33, 1.5, "1.2"), (-3, 1, 123), ("normal", "absorb")):
            definition = {"id": "mod", "display_name": "MOD", "kind": "magic", "mp_cost": 1.9, "power": power}
            request = self.quote_request(magic=magic, fixed_bonus_damage=-2.9,
                                         target_resistances={"physical": resistance})
            cases.append({"operation": "quote", "definition": definition, "request": request})
        definition = {"id": "defaults", "display_name": "既定値", "kind": "magic", "mp_cost": "2"}
        cases.append({"operation": "quote", "definition": definition, "request": self.quote_request()})
        # 別属性の未対応値をこの魔法の耐性として誤用しない。
        cases.append({"operation": "quote", "definition": definition,
                      "request": self.quote_request(target_resistances={"mental": {"future": True}})})
        results = self.run_probe({"cases": cases})["results"]
        for case, observation in zip(cases, results):
            with self.subTest(case=case):
                result = observation["result"]
                self.assertTrue(result["ok"], result)
                self.assertEqual({field: result[field] for field in ("dealt", "remaining_hp")},
                                 self.python_hp_result(case["definition"], case["request"]))
                self.assertEqual(result["remaining_mp"], 100 - int(case["definition"]["mp_cost"]))

    # {
    #   責務: [test_prepare_rejects_missing_duplicate_and_unsupported_definitions: 定義選択の一意性・対応範囲・型を確認します]
    #   処理: [
    #     1: 正規と不正な定義一覧を用意します
    #     2: 成功・拒否と元入力の不変を照合します
    #   ]
    #   引数: [self: 定義検証のテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_prepare_rejects_missing_duplicate_and_unsupported_definitions(self):
        # 正規の自傷付き魔法・吸MP・ランダム魔法を、通常魔法へ偽装しない。
        cases = [{"operation": "prepare", "document": self.document, "skill_id": "weaken"}]
        for skill_id in ("metal_burst", "possess", "dice_magic", "attack", "missing"):
            cases.append({"operation": "prepare", "document": self.document, "skill_id": skill_id})
        cases.append({"operation": "prepare", "document": {"schema_version": 1, "skills": [
            self.definitions["weaken"], self.definitions["weaken"]]}, "skill_id": "weaken"})
        for document in (None, [], {}, {"schema_version": True, "skills": []},
                         {"schema_version": 2, "skills": []}, {"schema_version": 1, "skills": {}}):
            cases.append({"operation": "prepare", "document": document, "skill_id": "weaken"})
        for changes in ({"display_name": ""}, {"description": 1}, {"element": ""},
                        {"mp_cost": 0}, {"power": True}, {"kind": "physical"}):
            definition = {**self.definitions["weaken"], **changes}
            cases.append({"operation": "prepare", "document": {"schema_version": 1, "skills": [definition]},
                          "skill_id": "weaken"})
        for field in ("self_damage_ratio", "status_effect", "target", "all_targets", "drain_mp", "critical_multiplier"):
            definition = {**self.definitions["weaken"], field: False}
            cases.append({"operation": "quote", "definition": definition, "request": self.quote_request()})
        results = self.run_probe({"cases": cases})["results"]
        self.assertTrue(results[0]["result"]["ok"])
        self.assertEqual(results[0]["result"]["skill"], self.definitions["weaken"])
        for observation in results:
            self.assertTrue(observation["input_preserved"])
            self.assertTrue(observation["result_independent"])
        for observation in results[1:]:
            with self.subTest(result=observation):
                self.assertFalse(observation["result"]["ok"])
                self.assertIn("reason", observation["result"])

    # {
    #   責務: [test_invalid_requests_and_native_nonfinite_values_are_rejected: 不正資源・未対応効果・非有限値・精度超過を拒否します]
    #   処理: [
    #     1: 不正型と境界外のケースを作ります
    #     2: Godot固有の非有限値も注入します
    #     3: 拒否と入力保持を確認します
    #   ]
    #   引数: [self: 不正入力を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_requests_and_native_nonfinite_values_are_rejected(self):
        # 現在資源は小数切捨てや文字列変換で補修しない。
        changes = [{"current_mp": value} for value in (None, True, "100", -1, 1.5, 2**53)]
        changes += [{"target_hp": value} for value in (None, True, "1", -1, 1.5, 1001, 2**53)]
        changes += [{"target_max_hp": value} for value in (None, True, "1000", 0, 1.5, 2**53)]
        changes += [{"magic": value} for value in (None, True, "no", 2**53)]
        changes += [{"variance": value} for value in (None, True, 0.919, 1.081)]
        changes += [{"target_resistances": value} for value in (None, [], {"mental": False}, {"mental": {}})]
        changes += [{field: False} for field in ("evade_element", "counter_ready", "power_multiplier",
                                                  "attack_multiplier", "equipment", "target_mp", "critical_roll")]
        cases = [{"operation": "quote", "definition": self.definitions["weaken"],
                  "request": self.quote_request(**change)} for change in changes]
        # 有限入力同士の乗算が精度上限を超えるケースも拒否する。
        cases.append({"operation": "quote", "definition": {**self.definitions["weaken"], "power": 2},
                      "request": self.quote_request(magic=2**52)})
        for target, fields in (("definition", ("power", "mp_cost")), ("request", (
                "magic", "target_hp", "target_max_hp", "current_mp", "variance", "guard", "fixed_bonus_damage"))):
            for field, value in itertools.product(fields, ("nan", "inf")):
                cases.append({"operation": "quote", "definition": self.definitions["weaken"],
                              "request": self.quote_request(),
                              "special": [{"target": target, "field": field, "value": value}]})
        for observation in self.run_probe({"cases": cases})["results"]:
            with self.subTest(result=observation):
                self.assertFalse(observation["result"]["ok"])
                self.assertIn("reason", observation["result"])
                self.assertTrue(observation["input_preserved"])

    # {
    #   責務: [test_mp_boundary_and_resource_caps: MP不足・ちょうどの支払い予測・吸収上限・無効を確認します]
    #   処理: [
    #     1: MPと回復の境界を用意します
    #     2: 結果と実入力の不変を確認します
    #   ]
    #   引数: [self: 資源境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_mp_boundary_and_resource_caps(self):
        # 無効・吸収でも予測MPは減るが、満HPの吸収ではHPは増えない。
        requests = [self.quote_request(current_mp=4), self.quote_request(current_mp=5),
                    self.quote_request(current_mp=5, target_hp=999, target_resistances={"mental": "absorb"}),
                    self.quote_request(current_mp=5, target_hp=1000, target_resistances={"mental": "absorb"}),
                    self.quote_request(current_mp=5, target_resistances={"mental": "immune"})]
        results = self.run_probe({"cases": [{"operation": "quote", "definition": self.definitions["weaken"],
                                             "request": request} for request in requests]})["results"]
        self.assertEqual(results[0]["result"]["reason"], "insufficient_mp")
        self.assertEqual([entry["result"]["remaining_mp"] for entry in results[1:]], [0, 0, 0, 0])
        self.assertEqual(results[2]["result"]["dealt"], -1)
        self.assertEqual(results[3]["result"]["dealt"], 0)
        self.assertEqual(results[4]["result"]["effect"], "immune")
        for observation in results:
            self.assertTrue(observation["input_preserved"])
            self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_performance_probe_reports_real_prediction_without_mutation: 性能経路が正常な予測と入力保持を測ることを確認します]
    #   処理: [
    #     1: 小さい反復数で実Godot計測を呼びます
    #     2: 予測結果と入力保持を照合します
    #   ]
    #   引数: [self: 性能プローブのテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_performance_probe_reports_real_prediction_without_mutation(self):
        # 時間値だけでは、正常な魔法予測が行われたとは判定しない。
        result = self.run_probe({"performance": True, "iterations": 100, "samples": 3, "warmup": 10})
        self.assertGreaterEqual(result["microseconds"], 0)
        self.assertTrue(result["input_preserved"])
        self.assertEqual((result["current_mp"], result["target_hp"]), (10, 1000))
        self.assertEqual((result["quote"]["remaining_mp"], result["quote"]["remaining_hp"]), (5, 945))
