# {
#   責務: [test_environment_contract: test・environment・契約の公開機能・宣言を定義する]
#   フィールド: []
# }
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


# {
#   責務: [EnvironmentContractTests: environment・契約・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class EnvironmentContractTests(unittest.TestCase):
    # {
    #   責務: [test_python_3135_environment_is_ignored: 検証: python 3135 environment is ignored]
    #   処理: [1: 検証: python 3135 environment is ignored]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_python_3135_environment_is_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("venv_3135/", ignored)

    # {
    #   責務: [test_runner_prefers_3135_and_keeps_legacy_fallback: 検証: runner prefers 3135 and keeps legacy fallback]
    #   処理: [1: 検証: runner prefers 3135 and keeps legacy fallback]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_runner_prefers_3135_and_keeps_legacy_fallback(self) -> None:
        runner = (ROOT / "scripts" / "run_python.bat").read_text(encoding="utf-8")
        preferred = runner.index("venv_3135\\Scripts\\python.exe")
        fallback = runner.index(".venv\\Scripts\\python.exe")
        self.assertLess(preferred, fallback)

    # {
    #   責務: [test_supported_python_range_remains_portable: 検証: supported python range remains portable]
    #   処理: [1: 検証: supported python range remains portable]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_supported_python_range_remains_portable(self) -> None:
        project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('requires-python = ">=3.10"', project)


if __name__ == "__main__":
    unittest.main()
