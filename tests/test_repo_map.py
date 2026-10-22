# {
#   責務: [test_repo_map: test・repo・マップの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_repo_map", ROOT / "tools/code-docs/script/generate_repo_map.py"
)
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


# {
#   責務: [RepoMapTests: repo・マップ・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class RepoMapTests(unittest.TestCase):
    # {
    #   責務: [test_signatures_are_compact_and_source_is_never_executed: 検証: signatures are compact and source is never executed]
    #   処理: [1: 検証: signatures are compact and source is never executed]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_signatures_are_compact_and_source_is_never_executed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            (source / "example.py").write_text(
                'raise RuntimeError("must not execute")\n'
                'class Example(Base):\n'
                '    def __init__(self, value: int = expensive_call()): pass\n'
                '    async def run(self, a, /, *items: str, required, flag=True, **kw) -> bool:\n'
                '        """BODY_SECRET"""\n'
                '        def nested(): pass\n'
                '        return True\n'
                '    def _private(self): pass\n'
                'def entry(value: str = "DEFAULT_SECRET"): pass\n',
                encoding="utf-8",
            )
            result = tool.render_repo_map(source)
            self.assertIn("class Example(Base)", result)
            self.assertIn("__init__(self, value: int=...)", result)
            self.assertIn("async run(self, a, /, *items: str, required, flag=..., **kw) -> bool", result)
            for hidden in ("BODY_SECRET", "DEFAULT_SECRET", "expensive_call", "nested", "_private", "RuntimeError"):
                # 'nested' is mentioned in the fixed header, not in the symbol index.
                self.assertNotIn(hidden, result.split("```text", 1)[1])

    # {
    #   責務: [test_order_and_body_only_changes_do_not_affect_output: 検証: order and body only changes do not affect output]
    #   処理: [1: 検証: order and body only changes do not affect output]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_order_and_body_only_changes_do_not_affect_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            (source / "z.py").write_text("def zebra(): return 1\n", encoding="utf-8")
            (source / "a.py").write_text("def alpha(): pass\n", encoding="utf-8")
            before = tool.render_repo_map(source)
            (source / "z.py").write_text("\n\ndef zebra(): return 999\n", encoding="utf-8")
            self.assertEqual(before, tool.render_repo_map(source))
            self.assertLess(before.index("## a.py"), before.index("## z.py"))

    # {
    #   責務: [test_check_detects_drift_without_rewriting_and_errors_preserve_output: 検証: check detects drift without rewriting and errors preserve output]
    #   処理: [1: 検証: check detects drift without rewriting and errors preserve output]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_check_detects_drift_without_rewriting_and_errors_preserve_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "src"
            source.mkdir()
            output = Path(temporary) / "map.md"
            path = source / "example.py"
            path.write_text("def sample(): pass\n", encoding="utf-8")
            args = ["--source", str(source), "--output", str(output)]
            self.assertEqual(tool.main(args + ["--check"]), 1)
            self.assertFalse(output.exists())
            self.assertEqual(tool.main(args), 0)
            original = output.read_bytes()
            self.assertEqual(tool.main(args), 0)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(tool.main(args + ["--check"]), 0)
            path.write_text("def sample(new): pass\n", encoding="utf-8")
            self.assertEqual(tool.main(args + ["--check"]), 1)
            self.assertEqual(output.read_bytes(), original)
            path.write_text("def broken(\n", encoding="utf-8")
            self.assertEqual(tool.main(args), 1)
            self.assertEqual(output.read_bytes(), original)
