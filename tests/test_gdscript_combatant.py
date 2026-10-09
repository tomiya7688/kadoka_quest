"""Battle-only resource state and read-only reconstruction; real Godot, private content/saves."""
# {
#   責務: [test_gdscript_combatant: Battle-only resource state and read-only reconstruction; real Godot, private content/saves.]
#   フィールド: []
# }
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import subprocess
import unittest
from unittest import mock

import test_gdscript_roster as fixture
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.monster import MonsterRecord, equipment_allows_species
from kadoka_quest.data.battle_data import BattleDataLoader
from kadoka_quest.data.repository import GameRepository, STAT_KEYS

ROOT = fixture.ROOT


# {
#   責務: [identity: 専用比較個体のID・スライム種族・表示名を作ります]
#   処理: [1: 専用比較個体のID・スライム種族・表示名を作ります]
#   引数: [identifier: 専用比較個体の識別ID]
#   戻り値: [result: id・species_id・nameを持つ個体情報（dict）]
# }
def identity(identifier="one"):
    return {"id": identifier, "species_id": "slime", "name": "比較個体"}


# {
#   責務: [stats: 6能力値の既定値へ指定した比較用の値を加えます]
#   処理: [1: 6能力値の既定値へ指定した比較用の値を加えます]
#   引数: [changes: 比較ケース別の値や設定の上書き]
#   戻り値: [result: 指定した数値を持つ6能力値（dict）]
# }
def stats(**changes):
    return {**dict.fromkeys(STAT_KEYS, 10), "hp": 30, "mp": 7, **changes}


# {
#   責務: [state_case: test・gdscript・戦闘個体の状態・caseを求める]
#   処理: [1: test・gdscript・戦闘個体の状態・caseを求める]
#   引数: [
#     actions: actions
#     changes: changes
#   ]
#   戻り値: [result: test・gdscript・戦闘個体の状態・caseを求めるための結果（型注釈なし）]
# }
def state_case(actions=(), **changes):
    return {"identity": identity(), "stats": stats(), "actions": list(actions), **changes}


# {
#   責務: [action: test・gdscript・戦闘個体のactionを求める]
#   処理: [1: test・gdscript・戦闘個体のactionを求める]
#   引数: [
#     kind: 種別
#     value: 値
#     changes: changes
#   ]
#   戻り値: [result: test・gdscript・戦闘個体のactionを求めるための結果（型注釈なし）]
# }
def action(kind, value=None, **changes):
    return {"kind": kind, "value": value, **changes}


# {
#   責務: [record: 専用個体の種族・レベル・＋・装備と学習状態を、実セーブから独立した辞書で作ります]
#   処理: [1: 専用個体の種族・レベル・＋・装備と学習状態を、実セーブから独立した辞書で作ります]
#   引数: [
#     identifier: 専用比較個体の識別ID
#     species: 種族
#     changes: 比較ケース別の値や設定の上書き
#   ]
#   戻り値: [result: 専用monsterとaiを持つ個体レコード（dict）]
# }
def record(identifier="one", species="slime", **changes):
    return {"monster": {**identity(identifier), "schema_version": 1, "species_id": species, "level": 1,
                        "plus_choices": [], "equipment_id": None, **changes},
            "ai": {"schema_version": 1, "learned_private": {"weights": [12, 34]}}}


