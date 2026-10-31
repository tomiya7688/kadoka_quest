"""追加したPythonファイルとGDScriptファイルだけを整形する道具が、既存ファイルを書き換えず、比較元がない場合に失敗することを検証します。"""

# {
#   責務: [test_format_changed: 一時Gitリポジトリで、整形対象の選び方・整形確認の失敗・整形後の成功・既存ファイルの保護・比較元の欠落を検証します]
#   フィールド: [
#     UNFORMATTED: Ruffが書き換える形の短いPythonコード（str）
#     UNFORMATTED_GD: gdformatが書き換える形の、改行がLFだけの短いGDScriptコード（str）
#     FORMATTERS_INSTALLED: tools/format/requirements.txtのRuffとgdtoolkitが両方とも導入されているか（bool）
#   ]
# }
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("format_changed", ROOT / "tools/format/script/format_changed.py")
format_changed = importlib.util.module_from_spec(_spec)
# dataclassは定義したモジュールをsys.modulesから引くため、読み込む前に登録します。
sys.modules[_spec.name] = format_changed
_spec.loader.exec_module(format_changed)
UNFORMATTED = "x = {  'a':1 }\n"
UNFORMATTED_GD = 'extends Node\nvar x={  "a":1 }\n'
FORMATTERS_INSTALLED = all(importlib.util.find_spec(module) is not None for module in ("ruff", "gdtoolkit"))


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
#     3: 日本語名の未追跡ファイルと、既存・追加のGDScriptファイルを加え、道具が使うリポジトリ直下を一時リポジトリへ差し替えます
#   ]
#   引数: [
#     tmp_path: 一時フォルダ（Path）
#     monkeypatch: 道具のリポジトリ直下を差し替えるpytestの道具
#   ]
#   戻り値: [result: 一時Gitリポジトリのフォルダ（Path）]
# }
@pytest.fixture
def repository(tmp_path, monkeypatch):
    # Gitのフックなどから実行された場合も、別のリポジトリや利用者の署名設定を使わないようにします。
    for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(variable, raising=False)
    git(tmp_path, "init", "--initial-branch=main")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "test")
    git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "existing.py").write_text(UNFORMATTED, encoding="utf-8")
    (tmp_path / "existing.gd").write_bytes(UNFORMATTED_GD.encode("utf-8"))
    git(tmp_path, "add", "existing.py", "existing.gd")
    git(tmp_path, "commit", "-m", "base")
    git(tmp_path, "switch", "-c", "work")
    (tmp_path / "committed.py").write_text(UNFORMATTED, encoding="utf-8")
    # 改行の変換を確かめるため、Windowsでも改行をLFのまま書き込みます。
    (tmp_path / "committed.gd").write_bytes(UNFORMATTED_GD.encode("utf-8"))
    git(tmp_path, "add", "committed.py", "committed.gd")
    git(tmp_path, "commit", "-m", "add")
    (tmp_path / "staged.py").write_text(UNFORMATTED, encoding="utf-8")
    git(tmp_path, "add", "staged.py")
    (tmp_path / "untracked.py").write_text(UNFORMATTED, encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not python\n", encoding="utf-8")
    # Gitが既定で引用符付きの8進表記にする日本語名も、対象から漏れないことを確かめます。
    (tmp_path / "日本語.py").write_text(UNFORMATTED, encoding="utf-8")
    # 既存ファイルは変更しても対象にせず、他の作業者の行を書き換えないことを確かめます。
    (tmp_path / "existing.py").write_text(UNFORMATTED + "y = 1\n", encoding="utf-8")
    (tmp_path / "existing.gd").write_bytes((UNFORMATTED_GD + "var y=1\n").encode("utf-8"))
    monkeypatch.setattr(format_changed, "ROOT", tmp_path)
    return tmp_path


# {
#   責務: [test_only_added_files_are_targets: コミット済み・index・未追跡の追加ファイルだけが拡張子ごとの対象になり、既存ファイルと対象外の拡張子は含まれないことを確認します]
#   処理: [1: 比較元mainからの.pyと.gdの対象一覧を取得して比較します]
#   引数: [repository: 一時Gitリポジトリのフォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
def test_only_added_files_are_targets(repository):
    assert format_changed.added_files("main", ".py") == ["committed.py", "staged.py", "untracked.py", "日本語.py"]
    assert format_changed.added_files("main", ".gd") == ["committed.gd"]


# {
#   責務: [test_check_fails_then_format_fixes_without_touching_existing: 整形確認が整形漏れで失敗し、整形後に成功し、既存ファイルは変わらず、GDScriptの改行がLFのままであることを確認します]
#   処理: [
#     1: --checkの終了コードが失敗で、対象ファイルが書き換わらないことを確認します
#     2: 整形してから--checkが成功し、PythonとGDScriptの追加ファイルが整形され、既存ファイルの内容が変更前のままであることを確認します
#     3: 整形前にLFだけだったGDScriptファイルが、WindowsでもCRLFを含まないことを確認します
#   ]
#   引数: [repository: 一時Gitリポジトリのフォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
@pytest.mark.skipif(not FORMATTERS_INSTALLED, reason="tools/format/requirements.txtのRuffとgdtoolkitが必要です")
def test_check_fails_then_format_fixes_without_touching_existing(repository):
    existing_before = (repository / "existing.py").read_text(encoding="utf-8")
    existing_gd_before = (repository / "existing.gd").read_bytes()
    assert format_changed.main(["--check", "--base", "main"]) != 0
    assert (repository / "committed.py").read_text(encoding="utf-8") == UNFORMATTED
    assert format_changed.main(["--base", "main"]) == 0
    assert format_changed.main(["--check", "--base", "main"]) == 0
    for name in ("committed.py", "staged.py", "untracked.py", "日本語.py"):
        assert (repository / name).read_text(encoding="utf-8") == 'x = {"a": 1}\n', name
    assert (repository / "existing.py").read_text(encoding="utf-8") == existing_before
    # gdformatはWindowsでCRLFを書き込むため、道具がLFへ戻したことをバイト単位で確かめます。
    assert (repository / "committed.gd").read_bytes() == b'extends Node\nvar x = {"a": 1}\n'
    assert (repository / "existing.gd").read_bytes() == existing_gd_before


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


# {
#   責務: [test_missing_formatter_fails_with_setup_code: Ruffまたはgdtoolkitが導入されていない場合に、整形漏れと区別できる終了コード2と、足りない道具の名前と導入方法を返すことを確認します]
#   処理: [1: Ruffとgdtoolkitのそれぞれについて、モジュール探索を見つからない結果へ差し替えて--checkを実行し、終了コードと案内を確認します]
#   引数: [
#     repository: 一時Gitリポジトリのフォルダ（Path）
#     monkeypatch: モジュール探索を一時的に差し替えるpytestの道具
#     capsys: 標準出力を取得するpytestの道具
#     module: 見つからない結果へ差し替えるformatterのPythonモジュール名（str）
#     name: 案内に表示されるはずのformatterの名前（str）
#   ]
#   戻り値: [result: なし（None）]
# }
@pytest.mark.parametrize(("module", "name"), [("ruff", "Ruff"), ("gdtoolkit", "gdformat")])
def test_missing_formatter_fails_with_setup_code(repository, monkeypatch, capsys, module, name):
    original = format_changed.importlib.util.find_spec
    monkeypatch.setattr(
        format_changed.importlib.util, "find_spec", lambda target, *args: None if target == module else original(target, *args)
    )
    assert format_changed.main(["--check", "--base", "main"]) == 2
    output = capsys.readouterr().out
    assert name in output and "がありません" in output and "tools/format/requirements.txt" in output
