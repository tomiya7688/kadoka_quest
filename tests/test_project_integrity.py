# {
#   責務: [test_project_integrity: 共有文書の必須パス・coreの依存境界・プレーンなコマンド・生成索引の鮮度を検証します]
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
#   責務: [load_module: 指定した開発用Pythonモジュールをファイル位置から読み、検証用に返します]
#   処理: [1: import仕様を作り、読込不能なら例外を返し、読込可能ならモジュールを実行します]
#   引数: [
#     name: 読み込む開発用モジュールへ割り当てる名前（str）
#     path: checkerまたは生成ツールのPythonファイル（Path）
#   ]
#   戻り値: [result: 読み込んだモジュール。読込仕様が作れなければRuntimeErrorです]
# }
def load_module(name: str, path: Path):
    # Playerの起動経路ではなく開発ツールだけを明示指定し、テストから検査APIを利用できるようにします。
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# {
#   責務: [ProjectIntegrityTests: 開発用checkerとクラス図生成器を保持し、文書・依存・コマンドの契約を確認します]
#   フィールド: [
#     checker: 必須パスとcore依存を検査する開発用モジュール
#     code_docs: Python ASTからクラス図本文を生成する開発用モジュール
#   ]
# }
class ProjectIntegrityTests(unittest.TestCase):
    # {
    #   責務: [setUpClass: 各整合性テストで使うcheckerとクラス図生成器を一度だけ読み込みます]
    #   処理: [1: リポジトリ内の二つの開発ツールをファイル位置から取得します]
    #   引数: [cls: 共通の検査ツール参照を保持するテストクラス]
    #   戻り値: [result: なし（None）。ゲームや保存データは初期化しません]
    # }
    @classmethod
    def setUpClass(cls) -> None:
        # 各ケースのたびにツールを読み直さず、同じ検査APIで正常系と拒否系を比較します。
        cls.checker = load_module(
            "project_integrity_checker",
            ROOT / "tools" / "project-integrity" / "script" / "check_project_rules.py",
        )
        cls.code_docs = load_module(
            "code_docs_generator",
            ROOT / "tools" / "code-docs" / "script" / "generate_class_diagram.py",
        )

    # {
    #   責務: [test_current_core_respects_dependency_boundary: 現在のcoreに画面・ファイルI/Oの禁止依存がないことを確認します]
    #   処理: [1: 実coreの静的検査で診断が空になるか照合します]
    #   引数: [self: 共通checkerを保持するテストケース]
    #   戻り値: [result: なし（None）。禁止依存があればassertionで失敗します]
    # }
    def test_current_core_respects_dependency_boundary(self) -> None:
        # coreを実行せず、構文木から層境界の違反がないことを確認します。
        self.assertEqual(self.checker.core_boundary_errors(), [])

    # {
    #   責務: [test_core_boundary_reports_forbidden_import_and_open: 禁止されたpygame依存とopenによるI/Oを検査器が検出することを確認します]
    #   処理: [1: 一時領域の不正ソースを静的検査し、依存とI/Oの二診断を照合します]
    #   引数: [self: 共通checkerを保持するテストケース]
    #   戻り値: [result: なし（None）。検出漏れや誤った診断数はassertionで失敗します]
    # }
    def test_core_boundary_reports_forbidden_import_and_open(self) -> None:
        # 不正コードは一時ファイルへ文字列として置くだけで、実行や正規coreの編集は行いません。
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
    #   責務: [test_command_payload_contract_accepts_only_plain_json_like_data: コマンドはJSON互換の通常データを受理し、Objectやtupleを拒否することを確認します]
    #   処理: [1: 正常なネスト辞書の受理と、非対応値を持つ要求のTypeErrorを照合します]
    #   引数: [self: コマンドの値境界を検査するテストケース]
    #   戻り値: [result: なし（None）。非プレーン値の受理はassertionで失敗します]
    # }
    def test_command_payload_contract_accepts_only_plain_json_like_data(self) -> None:
        # 層間要求へUIオブジェクトなどを混入させず、JSON互換の値だけを渡せることを確認します。
        payload = {"name": "slime", "level": 4, "flags": [True, None], "meta": {"ratio": 0.5}}
        self.assertTrue(is_plain_data(payload))
        command = AppCommand("field", "test", payload)
        self.assertEqual(command.payload, payload)

        with self.assertRaises(TypeError):
            AppCommand("field", "bad", {"value": object()})
        with self.assertRaises(TypeError):
            AppCommand("field", "bad", {"position": (1, 2)})

    # {
    #   責務: [test_tracked_application_diagram_is_current: 追跡するapplicationクラス図が現在のPython宣言と一致することを確認します]
    #   処理: [1: ASTから生成した本文と保存済みMermaid本文を比較します]
    #   引数: [self: クラス図生成器を保持するテストケース]
    #   戻り値: [result: なし（None）。保存済み索引が古ければassertionで失敗します]
    # }
    def test_tracked_application_diagram_is_current(self) -> None:
        # クラス図を自動更新して不一致を隠さず、読み取りだけで索引の鮮度を確認します。
        expected = self.code_docs.render_class_diagram(ROOT / "src" / "kadoka_quest" / "application")
        tracked = (ROOT / "docs" / "generated" / "application_class_diagram.mmd").read_text(encoding="utf-8")
        self.assertEqual(tracked, expected)

    # {
    #   責務: [test_shared_rule_documents_are_required_but_private_rules_are_optional: 共有規約四文書の欠落をcheckerが拒否し、ローカル専用規約を要求しないことを確認します]
    #   処理: [1: 必須パスだけの一時cloneを用意し、共有文書を一つずつ欠落させた診断を照合します]
    #   引数: [self: 必須パスcheckerを保持するテストケース]
    #   戻り値: [result: なし（None）。正本の検出漏れや任意規約の必須化はassertionで失敗します]
    # }
    def test_shared_rule_documents_are_required_but_private_rules_are_optional(self) -> None:
        # 正規リポジトリや実セーブを削除せず、一時領域の空ファイルだけで欠落検出を確認します。
        required = ("README.md", "コーディング規約.md", "CODING_RULES.md", "COMMENT_RULES.md")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in self.checker.REQUIRED_PATHS:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            self.assertEqual(self.checker.required_path_errors(root), [])
            for name in required:
                relative = f"docs/開発者向け/{name}"
                (root / relative).unlink()
                self.assertEqual(self.checker.required_path_errors(root), [f"missing required project path: {relative}"])
                (root / relative).touch()
            self.assertFalse((root / "docs/開発者向け/ローカル専用").exists())
            self.assertEqual(self.checker.required_path_errors(root), [])


if __name__ == "__main__":
    unittest.main()
