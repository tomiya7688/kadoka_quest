"""Godotを使うテストへgodotマーカーを付け、Godotが必須の実行ではGodot不在によるskipを失敗にします。"""

# {
#   責務: [conftest: 実Godotを起動するテストを-m godotで選べるようにし、KADOKA_REQUIRE_GODOT=1の実行でGodotの未設定やskipを成功扱いにしないようにします]
#   フィールド: [
#     REQUIRE_VARIABLE: Godotを必須にする環境変数の名前（str）
#     _godot_skips: Godotがないためにskipされたテストのnode IDと理由（list[str]）
#     _godot_files: ファイルごとの「Godotを使うか」の判定結果（dict[Path, bool]）
#   ]
# }
from __future__ import annotations

import os
from pathlib import Path
import shutil

import pytest


REQUIRE_VARIABLE = "KADOKA_REQUIRE_GODOT"
_godot_skips: list[str] = []
_godot_files: dict[Path, bool] = {}


# {
#   責務: [godot_required: KADOKA_REQUIRE_GODOT=1で、Godotのテストを必ず実行する設定かを返します]
#   処理: [1: 環境変数が1かどうかを返します]
#   引数: []
#   戻り値: [result: Godotが必須ならtrue（bool）]
# }
def godot_required() -> bool:
    return os.environ.get(REQUIRE_VARIABLE) == "1"


# {
#   責務: [find_godot: テストと同じ規則で、KADOKA_GODOT_EXECUTABLEまたはPATHからGodotの実行ファイルを探します]
#   処理: [1: 環境変数の指定を優先し、なければPATHのgodot・godot4を探し、実在するファイルだけを返します]
#   引数: []
#   戻り値: [result: 実在するGodotの実行ファイルのパス。見つからなければNone（str | None）]
# }
def find_godot() -> str | None:
    candidate = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    return candidate if candidate and Path(candidate).is_file() else None


# {
#   責務: [pytest_configure: godotマーカーを登録し、Godotが必須なのに見つからない場合はテストを始める前に止めます]
#   処理: [
#     1: -m godotで選べるようにマーカーを登録します
#     2: KADOKA_REQUIRE_GODOT=1でGodotが見つからなければ、理由付きの使用エラーにします
#   ]
#   引数: [config: pytestの設定（pytest.Config）]
#   戻り値: [result: なし（None）]
# }
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "godot: 実Godotを起動するテスト。CIのGodotジョブは-m godotで選びます")
    # 全テストをskipしたうえで成功と表示する前に、設定の誤りとして止めます。
    if godot_required() and find_godot() is None:
        raise pytest.UsageError(
            f"{REQUIRE_VARIABLE}=1ですが、KADOKA_GODOT_EXECUTABLEまたはPATHにGodotの実行ファイルが見つかりません。"
        )


# {
#   責務: [_uses_godot: テストファイルのソースが実Godotの設定を参照するかを、ファイルごとに一度だけ判定します]
#   処理: [1: ソースにKADOKA_GODOT_EXECUTABLE・GODOT・godot_harnessのいずれかがあればGodotを使うと判定し、結果を記録します]
#   引数: [path: テストファイルのパス（Path）]
#   戻り値: [result: Godotを使うファイルならtrue（bool）]
# }
def _uses_godot(path: Path) -> bool:
    # テストごとにファイルを読み直さないよう、同じファイルの判定を共有します。
    if path not in _godot_files:
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            source = ""
        _godot_files[path] = any(word in source for word in ("KADOKA_GODOT_EXECUTABLE", "GODOT", "godot_harness"))
    return _godot_files[path]


# {
#   責務: [pytest_collection_modifyitems: 実Godotを参照するファイルのテストへgodotマーカーを付けます]
#   処理: [1: 収集した各テストのファイルを判定し、Godotを使うファイルのテストへマーカーを追加します]
#   引数: [
#     config: pytestの設定（pytest.Config）
#     items: 収集したテストの一覧（list[pytest.Item]）
#   ]
#   戻り値: [result: なし（None）]
# }
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if _uses_godot(Path(str(item.fspath))):
            item.add_marker(pytest.mark.godot)


# {
#   責務: [pytest_runtest_logreport: Godotが必須の実行で、Godotを理由にskipされたテストを記録します]
#   処理: [1: skipの理由にGodotが含まれる結果だけを、node IDと理由の組で記録します]
#   引数: [report: 一つのテスト段階の結果（pytest.TestReport）]
#   戻り値: [result: なし（None）]
# }
def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if not godot_required() or not report.skipped:
        return
    reason = str(report.longrepr)
    if "godot" in reason.lower():
        _godot_skips.append(f"{report.nodeid}: {reason}")


# {
#   責務: [pytest_sessionfinish: Godotが必須の実行でGodotを理由にしたskipがあれば、全体の結果を失敗にします]
#   処理: [1: 記録したskipを表示し、終了コードを失敗へ変えます]
#   引数: [
#     session: pytestの実行全体（pytest.Session）
#     exitstatus: pytestが決めた終了コード（int）
#   ]
#   戻り値: [result: なし（None）]
# }
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    # Godotの検査がskipだけで終わった実行を、Godotの検証に成功したとは扱いません。
    if _godot_skips:
        print(f"\n[ERROR] {REQUIRE_VARIABLE}=1ですが、Godotを理由に{len(_godot_skips)}件がskipされました。")
        for line in _godot_skips[:20]:
            print("  " + line)
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
