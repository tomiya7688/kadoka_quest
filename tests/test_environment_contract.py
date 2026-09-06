from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EnvironmentContractTests(unittest.TestCase):
    def test_python_3135_environment_is_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("venv_3135/", ignored)

    def test_runner_prefers_3135_and_keeps_legacy_fallback(self) -> None:
        runner = (ROOT / "scripts" / "run_python.bat").read_text(encoding="utf-8")
        preferred = runner.index("venv_3135\\Scripts\\python.exe")
        fallback = runner.index(".venv\\Scripts\\python.exe")
        self.assertLess(preferred, fallback)

    def test_supported_python_range_remains_portable(self) -> None:
        project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('requires-python = ">=3.10"', project)


if __name__ == "__main__":
    unittest.main()
