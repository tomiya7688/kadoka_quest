"""MP付き物理スキルの純粋予測を実GodotとPython正本で比較する。実セーブは使わない。"""
# {
#   責務: [test_gdscript_physical_skill: 定義検証・物理数値・入力不変・未接続境界の回帰検証]
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
#   責務: [PhysicalSkillBoundaryTests: 純粋契約の依存境界とScene未接続を確認する]
#   フィールド: []
# }
class PhysicalSkillBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_contract_has_no_persistence_ai_or_scene_dependencies: 状態更新とI/Oを数値予測へ持ち込まない]
    #   処理: [1: 契約の依存とScene側の未接続を確認する]
    #   引数: [self: 境界検証ケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_contract_has_no_persistence_ai_or_scene_dependencies(self):
        # 純粋契約からSession・永続化・乱数源・描画へ依存しない。
        source = (fixture.ROOT / "gdscript/engine/physical_skill_contract.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "res://application/", "res://data/", "res://ui/",
                          "battle_session", ".pay_mp(", ".take_damage(", "randf(", "RandomNumberGenerator"):
            self.assertNotIn(forbidden, source)
        scene = (fixture.ROOT / "gdscript/application/field_application.gd").read_text(encoding="utf-8")
        self.assertNotIn("physical_skill_contract", scene)


