# {
#   責務: [test_project_integrity: test・project・integrityの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from kadoka_quest.application.app_command import AppCommand, is_plain_data


ROOT = Path(__file__).resolve().parents[1]


# {
#   責務: [load_module: moduleを読み込む]
#   処理: [1: moduleを読み込む]
#   引数: [
#     name: 名前（str）
#     path: パス（Path）
#   ]
#   戻り値: [result: module（型注釈なし）]
# }
def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# {
#   責務: [ProjectIntegrityTests: project・integrity・testsの状態と振る舞いを担当する]
#   フィールド: [
#     checker: checker
#     code_docs: code・docs
#   ]
# }
class ProjectIntegrityTests(unittest.TestCase):
    # {
    #   責務: [setUpClass: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [cls: 対象クラス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @classmethod
    def setUpClass(cls) -> None:
        cls.checker = load_module(
            "project_integrity_checker",
            ROOT / "tools" / "project-integrity" / "script" / "check_project_rules.py",
        )
        cls.code_docs = load_module(
            "code_docs_generator",
            ROOT / "tools" / "code-docs" / "script" / "generate_class_diagram.py",
        )

    # {
    #   責務: [test_current_core_respects_dependency_boundary: 検証: current core respects dependency boundary]
    #   処理: [1: 検証: current core respects dependency boundary]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_current_core_respects_dependency_boundary(self) -> None:
        self.assertEqual(self.checker.core_boundary_errors(), [])

    # {
    #   責務: [test_core_boundary_reports_forbidden_import_and_open: 検証: core boundary reports forbidden import and open]
    #   処理: [1: 検証: core boundary reports forbidden import and open]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_core_boundary_reports_forbidden_import_and_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.py").write_text(
                "import pygame\n\ndef load():\n    return open('x.txt')\n",
                encoding="utf-8",
            )
            errors = self.checker.core_boundary_errors(root)

        self.assertEqual(len(errors), 2)
        self.assertTrue(any("core must not import pygame" in error for error in errors))
        self.assertTrue(any("core must not perform file I/O" in error for error in errors))

    # {
    #   責務: [test_command_payload_contract_accepts_only_plain_json_like_data: 検証: command payload contract accepts only plain json like data]
    #   処理: [1: 検証: command payload contract accepts only plain json like data]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_command_payload_contract_accepts_only_plain_json_like_data(self) -> None:
        payload = {"name": "slime", "level": 4, "flags": [True, None], "meta": {"ratio": 0.5}}
        self.assertTrue(is_plain_data(payload))
        command = AppCommand("field", "test", payload)
        self.assertEqual(command.payload, payload)

        with self.assertRaises(TypeError):
            AppCommand("field", "bad", {"value": object()})
        with self.assertRaises(TypeError):
            AppCommand("field", "bad", {"position": (1, 2)})

    # {
    #   責務: [test_tracked_application_diagram_is_current: 検証: tracked application diagram is current]
    #   処理: [1: 検証: tracked application diagram is current]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_tracked_application_diagram_is_current(self) -> None:
        expected = self.code_docs.render_class_diagram(ROOT / "src" / "kadoka_quest" / "application")
        tracked = (ROOT / "docs" / "generated" / "application_class_diagram.mmd").read_text(encoding="utf-8")
        self.assertEqual(tracked, expected)


if __name__ == "__main__":
    unittest.main()
