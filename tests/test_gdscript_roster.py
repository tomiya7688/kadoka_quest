"""Real-Godot owned-individual bootstrap/read-only UI, isolated from all user saves."""
# {
#   責務: [test_gdscript_roster: Real-Godot owned-individual bootstrap/read-only UI, isolated from all user saves.]
#   フィールド: []
# }
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from kadoka_quest.core.ai import default_ai
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import DEFAULT_STATE, StateStore

ROOT = Path(__file__).resolve().parents[1]
GODOT = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")


# {
#   責務: [GDScriptRosterBoundaryTests: gdscript・所有個体台帳・boundary・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class GDScriptRosterBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_record_rules_and_renderer_do_not_access_persistence: 検証: record rules and renderer do not access persistence]
    #   処理: [1: 検証: record rules and renderer do not access persistence]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_record_rules_and_renderer_do_not_access_persistence(self):
        paths = ("engine/monster_record_contract.gd", "ui/roster_view.gd")
        for path in paths:
            source = (ROOT / "gdscript" / path).read_text(encoding="utf-8")
            for forbidden in ("FileAccess.", "DirAccess.", "load_species(", "write_atomic("):
                self.assertNotIn(forbidden, source)
        self.assertIn("extends RefCounted", (ROOT / "gdscript" / paths[0]).read_text(encoding="utf-8"))


