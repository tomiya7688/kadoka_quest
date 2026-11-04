"""Windows CIのテスト起動と、公開の謎の正解を示すテスト定数の区別を検証します。"""
# {
#   責務: [test_ci_test_runner: 全テストを起動するCI設定と公開ゲーム用文字列の明確な命名を検証します]
#   フィールド: []
# }
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


# {
#   責務: [CITestConfigurationTests: WindowsのCIが全pytestを実行し、公開の謎を認証定数と混同しないことを確認します]
#   フィールド: []
# }
class CITestConfigurationTests(unittest.TestCase):
    # {
    #   責務: [test_windows_ci_installs_pytest_and_runs_complete_suite: WindowsのCIがpytestと整形の道具を導入し、テストを限定せず起動することを確認します]
    #   処理: [1: ワークフローを読み、pytestとtools/format/requirements.txtの導入と全体起動を確認して失敗無視と旧起動方式を拒否します]
    #   引数: [self: CI設定を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_windows_ci_installs_pytest_and_runs_complete_suite(self):
        # pytest形式のテストをunittestだけで取りこぼす回帰と、依存不足を防ぎます。
        workflow = (ROOT / ".github/workflows/windows-distribution.yml").read_text(encoding="utf-8")
        self.assertIn("python -m pip install pytest", workflow)
        # CIではtests/test_format_changed.pyが実際のRuffとgdformatを必須にするため、導入漏れで失敗しないことを確かめます。
        self.assertIn("-r tools/format/requirements.txt", workflow)
        self.assertRegex(workflow, r"(?m)^        run: python -m pytest[ \t]*$")
        self.assertNotIn("python -m unittest discover", workflow)
        self.assertNotIn("continue-on-error", workflow)

    # {
    #   責務: [test_public_puzzle_answer_remains_unchanged_and_explicitly_named: 公開のゲーム用合言葉の値を保持し、認証用PASSWORD定数から区別することを確認します]
    #   処理: [1: テストモジュールを実行せずASTから公開合言葉の定数名と値を確認します]
    #   引数: [self: 公開ゲーム用文字列の意味と値を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_public_puzzle_answer_remains_unchanged_and_explicitly_named(self):
        # 認証情報を隠したり暗号化したりする変更ではなく、公開の謎であることを名前に表します。
        tree = ast.parse((ROOT / "tests/test_gdscript_password.py").read_text(encoding="utf-8"))
        constants = {target.id: node.value.value for node in tree.body if isinstance(node, ast.Assign)
                     and isinstance(node.value, ast.Constant) for target in node.targets if isinstance(target, ast.Name)}
        self.assertEqual(constants["SPRING_PUZZLE_ANSWER"], "へいわなすみか")
        self.assertNotIn("PASSWORD", constants)
