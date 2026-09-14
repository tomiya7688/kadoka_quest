from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContextToolTests(unittest.TestCase):
    def test_affected_tests_routes_core_change(self) -> None:
        module = load_module(
            "affected_tests_tool",
            ROOT / "tools" / "affected-tests" / "script" / "affected_tests.py",
        )
        config = json.loads(
            (ROOT / "tools" / "affected-tests" / "config.json").read_text(encoding="utf-8")
        )
        result = module.analyze(ROOT, ["src/kadoka_quest/core/battle.py"], config)
        self.assertIn("tests/test_core.py", result["test_candidates"])
        self.assertEqual("broader", result["fallback"])

    def test_import_map_extracts_imports(self) -> None:
        module = load_module(
            "python_import_map_tool",
            ROOT / "tools" / "import-map" / "script" / "python_import_map.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("import os\nfrom . import local\nfrom pkg.mod import value\n", encoding="utf-8")
            self.assertEqual([".", "os", "pkg.mod"], module.imports(path))


if __name__ == "__main__":
    unittest.main()
