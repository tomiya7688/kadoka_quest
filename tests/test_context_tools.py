# {
#   責務: [test_context_tools: test・判断用コンテキスト・toolsの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


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
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# {
#   責務: [ContextToolTests: 判断用コンテキスト・tool・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class ContextToolTests(unittest.TestCase):
    # {
    #   責務: [test_affected_tests_routes_core_change: 検証: affected tests routes core change]
    #   処理: [1: 検証: affected tests routes core change]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [test_import_map_extracts_imports: 検証: import map extracts imports]
    #   処理: [1: 検証: import map extracts imports]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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