# {
#   責務: [CombatantBoundaryTests: 戦闘個体の資源契約と再構築入口からI/O・画面・乱数・学習を分離する依存境界を検証します]
#   フィールド: []
# }
class CombatantBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_pure_state_has_no_io_ui_random_learning_or_reconstruction: 資源保持と個体再構築にI/O・画面・乱数・学習の依存がないか確認します]
    #   処理: [1: 資源契約とBuilderの禁止参照、およびフィールドへの未接続をソースで検査します]
    #   引数: [self: 戦闘個体の依存境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_pure_state_has_no_io_ui_random_learning_or_reconstruction(self):
        source = (ROOT / "gdscript/engine/combatant_state.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "OS.", "randf(", "randi(", "Input.", "Label",
                          "res://data/", "res://application/", "res://ui/", ".learn("):
            self.assertNotIn(forbidden, source)
        builder = (ROOT / "gdscript/application/combatant_builder.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "write_atomic", "save(", "Label", ".learn("):
            self.assertNotIn(forbidden, builder)
        field = (ROOT / "gdscript/application/field_application.gd").read_text(encoding="utf-8")
        self.assertNotIn("combatant_builder", field)
        self.assertNotIn("combatant_state", field)

    # {
    #   責務: [test_performance_tool_remains_developer_only: 戦闘個体の性能検査CLIをゲーム本体や画面から呼ばないことを確認します]
    #   処理: [1: Python本体とGodot application/uiのソースに開発専用CLI名がないか検査します]
    #   引数: [self: 性能検査ツールの依存境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_performance_tool_remains_developer_only(self):
        for directory in (ROOT / "src/kadoka_quest", ROOT / "gdscript/application", ROOT / "gdscript/ui"):
            for path in directory.rglob("*"):
                if path.suffix in (".py", ".gd"):
                    self.assertNotIn("check_gdscript_combatant", path.read_text(encoding="utf-8"))


# {
#   責務: [GDScriptCombatantTests: 専用fixtureと実Godotを使い、戦闘個体の再構築・資源保持/更新を検証します]
#   フィールド: [
#     setUp: 所有個体fixtureへ委譲して検証専用領域を用意するメソッド
#     seed_state: 所有個体fixtureを使い専用フィールド状態を作るメソッド
#     seed_record: 所有個体fixtureを使い専用個体/AIを作るメソッド
#     write: 専用領域へfixture JSONを書き込むメソッド
#     saved_files: 専用保存ファイルの相対パスとbyte列を比較用に返すメソッド
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real combatant-resource probes")
class GDScriptCombatantTests(unittest.TestCase):
    setUp = fixture.GDScriptRosterTests.setUp
    seed_state = fixture.GDScriptRosterTests.seed_state
    seed_record = fixture.GDScriptRosterTests.seed_record
    write = fixture.GDScriptRosterTests.write
    saved_files = fixture.GDScriptRosterTests.saved_files

    # {
    #   責務: [invoke: gdscript・戦闘個体・testsのinvokeを求める]
    #   処理: [1: gdscript・戦闘個体・testsのinvokeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     request: 要求
    #   ]
    #   戻り値: [result: gdscript・戦闘個体・testsのinvokeを求めるための結果（型注釈なし）]
    # }
    def invoke(self, **request):
        path = self.content / "combatant-probe.json"
        path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content), KADOKA_SAVE_DIR=str(self.legacy),
                           KADOKA_GDSCRIPT_SAVE_ROOT=str(self.saves), KADOKA_GDSCRIPT_SAVE_NAME="default")
        process = subprocess.run(
            [str(fixture.GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
             "res://tests/run_combatant_probe.gd", "--", str(path)],
            cwd=self.content, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout[-1600:])
        self.assertNotIn("SCRIPT ERROR", process.stderr)
        self.assertNotIn("ERROR:", process.stderr)
        for line in process.stdout.splitlines():
            if line.startswith("KADOKA_COMBATANT_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(process.stderr + process.stdout[-1600:])

    # {
    #   責務: [byte_snapshot: gdscript・戦闘個体・testsのbyte・独立した状態の写しを求める]
    #   処理: [1: gdscript・戦闘個体・testsのbyte・独立した状態の写しを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: gdscript・戦闘個体・testsのbyte・独立した状態の写しを求めるための結果（型注釈なし）]
    # }
    def byte_snapshot(self):
        return {str(path.relative_to(self.content)): hashlib.sha256(path.read_bytes()).hexdigest()
                for directory in ("data", "assets", "python-saves", "gd-saves")
                for path in (self.content / directory).rglob("*") if path.is_file()}

    # {
    #   責務: [test_all_species_levels_plus_and_allowed_equipment_start_like_python: 検証: all species levels plus and allowed equipment start like python]
    #   処理: [1: 検証: all species levels plus and allowed equipment start like python]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_all_species_levels_plus_and_allowed_equipment_start_like_python(self):
        repository = GameRepository(self.content / "data")
        loader = BattleDataLoader(repository)
        cases = []
        for species in repository.list_species_ids():
            bundle = repository.get_species(species)
            chain = [stage["options"][0]["id"] for stage in bundle.plus["stages"]]
            permitted = [identifier for identifier, item in repository.get_equipment().items()
                         if equipment_allows_species(item, species)]
            for level in (1, 10, 50, 100):
                for choices in ([], chain[:1], chain):
                    for equipment in (None, *permitted):
                        cases.append(record(f"actor_{len(cases)}", species, level=level,
                                            plus_choices=choices, equipment_id=equipment, hp=0, mp=0))
        before = self.byte_snapshot()
        results = self.invoke(records=cases)["records"]
        self.assertEqual(len(results), len(cases))
        for parameters, item in zip(cases, results):
            with self.subTest(monster=parameters["monster"]):
                actual = item["value"]
                self.assertTrue(actual["ok"], actual)
                self.assertTrue(item["preserved"])
                expected = loader.build_combatant(MonsterRecord(
                    copy.deepcopy(parameters["monster"]), copy.deepcopy(parameters["ai"])
                ))
                self.assertEqual(actual["snapshot"]["stats"], expected.stats)
                self.assertEqual(actual["snapshot"]["hp"], expected.hp)
                self.assertEqual(actual["snapshot"]["mp"], expected.mp)
                self.assertEqual(actual["snapshot"]["alive"], expected.alive)
                self.assertEqual(actual["snapshot"]["fled"], expected.fled)
                self.assertEqual(actual["snapshot"]["identity"],
                                 {key: parameters["monster"][key] for key in ("id", "species_id", "name")})
                self.assertNotIn("ai", actual["snapshot"])
                self.assertEqual(actual["scope"], "combatant_resources_only")
        self.assertEqual(self.byte_snapshot(), before)

    # {
    #   責務: [test_hp_zero_overkill_and_reinitialization_never_resurrect_runtime: 検証: hp zero overkill and reinitialization never resurrect runtime]
    #   処理: [1: 検証: hp zero overkill and reinitialization never resurrect runtime]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_hp_zero_overkill_and_reinitialization_never_resurrect_runtime(self):
        actions = [action("damage", 0), action("damage", 8), action("damage", 1000),
                   action("damage", 0), action("damage", 1), action("start"), action("living")]
        result = self.invoke(cases=[state_case(actions)])["cases"][0]
        values = [step["value"] for step in result["observations"]]
        self.assertEqual([item["dealt"] for item in values[:5]], [0, 8, 22, 0, 0])
        self.assertEqual([item["hp"] for item in values[:5]], [30, 22, 0, 0, 0])
        self.assertEqual(values[5], {"ok": False, "reason": "already_initialized"})
        self.assertEqual(values[6], {"ok": True, "members": []})
        expected = BattleDataLoader(GameRepository(self.content / "data")).build_combatant(
            MonsterRecord(record()["monster"], {}))
        self.assertGreater(expected.hp, 0)  # Python constructor hp=0 is a fresh-start sentinel only.
        expected.hp = 0
        self.assertFalse(expected.alive)
        self.assertFalse(result["observations"][-1]["snapshots"][0]["alive"])
        self.assertTrue(result["input_preserved"])

    # {
    #   責務: [test_mp_affordability_zero_exact_and_insufficient_are_non_destructive: 検証: mp affordability zero exact and insufficient are non destructive]
    #   処理: [1: 検証: mp affordability zero exact and insufficient are non destructive]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_mp_affordability_zero_exact_and_insufficient_are_non_destructive(self):
        steps = [action("cost", 7), action("pay", 8), action("pay", 0), action("pay", 7),
                 action("cost", 1), action("pay", 1), action("pay", 0)]
        cases = [state_case(steps), state_case([action("pay", 0), action("pay", 1)], stats=stats(mp=0))]
        result = self.invoke(cases=cases)["cases"]
        values = [step["value"] for step in result[0]["observations"]]
        self.assertTrue(values[0]["affordable"])
        self.assertFalse(values[1]["ok"])
        self.assertEqual(values[1]["reason"], "insufficient_mp")
        self.assertEqual([values[i]["mp"] for i in (1, 2, 3, 4, 5, 6)], [7, 7, 0, 0, 0, 0])
        self.assertEqual([values[i]["spent"] for i in (1, 2, 3, 5, 6)], [0, 0, 7, 0, 0])
        self.assertTrue(result[1]["initialized"]["ok"])
        self.assertTrue(result[1]["observations"][0]["value"]["ok"])
        self.assertFalse(result[1]["observations"][1]["value"]["ok"])

    # {
    #   責務: [test_fled_is_not_living_even_with_hp_and_independent_members_keep_order: 検証: fled is not living even with hp and independent members keep order]
    #   処理: [1: 検証: fled is not living even with hp and independent members keep order]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_fled_is_not_living_even_with_hp_and_independent_members_keep_order(self):
        steps = [action("start", actor=1, identity=identity("two")), action("damage", 2),
                 action("pay", 3, actor=1), action("living"), action("flee"), action("living"),
                 action("flee"), action("damage", 100, actor=1), action("living")]
        result = self.invoke(cases=[state_case(steps)])["cases"][0]["observations"]
        self.assertEqual([member["identity"]["id"] for member in result[3]["value"]["members"]], ["one", "two"])
        self.assertEqual([member["identity"]["id"] for member in result[5]["value"]["members"]], ["two"])
        self.assertTrue(result[4]["value"]["changed"])
        self.assertFalse(result[6]["value"]["changed"])
        self.assertEqual(result[8]["value"]["members"], [])
        first, second = result[-1]["snapshots"]
        self.assertEqual((first["hp"], first["mp"], first["fled"]), (28, 7, True))
        self.assertEqual((second["hp"], second["mp"], second["fled"]), (0, 4, False))

    # {
    #   責務: [test_inputs_returned_snapshots_and_initial_result_have_no_shared_state: 検証: inputs returned snapshots and initial result have no shared state]
    #   処理: [1: 検証: inputs returned snapshots and initial result have no shared state]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_inputs_returned_snapshots_and_initial_result_have_no_shared_state(self):
        member = {"identity": identity(), "stats": stats(), "hp": 30, "mp": 7, "alive": True, "fled": False}
        steps = [action("initial_result_mutation"), action("snapshot_mutation"),
                 action("living_mutation", members=[member]), action("input_mutation"), action("damage", 2)]
        result = self.invoke(cases=[state_case(steps)])["cases"][0]
        for observation in result["observations"]:
            snapshot = observation["snapshots"][0]
            self.assertEqual(snapshot["stats"], stats())
            self.assertEqual(snapshot["identity"], identity())
        self.assertEqual(result["observations"][-1]["snapshots"][0]["hp"], 28)
        self.assertFalse(result["input_preserved"])  # Probe intentionally edits the caller's own input.
        self.assertTrue(result["case_preserved"])

    # {
    #   責務: [test_invalid_damage_and_mp_types_nonfinite_and_bounds_never_mutate: 検証: invalid damage and mp types nonfinite and bounds never mutate]
    #   処理: [1: 検証: invalid damage and mp types nonfinite and bounds never mutate]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_damage_and_mp_types_nonfinite_and_bounds_never_mutate(self):
        invalid = [None, True, False, -1, 1.5, "1", [], {}, 2**53]
        steps = [action(kind, value) for kind in ("damage", "cost", "pay") for value in invalid]
        steps += [action(kind, special=special) for kind in ("damage", "cost", "pay") for special in ("inf", "nan")]
        result = self.invoke(cases=[state_case(steps)])["cases"][0]
        for step in result["observations"]:
            with self.subTest(step=step["value"]):
                self.assertFalse(step["value"]["ok"])
                self.assertIn("reason", step["value"])
                self.assertEqual(step["snapshots"][0]["hp"], 30)
                self.assertEqual(step["snapshots"][0]["mp"], 7)
        # JSON numbers arrive as float in Godot; integral floats within exact range are supported.
        steps = [action("damage", 2.0), action("pay", 7.0), action("damage", 2**53 - 1)]
        result = self.invoke(cases=[state_case(steps)])["cases"][0]
        self.assertEqual(result["observations"][0]["value"]["dealt"], 2)
        self.assertEqual(result["observations"][1]["value"]["mp"], 0)
        self.assertEqual(result["observations"][2]["value"]["hp"], 0)

    # {
    #   責務: [test_uninitialized_refusal_and_failed_start_can_retry_without_defaults: 検証: uninitialized refusal and failed start can retry without defaults]
    #   処理: [1: 検証: uninitialized refusal and failed start can retry without defaults]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_uninitialized_refusal_and_failed_start_can_retry_without_defaults(self):
        steps = [action("damage", 1), action("pay", 1), action("cost", 0), action("flee")]
        cases = [state_case(steps, start=False),
                 state_case([action("start", identity=identity(), stats=stats())], stats={})]
        result = self.invoke(cases=cases)["cases"]
        for observation in result[0]["observations"]:
            self.assertEqual(observation["value"], {"ok": False, "reason": "not_initialized"})
            self.assertEqual(observation["snapshots"], [{}, {}])
        self.assertFalse(result[1]["initialized"]["ok"])
        self.assertTrue(result[1]["observations"][0]["value"]["ok"])

    # {
    #   責務: [test_invalid_identity_and_stats_refuse_with_reasons: 検証: invalid identity and stats refuse with reasons]
    #   処理: [1: 検証: invalid identity and stats refuse with reasons]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_identity_and_stats_refuse_with_reasons(self):
        identities = [None, [], {}, identity("../escape"), {**identity(), "species_id": True}, {**identity(), "name": ""}]
        cases = [state_case(identity=value) for value in identities]
        cases += [state_case(stats=value) for value in (None, [], {}, stats(hp=0))]
        for key in STAT_KEYS:
            cases.append(state_case(stats={k: v for k, v in stats().items() if k != key}))
            cases += [state_case(stats=stats(**{key: value})) for value in (True, -1, "10", 1.1, 2**53)]
            cases += [state_case(special_stats={key: special}) for special in ("inf", "nan")]
        result = self.invoke(cases=cases)["cases"]
        for parameters, actual in zip(cases, result):
            with self.subTest(parameters=parameters):
                self.assertFalse(actual["initialized"]["ok"])
                self.assertIn("reason", actual["initialized"])
                self.assertTrue(actual["input_preserved"])

    # {
    #   責務: [test_living_snapshot_validation_refuses_invalid_or_duplicate_members: 検証: living snapshot validation refuses invalid or duplicate members]
    #   処理: [1: 検証: living snapshot validation refuses invalid or duplicate members]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_living_snapshot_validation_refuses_invalid_or_duplicate_members(self):
        member = {"identity": identity(), "stats": stats(), "hp": 30, "mp": 7, "alive": True, "fled": False}
        malformed = [None, {}, {**member, "hp": -1}, {**member, "hp": 31}, {**member, "mp": 8},
                     {**member, "alive": False}, {**member, "fled": 1}, {**member, "hp": True}]
        members = [None, {}, *[[value] for value in malformed], [member, member]]
        steps = [action("living", members=value) for value in members]
        result = self.invoke(cases=[state_case(steps)])["cases"][0]
        for step in result["observations"]:
            self.assertFalse(step["value"]["ok"])
            self.assertIn("reason", step["value"])
        self.assertEqual(result["observations"][-1]["value"]["reason"], "duplicate_member")

    # {
    #   責務: [test_team_limit_is_not_ownership_limit_and_never_silently_truncates: 検証: team limit is not ownership limit and never silently truncates]
    #   処理: [1: 検証: team limit is not ownership limit and never silently truncates]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_team_limit_is_not_ownership_limit_and_never_silently_truncates(self):
        owned = [record(f"owned_{index}") for index in range(120)]
        teams = [[], owned[:4], owned[:5], [owned[0], owned[0]], [owned[0], None], {}, None]
        result = self.invoke(records=owned, teams=teams)
        self.assertEqual(len(result["records"]), 120)
        self.assertTrue(all(item["value"]["ok"] and item["preserved"] for item in result["records"]))
        values = [item["value"] for item in result["teams"]]
        self.assertEqual(values[0], {"ok": True, "members": []})
        self.assertEqual([item["snapshot"]["identity"]["id"] for item in values[1]["members"]],
                         [item["monster"]["id"] for item in owned[:4]])
        self.assertEqual([item["reason"] for item in values[2:]],
                         ["active_team_limit", "duplicate_member", "invalid_record", "invalid_team", "invalid_team"])
        self.assertTrue(all(item["preserved"] for item in result["teams"]))

    # {
    #   責務: [test_invalid_records_and_unsupported_definitions_are_not_repaired: 検証: invalid records and unsupported definitions are not repaired]
    #   処理: [1: 検証: invalid records and unsupported definitions are not repaired]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_records_and_unsupported_definitions_are_not_repaired(self):
        invalid = [None, [], {}, {"monster": record()["monster"]},
                   record(level=True), record(level=101), record(name=123), record(species="../escape"),
                   record(species="missing"), record(schema_version=99), record(plus_choices="bad"),
                   {**record(), "ai": {"schema_version": 99}}]
        before = self.byte_snapshot()
        actual = self.invoke(records=invalid)["records"]
        for parameters, item in zip(invalid, actual):
            with self.subTest(record=parameters):
                self.assertFalse(item["value"]["ok"])
                self.assertIn("reason", item["value"])
                self.assertTrue(item["preserved"])
        self.assertEqual(self.byte_snapshot(), before)
        for filename in ("stats", "skills", "plus"):
            path = self.content / "data/species/slime" / (filename + ".json")
            original = path.read_bytes()
            malformed = json.loads(original)
            malformed["schema_version"] = 99
            path.write_text(json.dumps(malformed), encoding="utf-8")
            before = self.byte_snapshot()
            result = self.invoke(records=[record()])["records"][0]["value"]
            self.assertFalse(result["ok"], result)
            self.assertEqual(self.byte_snapshot(), before)
            path.write_bytes(original)
        path = self.content / "data/equipment/equipment.json"
        path.write_text('{"schema_version":99,"equipment":[]}', encoding="utf-8")
        before = self.byte_snapshot()
        result = self.invoke(records=[record()])["records"][0]["value"]
        self.assertFalse(result["ok"])
        self.assertEqual(self.byte_snapshot(), before)

    # {
    #   責務: [test_missing_corrupt_and_nonfinite_definitions_refuse_without_replacement: 検証: missing corrupt and nonfinite definitions refuse without replacement]
    #   処理: [1: 検証: missing corrupt and nonfinite definitions refuse without replacement]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_missing_corrupt_and_nonfinite_definitions_refuse_without_replacement(self):
        path = self.content / "data/species/slime/stats.json"
        original = path.read_bytes()
        path.unlink()  # Only the dedicated fixture copy; missing definition must not be recreated.
        before = self.byte_snapshot()
        result = self.invoke(records=[record()])["records"][0]["value"]
        self.assertFalse(result["ok"])
        self.assertEqual(self.byte_snapshot(), before)
        self.assertFalse(path.exists())
        for payload in ("broken JSON", {"schema_version": 1, "levels": {"1": stats(hp="inf")}},
                        {"schema_version": 1, "levels": {"1": stats(hp=None)}}):
            path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
            before = self.byte_snapshot()
            result = self.invoke(records=[record()])["records"][0]["value"]
            self.assertFalse(result["ok"], result)
            self.assertEqual(self.byte_snapshot(), before)
        path.write_bytes(original)

    # {
    #   責務: [test_unknown_choices_and_unusable_equipment_stay_warnings_not_record_repairs: 検証: unknown choices and unusable equipment stay warnings not record repairs]
    #   処理: [1: 検証: unknown choices and unusable equipment stay warnings not record repairs]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_unknown_choices_and_unusable_equipment_stay_warnings_not_record_repairs(self):
        repository = GameRepository(self.content / "data")
        forbidden = next(identifier for identifier, equipment in repository.get_equipment().items()
                         if not equipment_allows_species(equipment, "ghost"))
        cases = [record(species="ghost", plus_choices=["private_unknown"], equipment_id=identifier)
                 for identifier in ("private_missing", forbidden)]
        result = self.invoke(records=cases)["records"]
        loader = BattleDataLoader(repository)
        for parameters, item in zip(cases, result):
            self.assertTrue(item["value"]["ok"], item)
            self.assertTrue(item["value"]["warnings"])
            self.assertTrue(item["preserved"])
            self.assertEqual(item["value"]["equipment"], {})
            expected = loader.build_combatant(MonsterRecord(parameters["monster"], parameters["ai"]))
            self.assertEqual(item["value"]["snapshot"]["stats"], expected.stats)

    # {
    #   責務: [test_numeric_resource_operations_do_not_pretend_to_authorize_dead_or_fled_turns: 検証: numeric resource operations do not pretend to authorize dead or fled turns]
    #   処理: [1: 検証: numeric resource operations do not pretend to authorize dead or fled turns]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_numeric_resource_operations_do_not_pretend_to_authorize_dead_or_fled_turns(self):
        cases = [state_case([action("damage", 100), action("pay", 1), action("living")]),
                 state_case([action("flee"), action("pay", 1), action("living")])]
        result = self.invoke(cases=cases)["cases"]
        for case in result:
            self.assertTrue(case["observations"][1]["value"]["ok"])
            self.assertEqual(case["observations"][1]["value"]["mp"], 6)
            self.assertEqual(case["observations"][2]["value"]["members"], [])

    # {
    #   責務: [test_canonical_attack_numbers_apply_to_runtime_hp_like_python_without_learning: 検証: canonical attack numbers apply to runtime hp like python without learning]
    #   処理: [1: 検証: canonical attack numbers apply to runtime hp like python without learning]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_canonical_attack_numbers_apply_to_runtime_hp_like_python_without_learning(self):
        repository = GameRepository(self.content / "data")
        loader = BattleDataLoader(repository)
        cases = []
        for species in repository.list_species_ids():
            for level in (1, 50, 100):
                actor = record("attacker", species, level=level)
                target = record("target", "slime", level=level)
                attacks = [{"critical_roll": roll, "variance": variance, "guard": guard}
                           for roll, variance, guard in ((0.5, 0.92, 1), (0, 1.08, 0.5), (1 / 16, 1, 1))] * 8
                cases.append({"actor": actor, "target": target, "attacks": attacks})
        before = self.byte_snapshot()
        result = self.invoke(joined=cases)["joined"]
        for parameters, actual in zip(cases, result):
            with self.subTest(actor=parameters["actor"]["monster"]):
                self.assertTrue(actual["ok"], actual)
                self.assertTrue(actual["preserved"])
                actor = loader.build_combatant(MonsterRecord(parameters["actor"]["monster"], parameters["actor"]["ai"]))
                target = loader.build_combatant(MonsterRecord(parameters["target"]["monster"], parameters["target"]["ai"]))
                engine = BattleEngine(repository, [], [], learning_enabled=False)
                engine.learning.learn = mock.Mock()
                for attack, step in zip(parameters["attacks"], actual["steps"]):
                    target.guard = attack["guard"]
                    engine.rng = mock.Mock()
                    engine.rng.random.return_value = attack["critical_roll"]
                    engine.rng.uniform.return_value = attack["variance"]
                    previous = target.hp
                    engine._attack(actor, target, repository.get_skills()["attack"], allow_counter=False)
                    self.assertEqual(step["applied"]["dealt"], previous - target.hp)
                    self.assertEqual(step["numbers"]["dealt"], previous - target.hp)
                    self.assertEqual(step["snapshot"]["hp"], target.hp)
                    self.assertEqual(step["numbers"]["remaining_hp"], target.hp)
                    self.assertEqual(step["snapshot"]["alive"], target.alive)
                engine.learning.learn.assert_not_called()
        self.assertEqual(self.byte_snapshot(), before)

    # {
    #   責務: [test_owned_ai_party_items_and_content_remain_byte_identical_after_battle_probe: 検証: owned ai party items and content remain byte identical after battle probe]
    #   処理: [1: 検証: owned ai party items and content remain byte identical after battle probe]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_owned_ai_party_items_and_content_remain_byte_identical_after_battle_probe(self):
        self.seed_state(current_party=["owned", None, None, None], unknown={"keep": True})
        monster = self.seed_record("owned", level=100, plus_choices=[], private={"keep": [1, 2]})
        ai = {"schema_version": 1, "battles": 132, "actions": 654, "action_preferences": {"attack": 0.99}}
        self.write("monsters/owned/ai.json", ai)
        self.write("items/items.json", {"items": {"herb": 99}, "private": True})
        self.write("parties/private.json", {"monster_ids": ["owned"]})
        before = self.byte_snapshot()
        self.invoke(records=[{"monster": monster, "ai": ai}], cases=[state_case([action("damage", 100),
                                                                                 action("pay", 7), action("flee")])])
        self.assertEqual(self.byte_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
