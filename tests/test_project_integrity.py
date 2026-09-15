from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from kadoka_quest.application.app_command import AppCommand, is_plain_data


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProjectIntegrityTests(unittest.TestCase):
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

    def test_current_core_respects_dependency_boundary(self) -> None:
        self.assertEqual(self.checker.core_boundary_errors(), [])

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

    def test_command_payload_contract_accepts_only_plain_json_like_data(self) -> None:
        payload = {"name": "slime", "level": 4, "flags": [True, None], "meta": {"ratio": 0.5}}
        self.assertTrue(is_plain_data(payload))
        command = AppCommand("field", "test", payload)
        self.assertEqual(command.payload, payload)

        with self.assertRaises(TypeError):
            AppCommand("field", "bad", {"value": object()})
        with self.assertRaises(TypeError):
            AppCommand("field", "bad", {"position": (1, 2)})

    def test_tracked_application_diagram_is_current(self) -> None:
        expected = self.code_docs.render_class_diagram(ROOT / "src" / "kadoka_quest" / "application")
        tracked = (ROOT / "docs" / "generated" / "application_class_diagram.mmd").read_text(encoding="utf-8")
        self.assertEqual(tracked, expected)


if __name__ == "__main__":
    unittest.main()
