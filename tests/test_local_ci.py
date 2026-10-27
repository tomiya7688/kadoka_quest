"""ローカルCIがCIのワークフローと同じ検査を実行し、Godotが必須の実行でskipを成功扱いにしないことを検証します。"""
# {
#   責務: [test_local_ci: CIのワークフローとローカルCIの検査コマンドのずれ、Godot必須時のskip・未設定の失敗、godotマーカーの付与を検証します]
#   フィールド: [
#     ROOT: リポジトリ直下のパス（Path）
#     WORKFLOW: CIのPython quality workflowのパス（Path）
#     SETUP_PREFIXES: 検査ではなく環境準備のため、ローカルCIの対象外とするコマンドの先頭（tuple[str, ...]）
#   ]
# }
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/python-app.yml"
SETUP_PREFIXES = ("python -m pip", "python -m venv", ".package-venv/", "cd ", "archive=", "curl ", "echo ", "unzip ",
                  "executable=", "chmod ", '"$executable"', '"$GITHUB_WORKSPACE/', '"https://')
_spec = importlib.util.spec_from_file_location("run_local_ci", ROOT / "tools/local-ci/script/run_local_ci.py")
local_ci = importlib.util.module_from_spec(_spec)
# dataclassは定義中にsys.modulesから自分のモジュールを引くため、実行前に登録します。
sys.modules["run_local_ci"] = local_ci
_spec.loader.exec_module(local_ci)


# {
#   責務: [workflow_commands: CIのワークフローのrunに書かれたコマンドを、一行ずつ取り出します]
#   処理: [
#     1: run: |の後のより深い字下げの行と、run:に続く一行のコマンドを集めます
#     2: 前後の引用符と行継続の記号を除きます
#   ]
#   引数: [text: ワークフローのYAML本文（str）]
#   戻り値: [result: 出現順のコマンド一覧（list[str]）]
# }
def workflow_commands(text: str) -> list[str]:
    commands: list[str] = []
    block_indent: int | None = None
    for line in text.splitlines():
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        # 複数行のrunブロックは、run:より深い字下げが続く間だけを読みます。
        if block_indent is not None:
            if stripped and indent > block_indent:
                commands.append(stripped.rstrip("\\").strip())
                continue
            block_indent = None
        if stripped.startswith("run:") or stripped.startswith("- run:"):
            value = stripped.split("run:", 1)[1].strip()
            if value == "|":
                block_indent = indent
            elif value:
                commands.append(value.strip("'"))
    return commands


# {
#   責務: [test_every_ci_verification_command_runs_locally: CIのPython quality workflowの全検査コマンドが、ローカルCIの検査に含まれることを確認します]
#   処理: [
#     1: ワークフローから環境準備以外のコマンドを取り出します
#     2: 各コマンドがローカルCIの検査、パッケージ検査、またはGodot必須の全体pytestに含まれることを確認します
#   ]
#   引数: []
#   戻り値: [result: なし（None）]
# }
def test_every_ci_verification_command_runs_locally():
    verification = [command for command in workflow_commands(WORKFLOW.read_text(encoding="utf-8"))
                    if not command.startswith(SETUP_PREFIXES)]
    local = {step.command for step in local_ci.STEPS} | set(local_ci.PACKAGE_COMMANDS)
    # CIの-m godotはGodotのテストだけを選びます。ローカルのGodot必須の全体pytestはその全件を含みます。
    covered_by_full_pytest = {"python -m pytest -m godot"}
    assert "python -m pytest" in verification and "python -m pytest -m godot" in verification
    missing = [command for command in verification if command not in local | covered_by_full_pytest]
    assert missing == [], f"CIにだけある検査をtools/local-ci/script/run_local_ci.pyへ追加してください: {missing}"


# {
#   責務: [test_ci_pins_and_verifies_godot: CIのGodotジョブが版とSHA-512を固定し、Godotを必須にしていることを確認します]
#   処理: [1: ワークフロー本文に固定版・ハッシュ検証・Godot必須・godotマーカーの実行があることを確認します]
#   引数: []
#   戻り値: [result: なし（None）]
# }
def test_ci_pins_and_verifies_godot():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "GODOT_VERSION: 4.7.2-stable" in text
    assert "sha512sum --check --strict" in text
    assert 'KADOKA_REQUIRE_GODOT: "1"' in text
    assert "python -m pytest -m godot" in text


# {
#   責務: [run_pytest_on: tests/conftest.pyの複製と一つのテストファイルを一時フォルダへ置き、別プロセスのpytestで実行します]
#   処理: [1: conftestの複製と指定したテストを書き、指定した環境変数でpytestを起動して結果を返します]
#   引数: [
#     folder: 一時フォルダ（Path）
#     source: テストファイルの本文（str）
#     environment: 追加または上書きする環境変数。値がNoneなら削除します（dict[str, str | None]）
#     arguments: pytestへ追加で渡す引数（tuple[str, ...]）
#   ]
#   戻り値: [result: pytestの実行結果（subprocess.CompletedProcess）]
# }
def run_pytest_on(folder: Path, source: str, environment: dict[str, str | None], *arguments: str):
    shutil.copy(ROOT / "tests/conftest.py", folder / "conftest.py")
    (folder / "test_sample.py").write_text(source, encoding="utf-8")
    # WindowsのコンソールでもpytestとconftestのUTF-8の日本語を、そのまま読めるようにします。
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for key, value in environment.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", str(folder), *arguments],
                          cwd=folder, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=120, check=False)