# {
#   責務: [PhysicalSkillQuoteTests: 専用fixture・Python比較先・Godotプローブを所有する]
#   フィールド: [
#     folder: 一時fixtureの保存先（Path）
#     document: 正規skillsの読み取り専用コピー（dict）
#     definitions: ID別の正規定義（dict）
#     engine: 比較専用の学習しないPython BattleEngine
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real physical-skill probes")
class PhysicalSkillQuoteTests(unittest.TestCase):
    # {
    #   責務: [setUp: 実セーブを使わず予測比較のfixtureを準備する]
    #   処理: [
    #     1: 専用の一時領域と正規定義のコピーを用意する
    #     2: 学習しないPython比較先を作る
    #   ]
    #   引数: [self: 予測検証ケース]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        # プローブだけが書く一時領域を所有し、利用者の保存先を参照しない。
        temporary = tempfile.TemporaryDirectory(prefix="kadoka-physical-quote-")
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.document = json.loads((fixture.ROOT / "data/skills/skills.json").read_text(encoding="utf-8"))
        self.definitions = {entry["id"]: entry for entry in self.document["skills"]}
        # 比較は実BattleEngine._attackの数値だけ。AI選択・学習・保存は呼ばない。
        repository = GameRepository(fixture.ROOT / "data")
        self.engine = BattleEngine(repository, [], [], learning_enabled=False)
        self.engine.learning.learn = mock.Mock()

    # {
    #   責務: [run_probe: 専用fixtureで実Godotを起動し、契約結果を読み取る]
    #   処理: [
    #     1: 要求を専用JSONへ保存する
    #     2: 実Godotの終了と診断を確認する
    #     3: 結果を読み、fixtureのbyte不変を確認する
    #   ]
    #   引数: [
    #     self: 専用fixtureの所有者
    #     payload: ケースまたは性能測定の要求（dict）
    #   ]
    #   戻り値: [result: Godotが返した観測結果（dict）]
    # }
    def run_probe(self, payload):
        # 作成するのは専用fixtureだけ。正規data/assetsや実セーブは書き換えない。
        path = self.folder / "request.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        before = hashlib.sha256(path.read_bytes()).digest()
        process = subprocess.run(
            [str(fixture.GODOT), "--headless", "--path", str(fixture.ROOT / "gdscript"),
             "--script", "res://tests/run_physical_skill_probe.gd", "--", str(path)],
            cwd=self.folder, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        # 結果が出ていてもエンジン診断を成功として扱わない。
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        self.assertNotIn("SCRIPT ERROR", process.stderr)
        self.assertNotIn("ERROR:", process.stderr)
        self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)
        for line in process.stdout.splitlines():
            if line.startswith("KADOKA_PHYSICAL_SKILL_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(process.stderr + process.stdout)

    # {
    #   責務: [quote_request: 比較に必要な数値だけの予測要求を作る]
    #   処理: [1: 基準値とケース別の値を結合する]
    #   引数: [
    #     changes: ケース別の数値入力
    #   ]
    #   戻り値: [result: actor/targetを所有しない予測入力（dict）]
    # }
    @staticmethod
    def quote_request(**changes):
        # ケースごとに独立した辞書を返し、資源値を別ケースと共有しない。
        return {"attack": 100, "defense": 50, "target_hp": 1000, "current_mp": 100,
                "critical_roll": 0.5, "variance": 1.0, **changes}

    # {
    #   責務: [python_attack_result: 実Pythonの物理処理から比較するHP減少・会心情報を得る]
    #   処理: [
    #     1: 元レコードと分離した戦闘個体を作る
    #     2: 装備数値と明示乱数を設定する
    #     3: 実攻撃を呼び、レコードとAIの不変を確認する
    #   ]
    #   引数: [
    #     self: 比較用BattleEngineの所有者
    #     definition: 正規または専用MODスキル定義（dict）
    #     request: 比較する数値（dict）
    #   ]
    #   戻り値: [result: dealt/remaining_hp/critical（dict）]
    # }
    def python_attack_result(self, definition, request):
        # 原本と学習AIは戦闘の一時効果から独立していることを確認する。
        actor_record = MonsterRecord({"id": "actor", "name": "行動者", "species_id": "slime"}, {"keep": [1]})
        target_record = MonsterRecord({"id": "target", "name": "対象", "species_id": "slime"}, {"keep": [2]})
        before = copy.deepcopy([actor_record, target_record])
        actor_stats = {key: 1 for key in STAT_KEYS}
        target_stats = dict(actor_stats)
        actor_stats.update(attack=int(request["attack"]), mp=request["current_mp"])
        target_stats.update(defense=int(request["defense"]), hp=max(1, int(request["target_hp"])))
        # 通常attackの倍率をわざと変え、他スキルに流用していないことを検証する。
        equipment = {"skill_modifiers": {
            "attack": {"power_multiplier": 99},
            definition["id"]: {"power_multiplier": request.get("power_multiplier", 1.0)},
        }, "fixed_bonus_damage": request.get("fixed_bonus_damage", 0)}
        actor = Combatant(actor_record, actor_stats, [], {}, equipment=equipment)
        target = Combatant(target_record, target_stats, [], {})
        target.hp = int(request["target_hp"])
        target.guard = request.get("guard", 1.0)
        actor.attack_multiplier = request.get("attack_multiplier", 1.0)
        self.engine.rng = mock.Mock()
        self.engine.rng.random.return_value = request["critical_roll"]
        self.engine.rng.uniform.return_value = request["variance"]
        self.engine.log.clear()
        # _attackの数値のみを比較する。MP支払い・AI選択・反撃の成功証拠にはしない。
        self.engine._attack(actor, target, definition, allow_counter=False)
        self.engine.rng.uniform.assert_called_once_with(0.92, 1.08)
        self.engine.learning.learn.assert_not_called()
        self.assertEqual([actor_record, target_record], before)
        return {"dealt": request["target_hp"] - target.hp, "remaining_hp": target.hp,
                "critical": any("会心" in message for message in self.engine.log)}

    # {
    #   責務: [test_canonical_skills_match_python_numbers: 正規3スキルの会心・guard・揺らぎ・装備数値を比較する]
    #   処理: [
    #     1: 正規定義と境界値のケースを作る
    #     2: 実GodotとPythonのHP減少を比較する
    #     3: MP予測と入力・返却値の独立性を確認する
    #   ]
    #   引数: [self: 予測検証ケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_canonical_skills_match_python_numbers(self):
        # 会心率はpokeの倍率も含め、確率境界の一致を確認する。
        cases = []
        for skill_id, stats, roll, guard, variance, bonus, hp in itertools.product(
            ("body_bash", "roll", "poke"), ((0, 1000), (100, 50), (17, -4)),
            (0.0, 1 / 16, 1 / 8), (1.0, 0.5), (0.92, 1.0, 1.08), (0, 3), (1, 1000),
        ):
            request = self.quote_request(attack=stats[0], defense=stats[1], critical_roll=roll,
                                         guard=guard, variance=variance, fixed_bonus_damage=bonus,
                                         power_multiplier=1.1, target_hp=hp, attack_multiplier=1.3)
            cases.append({"operation": "quote", "definition": self.definitions[skill_id], "request": request})
        observations = self.run_probe({"cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        # 残MPは予測式のみ。実際の消費を行ったとは扱わない。
        for case, observation in zip(cases, observations):
            with self.subTest(skill=case["definition"]["id"], request=case["request"]):
                result = observation["result"]
                self.assertTrue(result["ok"], result)
                expected = self.python_attack_result(case["definition"], case["request"])
                for field in expected:
                    self.assertEqual(result[field], expected[field])
                self.assertEqual(result["remaining_mp"], 100 - int(case["definition"]["mp_cost"]))
                self.assertEqual(result["skill_id"], case["definition"]["id"])
                self.assertTrue(observation["input_preserved"])
                self.assertTrue(observation["result_independent"])

    # {
    #   責務: [test_catalog_selection_and_numeric_defaults: 正規・MOD・重複・欠損・既定値を検証する]
    #   処理: [
    #     1: 正常と不正なカタログをまとめて実行する
    #     2: コピーと数値正規化を確認する
    #   ]
    #   引数: [self: 予測検証ケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_catalog_selection_and_numeric_defaults(self):
        # 他の未移植定義は残したまま、選択したIDだけを一意に取り出す。
        mod = {"id": "mod_hit", "display_name": "試験打撃", "kind": "physical", "mp_cost": "3"}
        cases = [{"operation": "prepare", "document": self.document, "skill_id": skill}
                 for skill in ("body_bash", "roll", "poke")]
        cases += [{"operation": "prepare", "document": {"schema_version": 1, "skills": [mod]}, "skill_id": "mod_hit"},
                  {"operation": "prepare", "document": {"schema_version": 1, "skills": [mod, mod]}, "skill_id": "mod_hit"},
                  {"operation": "prepare", "document": self.document, "skill_id": "missing"},
                  {"operation": "prepare", "document": {"schema_version": True, "skills": [mod]}, "skill_id": "mod_hit"}]
        observations = self.run_probe({"cases": cases})["results"]
        for index, observation in enumerate(observations):
            self.assertEqual(observation["result"]["ok"], index < 4)
            self.assertTrue(observation["input_preserved"])
            self.assertTrue(observation["result_independent"])
        self.assertEqual(observations[3]["result"]["skill"]["power"], 1.0)
        self.assertEqual(observations[3]["result"]["skill"]["critical_multiplier"], 1.0)
        self.assertEqual(observations[3]["result"]["skill"]["mp_cost"], 3)

    # {
    #   責務: [test_mod_cost_power_and_critical_rules_match_python: MOD数値の切捨て・既定値・会心倍率を比較する]
    #   処理: [
    #     1: 有限MOD定義と境界乱数を用意する
    #     2: 正本の実攻撃と残MP予測を比較する
    #   ]
    #   引数: [self: 予測検証ケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_mod_cost_power_and_critical_rules_match_python(self):
        # 勝手な下限修復をせず、Pythonの有限MOD数値と同じ規則を維持する。
        cases = []
        for cost, power, critical, roll in itertools.product(
            ("3", 3.9), (-1, 0, "1.25", 2), (-1, 0, 2, 16, 99), (0.0, 0.5, 0.999),
        ):
            definition = {"id": "mod_hit", "display_name": "試験打撃", "kind": "physical",
                          "mp_cost": cost, "power": power, "critical_multiplier": critical}
            cases.append({"operation": "quote", "definition": definition,
                          "request": self.quote_request(critical_roll=roll, guard=0.5)})
        # power/critical_multiplier省略時の既定値は、それぞれ1.0。
        cases.append({"operation": "quote", "definition": {
            "id": "mod_hit", "display_name": "試験打撃", "kind": "physical", "mp_cost": 3,
        }, "request": self.quote_request()})
        observations = self.run_probe({"cases": cases})["results"]
        for case, observation in zip(cases, observations):
            with self.subTest(definition=case["definition"], request=case["request"]):
                result = observation["result"]
                self.assertTrue(result["ok"], result)
                expected = self.python_attack_result(case["definition"], case["request"])
                for field in expected:
                    self.assertEqual(result[field], expected[field])
                self.assertEqual(result["remaining_mp"], 100 - int(case["definition"]["mp_cost"]))
                self.assertTrue(observation["input_preserved"])

    # {
    #   責務: [test_mp_boundary_and_unsupported_effects_are_rejected: MP不足と未対応効果を成功扱いにしない]
    #   処理: [
    #     1: MP境界と未知キー・未対応kindを作る
    #     2: 正常ケースと拒否理由を確認する
    #   ]
    #   引数: [self: 予測検証ケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_mp_boundary_and_unsupported_effects_are_rejected(self):
        # MPは正規の非負整数だけ。ちょうど支払える場合の予測は0になる。
        definition = self.definitions["body_bash"]
        cases = [{"operation": "quote", "definition": definition, "request": self.quote_request(current_mp=value)}
                 for value in (3, 2, 0, -1, 3.5, True, "3", None)]
        # falseや空の効果も無視せず、実装されていない範囲を明示する。
        for field in ("status_effect", "element", "target", "self_damage_ratio", "counter", "protect_ally", "field_only"):
            cases.append({"operation": "quote", "definition": {**definition, field: False},
                          "request": self.quote_request()})
        for kind in ("magic", "random", "field", None, []):
            cases.append({"operation": "quote", "definition": {**definition, "kind": kind},
                          "request": self.quote_request()})
        for skill_id in ("attack", "defend"):
            cases.append({"operation": "quote", "definition": {**definition, "id": skill_id},
                          "request": self.quote_request()})
        for value in (0, -1, True, None, "0.9"):
            cases.append({"operation": "quote", "definition": {**definition, "mp_cost": value},
                          "request": self.quote_request()})
        cases.append({"operation": "quote", "definition": definition,
                      "request": self.quote_request(equipment={})})
        results = self.run_probe({"cases": cases})["results"]
        self.assertTrue(results[0]["result"]["ok"])
        self.assertEqual(results[0]["result"]["remaining_mp"], 0)
        for observation in results[1:]:
            self.assertFalse(observation["result"]["ok"])
            self.assertTrue(observation["input_preserved"])
        self.assertEqual(results[1]["result"]["reason"], "insufficient_mp")
        self.assertEqual(results[-1]["result"]["reason"], "unsupported_quote_field")

    # {
    #   責務: [test_nonfinite_precision_and_request_types_are_rejected: 型・精度超過・native非有限値を拒否する]
    #   処理: [
    #     1: 不正値の要求を作る
    #     2: 実Godotで理由付き拒否を確認する
    #   ]
    #   引数: [self: 予測検証ケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_nonfinite_precision_and_request_types_are_rejected(self):
        # JSONの通常値だけでなく、Godot nativeのNaN/Infも検証する。
        definition = self.definitions["roll"]
        cases = []
        for field, value in (("attack", True), ("defense", {}), ("variance", 1.09), ("critical_roll", 1.0),
                             ("target_hp", -1), ("current_mp", 2**53), ("attack", 2**53),
                             ("power_multiplier", "nan"), ("fixed_bonus_damage", True)):
            cases.append({"operation": "quote", "definition": definition, "request": self.quote_request(**{field: value})})
        for target, field in (("definition", "power"), ("definition", "critical_multiplier"),
                              ("definition", "mp_cost"), ("request", "current_mp"), ("request", "variance")):
            for value in ("nan", "inf"):
                cases.append({"operation": "quote", "definition": definition, "request": self.quote_request(),
                              "special": [{"target": target, "field": field, "value": value}]})
        for value in (None, [], "bad"):
            cases.append({"operation": "quote", "definition": definition, "request": value})
        for observation in self.run_probe({"cases": cases})["results"]:
            self.assertFalse(observation["result"]["ok"], observation)

    # {
    #   責務: [test_quote_benchmark_preserves_resources: 純粋予測の性能と入力資源不変を検証する]
    #   処理: [
    #     1: warmup後の予測中央値を測る
    #     2: 入力と出力を確認する
    #   ]
    #   引数: [self: 予測検証ケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_quote_benchmark_preserves_resources(self):
        # 余裕のある退行検出上限。Sessionや描画の計測には置き換えない。
        result = self.run_probe({"performance": True, "iterations": 1500, "samples": 3, "warmup": 500})
        self.assertLessEqual(result["microseconds"], 3000, result)
        self.assertEqual((result["current_mp"], result["target_hp"]), (10, 1000))
        self.assertEqual((result["quote"]["remaining_mp"], result["quote"]["remaining_hp"]), (7, 951))