# {
#   責務: [GDScriptRosterTests: gdscript・所有個体台帳・testsの状態と振る舞いを担当する]
#   フィールド: [
#     content: content
#     saves: saves
#     profile: プロファイル
#     legacy: legacy
#   ]
# }
@unittest.skipUnless(GODOT, "Set KADOKA_GODOT_EXECUTABLE for real roster/keyboard probes")
class GDScriptRosterTests(unittest.TestCase):
    # {
    #   責務: [setUp: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kadoka-gdscript-roster-")
        self.addCleanup(temporary.cleanup)
        self.content = Path(temporary.name)
        shutil.copytree(ROOT / "data", self.content / "data")
        shutil.copytree(ROOT / "assets", self.content / "assets")
        self.saves = self.content / "gd-saves"
        self.profile = self.saves / "default"
        self.legacy = self.content / "python-saves"
        self.legacy.mkdir()
        (self.legacy / "sentinel.json").write_text('{"keep":true}', encoding="utf-8")

    # {
    #   責務: [probe: gdscript・所有個体台帳・testsのprobeを求める]
    #   処理: [1: gdscript・所有個体台帳・testsのprobeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     actions: actions
    #     contracts: contracts
    #   ]
    #   戻り値: [result: gdscript・所有個体台帳・testsのprobeを求めるための結果（型注釈なし）]
    # }
    def probe(self, actions=(), **contracts):
        fixture = self.content / "probe.json"
        fixture.write_text(json.dumps({"actions": list(actions), **contracts}, ensure_ascii=False), encoding="utf-8")
        environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content), KADOKA_SAVE_DIR=str(self.legacy),
                           KADOKA_GDSCRIPT_SAVE_ROOT=str(self.saves), KADOKA_GDSCRIPT_SAVE_NAME="default")
        result = subprocess.run(
            [str(GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
             "res://tests/run_roster_probe.gd", "--", str(fixture)],
            cwd=self.content, env=environment, text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout[-1200:])
        self.assertNotIn("SCRIPT ERROR", result.stderr)
        for line in result.stdout.splitlines():
            if line.startswith("KADOKA_ROSTER_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]).decode("utf-8"))
        self.fail(result.stdout[-1200:] + result.stderr)

    # {
    #   責務: [seed_state: テスト専用保存先へケース別設定を持つ初期state.jsonを作ります]
    #   処理: [1: 既定状態を複製してinventoryを除き、指定設定を反映して専用保存先へ出力します]
    #   引数: [
    #     self: 処理対象インスタンス
    #     changes: current_partyなど、専用状態の既定値を置き換える設定（dict）
    #   ]
    #   戻り値: [result: 専用領域へ出力した状態辞書（dict）]
    # }
    def seed_state(self, **changes):
        state = json.loads(json.dumps(DEFAULT_STATE, ensure_ascii=False))
        state.pop("inventory")
        state.update(changes)
        self.write("state.json", state)
        return state

    # {
    #   責務: [write: テスト専用保存先の指定相対パスへJSONを作ります]
    #   処理: [1: 専用保存先の親フォルダを作り、UTF-8のJSONを出力します]
    #   引数: [
    #     self: 処理対象インスタンス
    #     relative: 専用profileからの保存ファイルの相対パス（str）
    #     value: 専用テストで保存するJSON互換値
    #   ]
    #   戻り値: [result: 専用領域へ作成したファイルのパス（Path）]
    # }
    def write(self, relative, value):
        path = self.profile / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    # {
    #   責務: [seed_record: 専用保存先へモンスター個体と既定の学習AIを作ります]
    #   処理: [1: 指定種族の個体へケース別設定を反映し、個体JSONとAI JSONを出力します]
    #   引数: [
    #     self: 処理対象インスタンス
    #     folder_id: 専用monstersフォルダ内で作る個体フォルダのID（str）
    #     species_id: 専用個体の種族ID。省略時slime（str）
    #     changes: levelやnameなど、専用個体の既定値を置き換える設定（dict）
    #   ]
    #   戻り値: [result: 専用保存先へ出力した個体定義（dict）]
    # }
    def seed_record(self, folder_id, species_id="slime", **changes):
        monster = {"schema_version": 1, "id": folder_id, "species_id": species_id, "name": f"個体{folder_id}",
                   "level": 42, "experience": 17, "plus_choices": ["custom_plus"], "equipment_id": None}
        monster.update(changes)
        self.write(f"monsters/{folder_id}/monster.json", monster)
        self.write(f"monsters/{folder_id}/ai.json", default_ai("normal"))
        return monster

    # {
    #   責務: [saved_files: 専用セーブ領域の相対パスとbyte列を保持し、再保存前後を比較可能にします]
    #   処理: [1: 専用領域のファイルを列挙し、指定時だけstate.jsonを比較対象から除きます]
    #   引数: [
    #     self: 検証専用セーブ領域profileを持つテストケース
    #     exclude_state: state.jsonを比較から除く場合はTrue（bool）
    #   ]
    #   戻り値: [result: profile基準の相対パスをキーとするbyte列の辞書（dict[str, bytes]）]
    # }
    def saved_files(self, exclude_state=False):
        return {str(path.relative_to(self.profile)): path.read_bytes() for path in self.profile.rglob("*")
                if path.is_file() and not (exclude_state and path.name == "state.json")}

    # {
    #   責務: [test_default_ai_matches_python_all_profiles_and_tactics: 七つのAIプロファイルと五つの作戦でGodot初期AIがPythonと一致するか確認します]
    #   処理: [1: 未知プロファイル/作戦を含む全組合せを作り、Godotの生成結果をdefault_aiと比較します]
    #   引数: [self: 専用のGodot所有個体プローブを持つテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_default_ai_matches_python_all_profiles_and_tactics(self):
        cases = [{"profile": profile, "tactic": tactic}
                 for profile in ("normal", "support", "trickster", "dice", "maru", "kadoka", "mod_profile")
                 for tactic in ("balanced", "aggressive", "careful", "variety", "invalid")]
        actual = self.probe(defaults=cases)["defaults"]
        for case, value in zip(cases, actual):
            with self.subTest(**case):
                self.assertEqual(value, default_ai(**case))

    # {
    #   責務: [test_individual_documents_match_python_factory_and_level_clamp: 七種族の個体/AI生成とLv1〜100への制限がPythonと一致するか確認します]
    #   処理: [1: 各種族のLv-9/1/42/100/200をGodotで生成し、PythonのMonsterStore.create結果と比較します]
    #   引数: [self: 正規dataの専用コピーとGodotプローブを持つテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_individual_documents_match_python_factory_and_level_clamp(self):
        cases = [{"id": f"reference_{index}_{level}", "species_id": species, "level": level, "name": "比較個体"}
                 for index, species in enumerate(("hero", "slime", "ball_slime", "metal_slime", "ghost", "maru", "kadoka"))
                 for level in (-9, 1, 42, 100, 200)]
        actual = self.probe(records=cases)["records"]
        reference = MonsterStore(self.content / "reference-monsters", GameRepository(self.content / "data"))
        for case, value in zip(cases, actual):
            with self.subTest(species=case["species_id"], level=case["level"]):
                expected = reference.create(case["species_id"], case["name"], case["level"],
                                            source="starter", monster_id=case["id"])
                self.assertEqual(value, {"monster": expected.monster, "ai": expected.ai})

    # {
    #   責務: [test_new_save_starters_party_reload_and_repeat_save_do_not_duplicate: 新規セーブの主人公/ボールスライムと再読込時の個体・パーティ保持を確認します]
    #   処理: [1: 保存/再読込後の個体数とbyte保持を比較し、Python互換・一時フォルダ不残留・旧保存領域の不変を確認します]
    #   引数: [self: 専用セーブと旧領域ダミーを持つテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_new_save_starters_party_reload_and_repeat_save_do_not_duplicate(self):
        result = self.probe([{"kind": "key", "key": "F5"}, {"kind": "key", "key": "F6"}])["observations"]
        records = result[-1]["owned"]["records"]
        self.assertEqual({record["monster"]["species_id"] for record in records.values()}, {"hero", "ball_slime"})
        members = [entry["id"] for entry in result[-1]["owned"]["party"]]
        self.assertEqual([records[id]["monster"]["species_id"] for id in members], ["hero", "ball_slime"])
        self.assertIn("ボールスライム", result[-1]["text"])
        before = self.saved_files(exclude_state=True)
        again = self.probe([{"kind": "save"}, {"kind": "key", "key": "F6"}])["observations"][-1]
        self.assertEqual(set(again["owned"]["records"]), set(records))
        self.assertEqual(self.saved_files(exclude_state=True), before)
        python = MonsterStore(self.profile / "monsters", GameRepository(self.content / "data"))
        self.assertEqual({record.monster_id for record in python.list_records()}, set(records))
        self.assertEqual(StateStore(self.profile / "state.json").load()["current_party"], members)
        self.assertFalse(any(path.name.startswith(".pending_") for path in (self.profile / "monsters").iterdir()))
        self.assertEqual((self.legacy / "sentinel.json").read_text(encoding="utf-8"), '{"keep":true}')

    # {
    #   責務: [test_existing_individual_ai_unknown_keys_and_party_order_are_readonly: 所有一覧表示と再保存が個体/AIのMOD情報や欠損枠を含むパーティ順を保持するか確認します]
    #   処理: [1: 専用個体/AIの既知/未知情報とパーティを用意し、表示/保存後のbyte列と並びを比較します]
    #   引数: [self: 専用セーブの所有個体と一覧表示を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_existing_individual_ai_unknown_keys_and_party_order_are_readonly(self):
        state = self.seed_state(current_party=["まるA", None, "missing", "hero_01"])
        self.seed_record("hero_01", "hero", name="自分", level=100)
        monster = self.seed_record("まるA", "maru", name="まる", mod_field={"kept": [True, "値"]})
        ai = default_ai("maru", "careful")
        ai.update(battles=123, actions=999, action_preferences={"heal": 0.13},
                  context_actions={"hp_low": 200}, mod_ai={"leave": "alone"})
        self.write("monsters/まるA/ai.json", ai)
        before = self.saved_files()
        result = self.probe([{"kind": "key", "key": "F6"}])["observations"][-1]
        self.assertEqual(result["owned"]["records"]["まるA"]["monster"], monster)
        self.assertEqual(result["owned"]["records"]["まるA"]["ai"], ai)
        self.assertEqual([entry["id"] for entry in result["owned"]["party"]], state["current_party"])
        self.assertIn("読込不可: missing", result["text"])
        self.assertEqual(self.saved_files(), before)
        self.probe([{"kind": "save"}])
        expected = {key: value for key, value in before.items() if key != "state.json"}
        self.assertEqual(self.saved_files(exclude_state=True), expected)
        stored = json.loads((self.profile / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["current_party"], state["current_party"])

    # {
    #   責務: [test_unlimited_roster_scroll_and_modal_input_does_not_move_or_save: 百二十体の所有一覧スクロールと、一覧表示中の移動/保存抑止を確認します]
    #   処理: [1: 専用一覧で末尾/先頭/ページ移動を操作し、閉じるまで座標と保存byte列を保持するか確認します]
    #   引数: [self: 専用セーブで一覧操作を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_unlimited_roster_scroll_and_modal_input_does_not_move_or_save(self):
        self.seed_state(current_party=["owned_000"])
        for index in range(120):
            self.seed_record(f"owned_{index:03}", name=f"仲間{index}")
        before = self.saved_files()
        observations = self.probe([{"kind": "key", "key": key} for key in
                                   ("F6", "END", "HOME", "PAGEDOWN", "DOWN", "F5", "ESC", "RIGHT")])["observations"]
        self.assertEqual(len(observations[1]["owned"]["records"]), 120)
        self.assertIn("仲間119", observations[1]["text"])
        self.assertGreater(observations[2]["scroll"], 0)
        self.assertEqual(observations[3]["scroll"], 0)
        self.assertGreater(observations[4]["scroll"], 0)
        self.assertEqual([(item["x"], item["y"]) for item in observations[:7]], [(18, 14)] * 7)
        self.assertFalse(observations[7]["visible"])
        self.assertEqual((observations[-1]["x"], observations[-1]["y"]), (19, 14))
        self.assertEqual(self.saved_files(), before)

    # {
    #   責務: [test_invalid_records_are_reported_without_deletion_or_repair: 読込不能な個体を報告し、勝手な削除や修復を行わないことを検証します]
    #   処理: [1: 不正な専用個体レコードを用意し、読込拒否の表示と原本保持を確認します]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_records_are_reported_without_deletion_or_repair(self):
        self.seed_state(current_party=["valid", "bad_0", None, "missing"])
        self.seed_record("valid")
        cases = [{"level": 0}, {"level": 101}, {"level": 1.5}, {"level": True}, {"id": "../escape"},
                 {"species_id": "missing"}, {"schema_version": 99}, {"plus_choices": "not-an-array"}, {"name": 42}]
        for index, changes in enumerate(cases):
            self.seed_record(f"bad_{index}", **changes)
        self.seed_record("broken_ai")
        (self.profile / "monsters/broken_ai/ai.json").write_text('{"broken":', encoding="utf-8")
        self.seed_record("future_ai")
        self.write("monsters/future_ai/ai.json", {"schema_version": 99})
        before = self.saved_files()
        result = self.probe([{"kind": "key", "key": "F6"}])["observations"][-1]
        self.assertEqual(set(result["owned"]["records"]), {"valid"})
        self.assertEqual(len(result["owned"]["warnings"]), len(cases) + 2)
        self.assertIn("読込不可: bad_0", result["text"])
        self.assertEqual(self.saved_files(), before)

    # {
    #   責務: [test_scroll_wheel_and_upward_keyboard_navigation: 検証: scroll wheel and upward keyboard navigation]
    #   処理: [1: 検証: scroll wheel and upward keyboard navigation]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_scroll_wheel_and_upward_keyboard_navigation(self):
        self.seed_state()
        for index in range(25):
            self.seed_record(f"scroll_{index:02}")
        observations = self.probe([
            {"kind": "key", "key": "F6"}, {"kind": "wheel"},
            {"kind": "key", "key": "END"}, {"kind": "key", "key": "PAGEUP"},
            {"kind": "key", "key": "UP"},
        ])["observations"]
        self.assertGreater(observations[2]["scroll"], 0)
        self.assertLess(observations[4]["scroll"], observations[3]["scroll"])
        self.assertLess(observations[5]["scroll"], observations[4]["scroll"])

    # {
    #   責務: [test_existing_id_and_path_traversal_are_never_overwritten: 検証: existing id and path traversal are never overwritten]
    #   処理: [1: 検証: existing id and path traversal are never overwritten]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_existing_id_and_path_traversal_are_never_overwritten(self):
        self.seed_state()
        self.seed_record("existing")
        before = self.saved_files()
        ids = ["existing", "../escape", "a/b", "a\\b", "CON", "nul.txt", "", ".."]
        observations = self.probe([{"kind": "create", "id": id} for id in ids])["observations"][1:]
        for id, observation in zip(ids, observations):
            with self.subTest(id=id):
                self.assertFalse(observation["outcome"]["ok"])
        self.assertEqual(self.saved_files(), before)
        self.assertFalse((self.saves / "escape").exists())

    # {
    #   責務: [test_retry_after_failed_state_write_reuses_published_starter_ids: 検証: retry after failed state write reuses published starter ids]
    #   処理: [1: 検証: retry after failed state write reuses published starter ids]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_retry_after_failed_state_write_reuses_published_starter_ids(self):
        blocked = self.profile / "state.json"
        blocked.mkdir(parents=True)
        observation = self.probe([{"kind": "save"}])["observations"][-1]
        self.assertFalse(observation["outcome"])
        before = self.saved_files(exclude_state=True)
        ids = {path.name for path in (self.profile / "monsters").iterdir()}
        self.assertEqual(len(ids), 2)
        blocked.rmdir()  # Exact empty directory in this test's private fixture.
        retry = self.probe([{"kind": "save"}])["observations"][-1]
        self.assertTrue(retry["outcome"])
        self.assertEqual(set(retry["owned"]["records"]), ids)
        self.assertEqual(self.saved_files(exclude_state=True), before)

    # {
    #   責務: [test_existing_starters_are_reused_on_first_save_with_ai_unchanged: 検証: existing starters are reused on first save with ai unchanged]
    #   処理: [1: 検証: existing starters are reused on first save with ai unchanged]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_existing_starters_are_reused_on_first_save_with_ai_unchanged(self):
        self.seed_record("my_hero", "hero")
        self.seed_record("my_ball", "ball_slime")
        self.seed_record("extra", "ghost")
        before = self.saved_files()
        result = self.probe([{"kind": "save"}])["observations"][-1]
        self.assertTrue(result["outcome"])
        self.assertEqual(set(result["owned"]["records"]), {"my_hero", "my_ball", "extra"})
        self.assertEqual([entry["id"] for entry in result["owned"]["party"]], ["my_hero", "my_ball"])
        for relative, value in before.items():
            self.assertEqual((self.profile / relative).read_bytes(), value)

    # {
    #   責務: [test_missing_starter_definition_refuses_first_save_before_creation: 検証: missing starter definition refuses first save before creation]
    #   処理: [1: 検証: missing starter definition refuses first save before creation]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_missing_starter_definition_refuses_first_save_before_creation(self):
        (self.content / "data/species/ball_slime/species.json").unlink()
        result = self.probe([{"kind": "save"}])["observations"][-1]
        self.assertFalse(result["outcome"])
        self.assertIn("初期種族", result["status"])
        self.assertFalse(self.profile.exists())

    # {
    #   責務: [test_invalid_orphan_prevents_duplicate_starters_without_repair: 検証: invalid orphan prevents duplicate starters without repair]
    #   処理: [1: 検証: invalid orphan prevents duplicate starters without repair]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_orphan_prevents_duplicate_starters_without_repair(self):
        self.seed_record("orphan", level=101)
        before = self.saved_files()
        result = self.probe([{"kind": "save"}])["observations"][-1]
        self.assertFalse(result["outcome"])
        self.assertIn("既存個体の問題", result["status"])
        self.assertEqual(self.saved_files(), before)
        self.assertFalse((self.profile / "state.json").exists())

    # {
    #   責務: [test_invalid_party_structure_is_reported_and_not_rewritten: 検証: invalid party structure is reported and not rewritten]
    #   処理: [1: 検証: invalid party structure is reported and not rewritten]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_party_structure_is_reported_and_not_rewritten(self):
        self.seed_state(current_party={"mod": "not a list"})
        self.seed_record("owned")
        before = self.saved_files()
        result = self.probe([{"kind": "key", "key": "F6"}])["observations"][-1]
        self.assertEqual(set(result["owned"]["records"]), {"owned"})
        self.assertIn("current_partyが配列ではありません", result["text"])
        self.assertEqual(self.saved_files(), before)

    # {
    #   責務: [test_unsaved_roster_ui_is_readonly_and_does_not_create_a_profile: 検証: unsaved roster ui is readonly and does not create a profile]
    #   処理: [1: 検証: unsaved roster ui is readonly and does not create a profile]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_unsaved_roster_ui_is_readonly_and_does_not_create_a_profile(self):
        observations = self.probe([{"kind": "key", "key": key} for key in ("F6", "F5", "RIGHT", "F6")])["observations"]
        self.assertIn("F5で初期仲間", observations[1]["text"])
        self.assertTrue(observations[1]["visible"])
        self.assertFalse(observations[-1]["visible"])
        self.assertEqual((observations[-1]["x"], observations[-1]["y"]), (18, 14))
        self.assertFalse(self.saves.exists())

    # {
    #   責務: [test_previous_prototype_empty_save_is_not_silently_given_new_members: 検証: previous prototype empty save is not silently given new members]
    #   処理: [1: 検証: previous prototype empty save is not silently given new members]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_previous_prototype_empty_save_is_not_silently_given_new_members(self):
        self.seed_state()
        result = self.probe([{"kind": "save"}, {"kind": "key", "key": "F6"}])["observations"][-1]
        self.assertEqual(result["owned"]["records"], {})
        self.assertEqual(json.loads((self.profile / "state.json").read_text(encoding="utf-8"))["current_party"], [])
        self.assertFalse((self.profile / "monsters").exists())
