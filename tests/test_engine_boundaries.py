from __future__ import annotations

import ast
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_engine.data_validator import DataValidator
from kadoka_quest.data.data_validator import DataValidator as LegacyDataValidator


class EngineBoundaryTests(unittest.TestCase):
    def test_engine_package_does_not_import_game_or_pygame(self) -> None:
        engine_root = PROJECT_ROOT / "src" / "kadoka_engine"
        imported_roots: set[str] = set()
        for path in engine_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".")[0])
        self.assertNotIn("kadoka_quest", imported_roots)
        self.assertNotIn("pygame", imported_roots)

    def test_engine_validator_requires_project_data_from_caller(self) -> None:
        validator = DataValidator(PROJECT_ROOT / "data")
        self.assertEqual(validator.root, PROJECT_ROOT / "data")
        self.assertEqual(validator.validate(), [])

    def test_legacy_game_import_keeps_default_data_root(self) -> None:
        self.assertEqual(LegacyDataValidator().validate(), [])


if __name__ == "__main__":
    unittest.main()
