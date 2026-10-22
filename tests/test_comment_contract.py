# {
#   責務: [test_comment_contract: test・comment・契約の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "comment-check" / "script" / "check_comments.py"


# {
#   責務: [load_checker: checkerを読み込む]
#   処理: [1: checkerを読み込む]
#   引数: []
#   戻り値: [result: module（型注釈なし）]
# }
def load_checker():
    spec = importlib.util.spec_from_file_location("kadoka_comment_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# {
#   責務: [function_block: test・comment・契約のfunction・ブロックを求める]
#   処理: [1: test・comment・契約のfunction・ブロックを求める]
#   引数: [
#     name: 名前
#     args: args
#     prefix: prefix
#     indent: indent
#   ]
#   戻り値: [result: test・comment・契約のfunction・ブロックを求めるための結果（型注釈なし）]
# }
def function_block(name="call", args=("value",), prefix="#", indent=""):
    lines = ["{", f"  責務: [{name}: 契約を検証する]", "  処理: [1: 入力に対応する結果を返す]", "  引数: ["]
    lines.extend(f"    {arg}: 入力" for arg in args)
    lines.extend(["  ]", "  戻り値: [result: 処理結果]", "}"])
    return "\n".join(indent + prefix + " " + line for line in lines) + "\n"


# {
#   責務: [module_block: test・comment・契約のmodule・ブロックを求める]
#   処理: [1: test・comment・契約のmodule・ブロックを求める]
#   引数: [name: 名前]
#   戻り値: [result: test・comment・契約のmodule・ブロックを求めるための結果（型注釈なし）]
# }
def module_block(name="fixture"):
    return f"# {{\n#   責務: [{name}: 検証fixtureを定義する]\n#   フィールド: []\n# }}\n"


# {
#   責務: [CommentContractTests: comment・契約・testsの状態と振る舞いを担当する]
#   フィールド: [checker: checker]
# }
class CommentContractTests(unittest.TestCase):
    # {
    #   責務: [setUpClass: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [cls: 対象クラス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @classmethod
    def setUpClass(cls):
        cls.checker = load_checker()

    # {
    #   責務: [source_errors: comment・契約・testsの元データ・errorsを求める]
    #   処理: [1: comment・契約・testsの元データ・errorsを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     text: 文字列
    #     suffix: suffix
    #     name: 名前
    #   ]
    #   戻り値: [result: comment・契約・testsの元データ・errorsを求めるための結果（型注釈なし）]
    # }
    def source_errors(self, text, suffix=".py", name="fixture"):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / (name + suffix)
            path.write_text(text, encoding="utf-8")
            return self.checker.check_source(path)

    # {
    #   責務: [test_python_private_nested_and_decorated_parameters: 検証: python private nested and decorated parameters]
    #   処理: [1: 検証: python private nested and decorated parameters]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_python_private_nested_and_decorated_parameters(self):
        source = module_block() + function_block("_call", ("value", "extra", "named", "rest"))
        source += "@decorator\ndef _call(value, /, *extra, named=1, **rest):\n"
        source += function_block("nested", ("item",), indent="    ")
        source += "    def nested(item):\n        return item\n    return nested(value)\n"
        count, errors = self.source_errors(source)
        self.assertEqual(count, 2)
        self.assertEqual(errors, [])

    # {
    #   責務: [test_class_requires_fields_and_name: 検証: class requires fields and name]
    #   処理: [1: 検証: class requires fields and name]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_class_requires_fields_and_name(self):
        text = module_block() + "# {\n#   責務: [Wrong: 説明]\n# }\nclass Owner:\n    pass\n"
        count, errors = self.source_errors(text)
        self.assertEqual(count, 1)
        self.assertTrue(any("fields" in error for error in errors))
        self.assertTrue(any("Owner" in error for error in errors))

    # {
    #   責務: [test_missing_comments_and_parameter_drift_are_failures: 検証: missing comments and parameter drift are failures]
    #   処理: [1: 検証: missing comments and parameter drift are failures]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_missing_comments_and_parameter_drift_are_failures(self):
        for source, expected in (
            (module_block() + "def call(value):\n    return value\n", "missing JSON-like"),
            (module_block() + function_block() + "def call(changed):\n    return changed\n", "parameter mismatch"),
        ):
            with self.subTest(expected=expected):
                _, errors = self.source_errors(source)
                self.assertTrue(any(expected in error for error in errors))

    # {
    #   責務: [test_semantic_aliases_are_case_insensitive_and_duplicates_fail: Semantic Keyの別名と重複を検証する]
    #   処理: [1: 検証: semantic aliases are case insensitive and duplicates fail]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_semantic_aliases_are_case_insensitive_and_duplicates_fail(self):
        text = function_block().replace("責務", "RESPONSIBILITY").replace("処理", "Action")
        text = text.replace("引数", "Parameters").replace("戻り値", "Return")
        _, errors = self.source_errors(module_block() + text + "def call(value):\n    return value\n")
        self.assertEqual(errors, [])
        text = text.replace("#   Action", "#   責務: [call: 重複]\n#   Action")
        _, errors = self.source_errors(module_block() + text + "def call(value):\n    return value\n")
        self.assertTrue(any("duplicate semantic key" in error for error in errors))

    # {
    #   責務: [test_blank_action_and_return_and_nonconsecutive_steps_fail: 空欄・処理番号の不整合を検証する]
    #   処理: [1: 検証: blank action and return and nonconsecutive steps fail]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_blank_action_and_return_and_nonconsecutive_steps_fail(self):
        for old, new, expected in (
            ("処理: [1: 入力に対応する結果を返す]", "処理: []", "numbered from 1"),
            ("処理: [1: 入力に対応する結果を返す]", "処理: [2: 入力に対応する結果を返す]", "numbered from 1"),
            ("戻り値: [result: 処理結果]", "戻り値: []", "return must describe"),
            ("value: 入力", "value:", "blank/malformed"),
        ):
            with self.subTest(expected=expected):
                source = module_block() + function_block().replace(old, new) + "def call(value):\n    return value\n"
                _, errors = self.source_errors(source)
                self.assertTrue(any(expected in error for error in errors))

    # {
    #   責務: [test_unknown_keys_are_preserved_not_guessed_and_ordinary_comments_allowed: 未知キーと通常コメントの許容を検証する]
    #   処理: [1: 検証: unknown keys are preserved not guessed and ordinary comments allowed]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_unknown_keys_are_preserved_not_guessed_and_ordinary_comments_allowed(self):
        text = function_block().replace("# }", "#   Cache: [ttl: キャッシュ期限]\n# }")
        text = module_block() + text + "# 呼出前の通常コメント\ndef call(value):\n    # 実装内部の補足\n    return value\n"
        # Ordinary notes are not structured entries and must not break association.
        _, errors = self.source_errors(text)
        self.assertEqual(errors, [])
        _, errors = self.source_errors(text.replace("# 呼出前の通常コメント\n", ""))
        self.assertEqual(errors, [])

    # {
    #   責務: [test_gdscript_nested_class_static_functions_and_comma_defaults: ネストclass・static・複合既定値を検証する]
    #   処理: [1: 検証: gdscript nested class static functions and comma defaults]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_gdscript_nested_class_static_functions_and_comma_defaults(self):
        source = module_block() + "extends RefCounted\n"
        source += "# {\n#   責務: [Owner: 専用状態]\n#   フィールド: []\n# }\nclass Owner:\n"
        source += function_block("call", ("value", "options", "label"), indent="\t")
        source += ('\tstatic func call(value: int, options: Dictionary = {"a": [1, 2]}, '
                   'label: String = "a,b") -> int:\n\t\treturn value\n')
        count, errors = self.source_errors(source, ".gd")
        self.assertEqual(count, 2)
        self.assertEqual(errors, [])

    # {
    #   責務: [test_batch_script_and_subroutine_comments: 検証: batch script and subroutine comments]
    #   処理: [1: 検証: batch script and subroutine comments]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_batch_script_and_subroutine_comments(self):
        source = "@echo off\n" + function_block("fixture", ("argv",), prefix="rem")
        source += "exit /b 0\n" + function_block("find_issue", ("1", "2"), prefix="rem")
        source += ':find_issue\nset "priority=%~1"\nset "classification=%~2"\nexit /b 0\n'
        count, errors = self.source_errors(source, ".bat")
        self.assertEqual(count, 1)
        self.assertEqual(errors, [])

    # {
    #   責務: [test_syntax_and_read_errors_are_not_success: 検証: syntax and read errors are not success]
    #   処理: [1: 検証: syntax and read errors are not success]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_syntax_and_read_errors_are_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.py"
            path.write_text("def broken(\n", encoding="utf-8")
            _, errors = self.checker.check([path, path.with_name("missing.py")])
            self.assertEqual(len(errors), 2)
            self.assertTrue(all("cannot inspect source" in error for error in errors))

    # {
    #   責務: [test_every_tracked_source_has_matching_comments: 検証: every tracked source has matching comments]
    #   処理: [1: 検証: every tracked source has matching comments]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_every_tracked_source_has_matching_comments(self):
        paths = self.checker.tracked_sources(ROOT)
        count, errors = self.checker.check(paths)
        self.assertGreater(count, 2400)
        self.assertGreater(len(paths), 295)
        self.assertEqual(errors, [])

    # {
    #   責務: [test_existing_python_ast_and_gdscript_code_are_unchanged: fixtureへの注釈が宣言/ASTを変えないことを確認する]
    #   処理: [1: 同じfixtureの注釈前後で実行ASTと宣言を比較する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_existing_python_ast_and_gdscript_code_are_unchanged(self):
        """Check comment-insertion neutrality on fixtures, not every game revision."""
        # Commit-independent canonical comparison belongs to migration validation;
        # this fixture guards the mechanism, not a permanently pinned game revision.
        original = "from __future__ import annotations\n\ndef call(value):\n    return value + 1\n"
        annotated = module_block() + original.replace("def call", function_block() + "def call")
        self.assertEqual(ast.dump(ast.parse(original)), ast.dump(ast.parse(annotated)))
        before = self.checker.gdscript_declarations("func call(value):\n\treturn value\n")
        after = self.checker.gdscript_declarations(function_block() + "func call(value):\n\treturn value\n")
        self.assertEqual([entry[1:] for entry in before], [entry[1:] for entry in after])

    # {
    #   責務: [test_multiline_gdscript_and_typed_array_signatures: 複数行と型付き配列の宣言も網羅する]
    #   処理: [1: コレクション既定値を含む2行シグネチャの入力名を照合する]
    #   引数: [self: 検証fixture]
    #   戻り値: [result: なし（None）。不一致はassertionで失敗する]
    # }
    def test_multiline_gdscript_and_typed_array_signatures(self):
        source = module_block() + "extends RefCounted\n" + function_block("call", ("value", "options"))
        source += 'static func call(\n\tvalue: int, options: Array[int] = [1, 2],\n) -> Array[int]:\n\treturn [value]\n'
        count, errors = self.source_errors(source, ".gd")
        self.assertEqual(count, 1)
        self.assertEqual(errors, [])

    # {
    #   責務: [test_unterminated_gdscript_is_not_silently_skipped: 未対応/破損した宣言を成功扱いしない]
    #   処理: [1: 閉じていない宣言の静的解析が拒否されることを確認する]
    #   引数: [self: 検証fixture]
    #   戻り値: [result: なし（None）。例外がなければ検証失敗]
    # }
    def test_unterminated_gdscript_is_not_silently_skipped(self):
        with self.assertRaisesRegex(ValueError, "unsupported GDScript"):
            self.checker.gdscript_declarations("func broken(\n")

    # {
    #   責務: [test_ci_header_must_precede_workflow_content: CIの説明ヘッダー位置を守る]
    #   処理: [1: 内容前のヘッダーを許可し、内容後のヘッダーを拒否する]
    #   引数: [self: 検証fixture]
    #   戻り値: [result: なし（None）。検査結果をassertionで確認する]
    # }
    def test_ci_header_must_precede_workflow_content(self):
        header = module_block()
        _, errors = self.source_errors(header + "name: test\n", ".yml")
        self.assertEqual(errors, [])
        _, errors = self.source_errors("name: test\n" + header, ".yml")
        self.assertTrue(any("precede executable" in error for error in errors))

    # {
    #   責務: [test_goto_error_label_has_no_positional_parameters: goto専用エラーラベルを引数なしで扱う]
    #   処理: [1: call用の2引数をエラーラベルへ捏造しないことを確認する]
    #   引数: [self: 検証fixture]
    #   戻り値: [result: なし（None）。不一致はassertionで失敗する]
    # }
    def test_goto_error_label_has_no_positional_parameters(self):
        source = "@echo off\n" + function_block("fixture", ("argv",), prefix="rem")
        source += "goto :failed\n" + function_block("failed", (), prefix="rem")
        source += ":failed\necho failure\nexit /b 1\n"
        count, errors = self.source_errors(source, ".bat")
        self.assertEqual(count, 1)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
