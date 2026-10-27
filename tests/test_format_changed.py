"""追加したPythonファイルだけを整形する道具が、既存ファイルを書き換えず、比較元がない場合に失敗することを検証します。"""

# {
#   責務: [test_format_changed: 一時Gitリポジトリで、整形対象の選び方・整形確認の失敗・整形後の成功・既存ファイルの保護・比較元の欠落を検証します]
#   フィールド: [UNFORMATTED: Ruffが書き換える形の短いPythonコード（str）]
# }
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("format_changed", ROOT / "tools/format/script/format_changed.py")
format_changed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(format_changed)
UNFORMATTED = "x = {  'a':1 }\n"


# {
#   責務: [git: 一時リポジトリでGitコマンドを実行し、失敗を例外にします]
#   処理: [1: 指定フォルダでGitを実行します]
#   引数: [
#     repository: 一時Gitリポジトリのフォルダ（Path）
#     args: Gitへ渡す引数（str）
#   ]
#   戻り値: [result: なし（None）]
# }
def git(repository: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repository, check=True, capture_output=True)


# {
#   責務: [repository: 既存ファイルをmainへコミットし、作業ブランチで追加・index追加・未追跡・既存変更の四種類を作った一時リポジトリを用意します]
#   処理: [
#     1: mainへ整形されていない既存ファイルをコミットします
#     2: 作業ブランチでコミット済みの追加、indexだけの追加、未追跡の追加、既存ファイルの変更を作ります
#     3: 道具が使うリポジトリ直下を一時リポジトリへ差し替えます
#   ]
#   引数: [
#     tmp_path: 一時フォルダ（Path）
#     monkeypatch: 道具のリポジトリ直下を差し替えるpytestの道具
#   ]
#   戻り値: [result: 一時Gitリポジトリのフォルダ（Path）]
# }
@pytest.fixture
def repository(tmp_path, monkeypatch):
    git(tmp_path, "init", "--initial-branch=main")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "test")
    (tmp_path / "existing.py").write_text(UNFORMATTED, encoding="utf-8")
    git(tmp_path, "add", "existing.py")
    git(tmp_path, "commit", "-m", "base")
    git(tmp_path, "switch", "-c", "work")
    (tmp_path / "committed.py").write_text(UNFORMATTED, encoding="utf-8")
    git(tmp_path, "add", "committed.py")
    git(tmp_path, "commit", "-m", "add")
    (tmp_path / "staged.py").write_text(UNFORMATTED, encoding="utf-8")
    git(tmp_path, "add", "staged.py")
    (tmp_path / "untracked.py").write_text(UNFORMATTED, encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not python\n", encoding="utf-8")
    # 既存ファイルは変更しても対象にせず、他の作業者の行を書き換えないことを確かめます。
    (tmp_path / "existing.py").write_text(UNFORMATTED + "y = 1\n", encoding="utf-8")
    monkeypatch.setattr(format_changed, "ROOT", tmp_path)
    return tmp_path


# {
#   責務: [test_only_added_python_files_are_targets: コミット済み・index・未追跡の追加Pythonファイルだけが対象になり、既存ファイルとPython以外は対象外であることを確認します]
#   処理: [1: 比較元mainからの対象一覧を取得して比較します]
#   引数: [repository: 一時Gitリポジトリのフォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
def test_only_added_python_files_are_targets(repository):
    assert format_changed.added_python_files("main") == ["committed.py", "staged.py", "untracked.py"]


# {
#   責務: [test_check_fails_then_format_fixes_without_touching_existing: 整形確認が整形漏れで失敗し、整形後に成功し、既存ファイルは変わらないことを確認します]
#   処理: [
#     1: --checkの終了コードが失敗で、対象ファイルが書き換わらないことを確認します
#     2: 整形してから--checkが成功し、既存ファイルの内容が変更前のままであることを確認します
#   ]
#   引数: [repository: 一時Gitリポジトリのフォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
@pytest.mark.skipif(importlib.util.find_spec("ruff") is None, reason="tools/format/requirements.txtのRuffが必要です")
def test_check_fails_then_format_fixes_without_touching_existing(repository):
    existing_before = (repository / "existing.py").read_text(encoding="utf-8")
    assert format_changed.main(["--check", "--base", "main"]) != 0
    assert (repository / "committed.py").read_text(encoding="utf-8") == UNFORMATTED
    assert format_changed.main(["--base", "main"]) == 0
    assert format_changed.main(["--check", "--base", "main"]) == 0
    assert (repository / "committed.py").read_text(encoding="utf-8") == 'x = {"a": 1}\n'
    assert (repository / "existing.py").read_text(encoding="utf-8") == existing_before


# {
#   責務: [test_missing_base_fails_instead_of_passing: 比較元が見つからない場合に、対象なしの成功ではなく終了コード2で失敗することを確認します]
#   処理: [1: 存在しない比較元を指定して実行し、終了コードを確認します]
#   引数: [repository: 一時Gitリポジトリのフォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
def test_missing_base_fails_instead_of_passing(repository):
    assert format_changed.main(["--check", "--base", "origin/missing"]) == 2


# {
#   責務: [test_default_base_follows_pull_request_target: CIのPull Requestでは対象ブランチ、それ以外ではorigin/mainを比較元にすることを確認します]
#   処理: [1: GITHUB_BASE_REFの有無で既定の比較元を確認します]
#   引数: [monkeypatch: 環境変数を一時的に変更するpytestの道具]
#   戻り値: [result: なし（None）]
# }
def test_default_base_follows_pull_request_target(monkeypatch):
    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
    assert format_changed.default_base() == "origin/main"
    monkeypatch.setenv("GITHUB_BASE_REF", "release")
    assert format_changed.default_base() == "origin/release"
