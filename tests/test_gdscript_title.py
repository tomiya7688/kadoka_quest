"""Godot版タイトル画面のセーブ選択・新規開始・フィールドへの切替を、専用の一時保存先と実Godotで検証します。"""

# {
#   責務: [test_gdscript_title: タイトル画面の実Godotプローブを、実セーブと分離した保存先で起動して結果を確認します]
#   フィールド: []
# }
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess

import pytest

from test_gdscript_bootstrap import GODOT, ROOT


# {
#   責務: [prepare_saves: 列挙・順序・除外の確認に使うセーブフォルダを専用の一時保存先へ作ります]
#   処理: [
#     1: state.jsonを持つ四つのセーブと、state.jsonのないフォルダを作ります
#     2: 40文字を超える名前のフォルダを作ります
#   ]
#   引数: [save_root: Godotへ渡す専用の一時保存先（Path）]
#   戻り値: [result: 作成した全ファイルの相対パスと内容の対応（dict[str, bytes]）]
# }
def prepare_saves(save_root: Path) -> dict[str, bytes]:
    # 自然順の確認のため「冒険10」が「冒険2」より後に並ぶ名前と、Linux/macOSで隠しフォルダになるドット始まりの名前を用意します。
    for name in (".adventure", "alpha", "冒険2", "冒険10", "あ" * 41):
        folder = save_root / name
        folder.mkdir(parents=True)
        (folder / "state.json").write_text('{"schema_version": 1}\n', encoding="utf-8")
    (save_root / "フォルダだけ").mkdir()
    return {str(path.relative_to(save_root)): path.read_bytes() for path in save_root.rglob("*") if path.is_file()}


# {
#   責務: [run_title_probe: タイトル画面のプローブを、セーブ名の環境変数を外した専用環境で実行し、結果を返します]
#   処理: [
#     1: 一時保存先と読み取り専用のコンテンツを指定し、KADOKA_GDSCRIPT_SAVE_NAMEを除いた環境でGodotを起動します
#     2: 実行エラーがないことを確認し、Base64のJSON結果を復元します
#   ]
#   引数: [
#     mode: プローブの検査区分。continueまたはnewです（str）
#     save_root: 専用の一時保存先（Path）
#     work: Godotの作業フォルダ（Path）
#   ]
#   戻り値: [result: プローブが出力した結果（dict）]
# }
def run_title_probe(mode: str, save_root: Path, work: Path) -> dict:
    # 共用の起動関数はセーブ名を固定してタイトルを飛ばすため、この検査では環境変数を外します。
    environment = {key: value for key, value in os.environ.items() if key != "KADOKA_GDSCRIPT_SAVE_NAME"}
    environment.update(
        KADOKA_CONTENT_ROOT=str(ROOT), KADOKA_GDSCRIPT_SAVE_ROOT=str(save_root), KADOKA_SAVE_DIR=str(work / "python-saves")
    )
    completed = subprocess.run(
        [str(GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script", "res://tests/run_title_probe.gd", "--", mode],
        cwd=work,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert "SCRIPT ERROR" not in completed.stderr, completed.stderr
    assert "ERROR:" not in completed.stderr, completed.stderr
    for line in completed.stdout.splitlines():
        if line.startswith("KADOKA_CONTRACT_RESULT="):
            return json.loads(base64.b64decode(line.split("=", 1)[1]).decode("utf-8"))
    raise AssertionError(f"No title probe result ({completed.returncode}):\n{completed.stdout}\n{completed.stderr}")


# {
#   責務: [test_title_continue_opens_selected_save_without_writing: 既存セーブの再開がセーブ名をフィールドへ渡し、保存データを変更しないことを確認します]
#   処理: [1: セーブを用意して再開区分のプローブを実行し、失敗一覧が空で、保存先のファイルが変わらないことを確認します]
#   引数: [tmp_path: 実セーブと分離した一時フォルダ（Path）]
#   戻り値: [result: なし]
# }
@pytest.mark.skipif(not GODOT, reason="KADOKA_GODOT_EXECUTABLEまたはGodotのPATH設定が必要です。")
def test_title_continue_opens_selected_save_without_writing(tmp_path):
    save_root = tmp_path / "saves"
    before = prepare_saves(save_root)
    result = run_title_probe("continue", save_root, tmp_path)
    assert result == {"ok": True, "failures": []}
    after = {str(path.relative_to(save_root)): path.read_bytes() for path in save_root.rglob("*") if path.is_file()}
    assert after == before


# {
#   責務: [test_title_new_game_defers_folder_creation_until_first_save: 新しいセーブ名での開始がフィールドへ切り替わり、保存するまでフォルダを作らないことを確認します]
#   処理: [1: セーブを用意して新規区分のプローブを実行し、失敗一覧が空で、新しいセーブ名のフォルダがないことを確認します]
#   引数: [tmp_path: 実セーブと分離した一時フォルダ（Path）]
#   戻り値: [result: なし]
# }
@pytest.mark.skipif(not GODOT, reason="KADOKA_GODOT_EXECUTABLEまたはGodotのPATH設定が必要です。")
def test_title_new_game_defers_folder_creation_until_first_save(tmp_path):
    save_root = tmp_path / "saves"
    before = prepare_saves(save_root)
    result = run_title_probe("new", save_root, tmp_path)
    assert result == {"ok": True, "failures": []}
    assert not (save_root / "新しい冒険").exists()
    after = {str(path.relative_to(save_root)): path.read_bytes() for path in save_root.rglob("*") if path.is_file()}
    assert after == before


# {
#   責務: [test_title_is_main_scene_and_keeps_field_entry_for_automation: 起動画面がタイトルで、セーブ名の環境変数がある自動実行ではタイトルを飛ばす経路があることを確認します]
#   処理: [1: project.godotの起動画面と、タイトルのアプリケーションが環境変数でフィールドへ直行することをソースから確認します]
#   引数: []
#   戻り値: [result: なし]
# }
def test_title_is_main_scene_and_keeps_field_entry_for_automation():
    settings = (ROOT / "gdscript/project.godot").read_text(encoding="utf-8")
    assert 'run/main_scene="res://scenes/title.tscn"' in settings
    source = (ROOT / "gdscript/application/title_application.gd").read_text(encoding="utf-8")
    assert 'OS.get_environment("KADOKA_GDSCRIPT_SAVE_NAME")' in source
    # 表示部品は保存やファイル操作を行わず、選択結果をシグナルで返すだけです。
    view = (ROOT / "gdscript/ui/title_view.gd").read_text(encoding="utf-8")
    for forbidden in ("FileAccess", "DirAccess", "save_profile", "res://data/"):
        assert forbidden not in view
