"""付与付き物理の実MP/HP/状態更新を、実GodotとPythonで比較します。実セーブは使いません。"""
# {
#   責務: [test_gdscript_status_physical_action: 状態補正・物理/付与の実適用と専用Application接続の正常系を検証します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import itertools
import json
import shutil
import unittest

from gdscript_status_action_fixture import ACTOR, TARGET, StatusActionFixture, action, action_case, fixture
import test_gdscript_combatant as combatant


# {
#   責務: [StatusPhysicalActionBoundaryTests: 計算/状態所有/呼出調停の責務を分離し、従来の物理入口の付与拒否を維持します]
#   フィールド: []
# }
class StatusPhysicalActionBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_action_reuses_contracts_without_io_ai_or_rng: 行動が共用検査/数値/状態所有者へ委譲し、Applicationが実処理を持たないことを確認します]
    #   処理: [1: 専用行動とApplicationのソース依存を照合し、未対応の通常入口を緩めていないか確認します]
    #   引数: [self: 行動接続の責務境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_action_reuses_contracts_without_io_ai_or_rng(self):
        root = fixture.godot_fixture.ROOT / "gdscript"
        source = (root / "engine/status_physical_skill_action.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "res://data/", "res://application/", "res://ui/",
                          "RandomNumberGenerator", "randf(", ".learn(", "await ", "callback("):
            self.assertNotIn(forbidden, source)
        for shared in ("_preflight.inspect(", "Stats.quote_stats(", "Quote.quote_damage(", ".claim(",
                       ".pay_mp(", ".take_damage(", ".apply_status_application(", ".finish("):
            self.assertIn(shared, source)
        application = (root / "application/battle_session_application.gd").read_text(encoding="utf-8")
        self.assertIn("_status_physical.resolve(request)", application)
        for forbidden in ("Stats.quote_stats(", ".pay_mp(", ".take_damage(", ".apply_status_application("):
            self.assertNotIn(forbidden, application)