SKIPPING_TEST = (
    "import pytest\n"
    "GODOT = None\n"
    "@pytest.mark.skipif(GODOT is None, reason='Set KADOKA_GODOT_EXECUTABLE for real probes')\n"
    "def test_needs_godot():\n"
    "    pass\n"
)


# {
#   責務: [test_godot_skip_fails_only_when_godot_is_required: Godotが必須の実行ではGodotを理由にしたskipを失敗にし、必須でない実行では従来どおりskipにすることを確認します]
#   処理: [
#     1: Godotを理由にskipするテストを、必須の設定と実在する実行ファイルの指定で実行し、失敗の終了コードを確認します
#     2: 同じテストを必須の設定なしで実行し、成功の終了コードを確認します
#   ]
#   引数: [tmp_path: 一時フォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
def test_godot_skip_fails_only_when_godot_is_required(tmp_path):
    # 実在するファイルなら起動前の確認を通るため、Godotの代わりにPythonの実行ファイルを指定します。
    required = run_pytest_on(tmp_path, SKIPPING_TEST,
                             {"KADOKA_REQUIRE_GODOT": "1", "KADOKA_GODOT_EXECUTABLE": sys.executable})
    assert required.returncode == pytest.ExitCode.TESTS_FAILED, required.stdout + required.stderr
    assert "Godotを理由に1件がskipされました" in required.stdout
    optional = run_pytest_on(tmp_path, SKIPPING_TEST, {"KADOKA_REQUIRE_GODOT": None})
    assert optional.returncode == pytest.ExitCode.OK, optional.stdout + optional.stderr


# {
#   責務: [test_missing_godot_stops_required_run_before_tests: Godotが必須なのに実行ファイルがない場合、テストを始める前に使用エラーで止まることを確認します]
#   処理: [1: 存在しない実行ファイルを指定して必須の設定で実行し、使用エラーの終了コードを確認します]
#   引数: [tmp_path: 一時フォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
def test_missing_godot_stops_required_run_before_tests(tmp_path):
    result = run_pytest_on(tmp_path, SKIPPING_TEST, {
        "KADOKA_REQUIRE_GODOT": "1", "KADOKA_GODOT_EXECUTABLE": str(tmp_path / "missing-godot"), "PATH": ""})
    assert result.returncode == pytest.ExitCode.USAGE_ERROR, result.stdout + result.stderr


# {
#   責務: [test_godot_marker_selects_only_godot_files: Godotの設定を参照するテストファイルだけに、-m godotで選べるマーカーが付くことを確認します]
#   処理: [1: Godotを参照するファイルと参照しないファイルを置き、-m godotで選ばれるテストを確認します]
#   引数: [tmp_path: 一時フォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
def test_godot_marker_selects_only_godot_files(tmp_path):
    (tmp_path / "test_plain.py").write_text("def test_plain():\n    pass\n", encoding="utf-8")
    result = run_pytest_on(tmp_path, "GODOT = 'godot'\ndef test_port():\n    pass\n", {"KADOKA_REQUIRE_GODOT": None},
                           "-m", "godot", "--collect-only")
    assert "test_port" in result.stdout and "test_plain" not in result.stdout, result.stdout


# {
#   責務: [test_local_ci_refuses_to_run_without_godot: ローカルCIがGodotなしでは検査を一つも実行せず、準備不足の終了コードを返すことを確認します]
#   処理: [1: Godotの指定とPATHを外してmainを呼び、終了コード2と案内を確認します]
#   引数: [
#     monkeypatch: 環境変数を一時的に変更するpytestの道具
#     capsys: 標準出力を取得するpytestの道具
#   ]
#   戻り値: [result: なし（None）]
# }
def test_local_ci_refuses_to_run_without_godot(monkeypatch, capsys):
    monkeypatch.delenv("KADOKA_GODOT_EXECUTABLE", raising=False)
    monkeypatch.setattr(local_ci.shutil, "which", lambda name: None)
    # Godotがないまま検査を始めると、Godotのテストがskipになったまま成功と表示されるおそれがあります。
    monkeypatch.setattr(local_ci, "run_step", lambda *args: pytest.fail("検査を実行してはいけません"))
    assert local_ci.main([]) == 2
    assert "KADOKA_GODOT_EXECUTABLE" in capsys.readouterr().out


# {
#   責務: [test_resolve_command_uses_current_python_and_godot: CIのコマンドを、実行中のPythonと指定したGodotで実行する引数へ変換することを確認します]
#   処理: [1: python・flake8・Godot参照を含むコマンドを変換し、引数の先頭と置換結果を確認します]
#   引数: []
#   戻り値: [result: なし（None）]
# }
def test_resolve_command_uses_current_python_and_godot():
    assert local_ci.resolve_command("python -m pytest", "godot")[:3] == [sys.executable, "-m", "pytest"]
    assert local_ci.resolve_command("flake8 . --count", "godot")[:3] == [sys.executable, "-m", "flake8"]
    godot = r"E:\tools\Godot 4\godot.exe"
    assert local_ci.resolve_command('"$KADOKA_GODOT_EXECUTABLE" --headless', godot) == [godot, "--headless"]
