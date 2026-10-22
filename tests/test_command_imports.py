# {
#   責務: [test_command_imports: test・コマンド・importsの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


# {
#   責務: [test_commands_import_in_fresh_process: 検証: commands import in fresh process]
#   処理: [1: 検証: commands import in fresh process]
#   引数: [module: module]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("module", [
    "kadoka_quest.apps.battle_command_app",
    "kadoka_quest.apps.field_command_app",
    "kadoka_quest.apps.manager_command_app",
    "kadoka_quest.apps.password_command_app",
    "kadoka_quest.application.runtime_orchestrator",
    "kadoka_quest.application",
])
def test_commands_import_in_fresh_process(module):
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    code = (
        f"import importlib; importlib.import_module({module!r}); "
        "from kadoka_quest.application import RuntimeOrchestrator; "
        "from kadoka_quest.application.runtime_orchestrator import RuntimeOrchestrator as Direct; "
        "assert RuntimeOrchestrator is Direct"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], env=environment,
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# {
#   責務: [test_unknown_application_export_raises_attribute_error: 検証: unknown application export raises attribute error]
#   処理: [1: 検証: unknown application export raises attribute error]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_unknown_application_export_raises_attribute_error():
    import kadoka_quest.application as application

    with pytest.raises(AttributeError, match="no attribute"):
        getattr(application, "missing_export")