# {
#   責務: [StatusPhysicalActionTests: 実Godot/PythonのMP/HP/状態一致と、最新状態・装備・Applicationの接続を検証します]
#   フィールド: [folder: 共用fixtureの専用要求/保存ダミー領域（Path）]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for status physical actions")
class StatusPhysicalActionTests(StatusActionFixture, unittest.TestCase):
    # {
    #   責務: [test_real_mp_hp_and_status_match_python: 会心/揺らぎ・致死/非致死・既存出血・耐性/確率境界を実Pythonへ照合します]
    #   処理: [1: 独立した直積ケースを実Godotで実行し、実MP消費・残HP・付与状態と乱数要否を比較します]
    #   引数: [self: 実行結果のPython互換を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_real_mp_hp_and_status_match_python(self):
        cases, expected = [], []
        for hp, critical, variance, effects, resistance, status_roll in itertools.product(
                (1, 1000), (0, 1 / 16), (0.92, 1.08), ([], ["bleeding"], ["poison"]),
                ("weak", "immune"), (0.49, 0.5)):
            case = action_case(steps=[{"operation": "next"}, action(critical_roll=critical, variance=variance, status_roll=status_roll)])
            case["teams"]["enemies"][0]["snapshot"]["hp"] = hp
            case["teams"]["enemies"][0]["snapshot"]["stats"]["hp"] = hp
            case["initial_statuses"]["enemies"]["same"] = effects
            case["teams"]["enemies"][0]["status_resistances"] = {"bleeding": resistance}
            cases.append(case)
            expected.append(self.python_action(case, critical, variance, status_roll))
        for case, observed, wanted in zip(cases, self.observe({"cases": cases})["results"], expected):
            with self.subTest(case=case["steps"][-1], hp=case["teams"]["enemies"][0]["snapshot"]["hp"]):
                result = observed["steps"][-1]["result"]
                self.assertTrue(result["ok"], result)
                self.assertTrue(result["executed"])
                self.assertEqual(result["scope"], "explicit_status_physical_skill_only")
                allies, enemies = result["session"]["teams"]["allies"], result["session"]["teams"]["enemies"]
                self.assertEqual((allies[0]["mp"], enemies[0]["hp"], result["dealt"]),
                                 (wanted["remaining_mp"], wanted["remaining_hp"], wanted["dealt"]))
                self.assertEqual(result["spent_mp"], 3)
                self.assertEqual(result["statuses"]["teams"]["enemies"]["same"], wanted["status_effects"])
                self.assertEqual(result["numbers"]["status"]["roll_required"], wanted["roll_required"])
                self.assertEqual(result["numbers"]["physical"]["remaining_mp"], wanted["remaining_mp"])
                self.assertEqual(len(result["session"]), 7)
                self.assertEqual(len(allies[0]), 6)

    # {
    #   責務: [test_live_bleeding_is_recomputed_between_actions: 戦闘中に追加した出血が次の攻撃の防御力へ一度だけ反映されることを確認します]
    #   処理: [1: 最初の79ダメージで出血を付与し、次ラウンドは基礎防御50を45へ補正して81ダメージになるか確認します]
    #   引数: [self: 最新状態の再読取を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_live_bleeding_is_recomputed_between_actions(self):
        case = action_case(steps=[{"operation": "next"}, action(), {"operation": "next"},
            {"operation": "claim"}, {"operation": "finish"}, {"operation": "begin", "order": [ACTOR, TARGET]},
            {"operation": "next"}, action()])
        observed = self.observe({"cases": [case]})["results"][0]
        first, second = observed["steps"][1]["result"], observed["steps"][-1]["result"]
        self.assertEqual((first["dealt"], second["dealt"]), (79, 81))
        self.assertEqual(second["session"]["teams"]["enemies"][0]["stats"]["defense"], 50)
        self.assertEqual(second["applied_status"]["outcome"], "already_present")
        self.assertEqual(second["session"]["teams"]["allies"][0]["mp"], 44)
        self.assertEqual(len(second["statuses"]["teams"]["enemies"]["same"]), 1)

    # {
    #   責務: [test_equipment_guard_and_initial_input_are_respected: 許可装備・物理guardと初期入力コピーの保持を実適用で確認します]
    #   処理: [1: 敵のぼうぎょ後に開始入力を編集し、装備補正とguardを含む元の行動結果をPythonへ照合します]
    #   引数: [self: 開始情報と最新guardを検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_equipment_guard_and_initial_input_are_respected(self):
        case = action_case(order=[TARGET, ACTOR], steps=[{"operation": "next"}, {"operation": "claim"},
            {"operation": "defend", "value": 0.5}, {"operation": "finish"}, {"operation": "next"},
            {"operation": "input_edit"}, action()])
        case["teams"]["allies"][0]["equipment"] = {"allowed_species_ids": ["slime"], "fixed_bonus_damage": 3,
            "skill_modifiers": {"mod_status_hit": {"power_multiplier": 2}}}
        wanted = self.python_action(case, guard=0.5)
        result = self.observe({"cases": [case]})["results"][0]["steps"][-1]["result"]
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["dealt"], wanted["dealt"])
        self.assertEqual(result["statuses"]["teams"]["enemies"]["same"], wanted["status_effects"])
        self.assertEqual(result["session"]["phase"], "round_finished")

    # {
    #   責務: [test_cure_before_execution_restores_base_defense: 予約提示後に出血を治療した場合、次の攻撃が低下前の防御力を使うことを確認します]
    #   処理: [1: 敵が自身の出血を実治療した後、付与付き物理が79ダメージを計算することを確認します]
    #   引数: [self: 治療後の最新状態を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_cure_before_execution_restores_base_defense(self):
        case = action_case(order=[TARGET, ACTOR], steps=[{"operation": "next"}, {"operation": "claim"},
            {"operation": "apply_cure", "actor": TARGET, "request": {"cure_chance": 1, "roll": 0}},
            {"operation": "finish"}, {"operation": "next"}, action()])
        case["initial_statuses"]["enemies"]["same"] = ["bleeding"]
        # 敵が先に自身を治療するシナリオを保つため、出血補正後も味方を上回る速度を設定します。
        case["teams"]["enemies"][0]["snapshot"]["stats"]["speed"] = 20
        observed = self.observe({"cases": [case]})["results"][0]
        self.assertTrue(observed["steps"][2]["result"]["cured"])
        self.assertEqual(observed["steps"][-1]["result"]["dealt"], 79)

    # {
    #   責務: [test_application_learning_legacy_rejection_and_failed_start_retry: 保存個体再構築からの専用行動と、従来開始/通常物理の拒否を確認します]
    #   処理: [1: 一時MODのbody_bashへ出血を加え、Lv6/7・不正初期状態の再試行・従来入口の拒否を実行します]
    #   引数: [self: ApplicationとJSON再構築の接続を検査するテストケース]
    #   戻り値: [result: なし（None）。正規dataと実セーブは変更しません]
    # }
    def test_application_learning_legacy_rejection_and_failed_start_retry(self):
        mod = self.folder / "mod"
        shutil.copytree(self.content / "data", mod / "data")
        path = mod / "data/skills/skills.json"
        skills = json.loads(path.read_text(encoding="utf-8"))
        next(item for item in skills["skills"] if item["id"] == "body_bash")["status_effect"] = {"id": "bleeding", "chance": 1}
        path.write_text(json.dumps(skills), encoding="utf-8")
        cases = [action_case(joined=True, project_root=str(mod), records={
            side: [combatant.record("same", "slime", level=level)] for side in ("allies", "enemies")},
            initial_statuses={side: {"same": []} for side in ("allies", "enemies")},
            steps=[{"operation": "next"}, {"operation": "ordinary_action", "target": TARGET, "skill_id": "body_bash",
                    "extra": {"critical_roll": 0.5, "variance": 1}}, action(skill_id="body_bash", status_roll=0)]) for level in (6, 7)]
        valid = copy.deepcopy(cases[1])
        invalid = copy.deepcopy(valid)
        invalid["initial_statuses"] = {"allies": {}, "enemies": {}}
        invalid["steps"] = [{"operation": "start", "input": valid}, *valid["steps"]]
        cases += [invalid, {**valid, "legacy": True}]
        observed = self.observe({"cases": cases})["results"]
        self.assertEqual(observed[0]["steps"][-1]["result"]["reason"], "skill_not_learned")
        self.assertFalse(observed[1]["steps"][1]["result"]["ok"])
        self.assertTrue(observed[1]["steps"][1]["unchanged"])
        self.assertTrue(observed[1]["steps"][-1]["result"]["applied_status"]["applied"])
        self.assertFalse(observed[2]["started"]["ok"])
        self.assertTrue(observed[2]["steps"][0]["result"]["ok"])
        self.assertTrue(observed[2]["steps"][-1]["result"]["executed"])
        self.assertEqual(observed[3]["steps"][-1]["result"]["reason"], "not_initialized")
        self.assertEqual(observed[3]["statuses"], {})
