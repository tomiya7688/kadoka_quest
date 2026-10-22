"""Priority policy and real Windows batch selection with a private, non-network gh."""
# {
#   責務: [test_task_priority: Priority policy and real Windows batch selection with a private, non-network gh.]
#   フィールド: []
# }
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/task-workflow/script/start_task.bat"
PRIORITIES = [f"priority: p{index}" for index in range(5)]


# {
#   責務: [requests_through: test・task・priorityのrequests・throughを求める]
#   処理: [1: test・task・priorityのrequests・throughを求める]
#   引数: [index: 位置番号]
#   戻り値: [result: test・task・priorityのrequests・throughを求めるための結果（型注釈なし）]
# }
def requests_through(index):
    return [entry for offset, label in enumerate(PRIORITIES) if offset <= index
            for entry in ([label + "+gdscript", label] if offset == 1 else [label])]


# {
#   責務: [PriorityPolicyTests: priority・policy・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class PriorityPolicyTests(unittest.TestCase):
    # {
    #   責務: [test_batch_checks_all_five_priorities_in_order: 検証: batch checks all five priorities in order]
    #   処理: [1: 検証: batch checks all five priorities in order]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_batch_checks_all_five_priorities_in_order(self):
        source = SCRIPT.read_text(encoding="utf-8")
        positions = [source.index(f'"{label}"') for label in PRIORITIES]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('sort:created-asc', source)
        for legacy in ("critical", "high", "medium", "low"):
            self.assertNotIn(f"priority: {legacy}", source)

    # {
    #   責務: [test_policy_is_linked_and_reserves_p0_for_emergencies: 検証: policy is linked and reserves p0 for emergencies]
    #   処理: [1: 検証: policy is linked and reserves p0 for emergencies]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_policy_is_linked_and_reserves_p0_for_emergencies(self):
        policy = ROOT / "docs/ワークフロー/Issue優先度方針.md"
        content = policy.read_text(encoding="utf-8")
        for label in ("P0", "P1", "P2", "P3", "P4"):
            self.assertIn(f"| {label} |", content)
        self.assertIn("緊急対応専用", content)
        self.assertIn("新規Issueの既定値", content)
        self.assertIn("将来・長期保留", content)
        for relative in ("AGENTS.md", "docs/ワークフロー/ワークフロー.md", "docs/context/WORKFLOW.md", "tools/README.md"):
            self.assertIn("Issue優先度方針.md", (ROOT / relative).read_text(encoding="utf-8"))


# {
#   責務: [WindowsPrioritySelectionTests: windows・priority・選択状態・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
@unittest.skipUnless(os.name == "nt", "Real cmd.exe batch selection is Windows-specific")
class WindowsPrioritySelectionTests(unittest.TestCase):
    # {
    #   責務: [run_batch: batchを実行する]
    #   処理: [1: batchを実行する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     available: available
    #     migration: migration
    #     auth_status: auth・状態異常
    #     view_status: 表示・状態異常
    #   ]
    #   戻り値: [result: batchを実行するための結果（型注釈なし）]
    # }
    def run_batch(self, available, *, migration=(), auth_status=0, view_status=0):
        with tempfile.TemporaryDirectory(prefix="kadoka-priority-") as directory:
            private = Path(directory)
            trace = private / "requests.txt"
            stub = ["@echo off", 'if "%1 %2"=="auth status" exit /b ' + str(auth_status),
                    'if "%1 %2"=="issue view" (', '  echo VIEW:%~3', f"  exit /b {view_status}", ")",
                    'if not "%1 %2"=="issue list" exit /b 9', 'if "%~8"=="gdscript" (',
                    '  echo %~6+gdscript>>"%KADOKA_TEST_PRIORITY_TRACE%"']
            stub.extend(f"  echo {number}" for number in migration)
            stub.extend(["  exit /b 0", ")", 'echo %~6>>"%KADOKA_TEST_PRIORITY_TRACE%"'])
            for label, numbers in available.items():
                stub.append(f'if "%~6"=="{label}" (')
                stub.extend(f"  echo {number}" for number in numbers)
                stub.append(")")
            stub.append("exit /b 0")
            # Only private test fixtures are written; the real gh is shadowed in this child's PATH.
            (private / "gh.cmd").write_text("\r\n".join(stub) + "\r\n", encoding="ascii")
            environment = dict(os.environ, PATH=str(private) + os.pathsep + os.environ.get("PATH", ""),
                               KADOKA_TEST_PRIORITY_TRACE=str(trace))
            result = subprocess.run([os.environ["COMSPEC"], "/d", "/c", str(SCRIPT)], cwd=private,
                                    env=environment, capture_output=True, text=True, timeout=20)
            requests = trace.read_text(encoding="ascii").splitlines() if trace.exists() else []
            return result, requests

    # {
    #   責務: [test_each_priority_wins_before_lower_priorities: 検証: each priority wins before lower priorities]
    #   処理: [1: 検証: each priority wins before lower priorities]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_each_priority_wins_before_lower_priorities(self):
        for index, label in enumerate(PRIORITIES):
            with self.subTest(label=label):
                available = {entry: [900 - offset] for offset, entry in enumerate(PRIORITIES) if offset >= index}
                result, requests = self.run_batch(available)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"Priority: {label}", result.stdout)
                self.assertIn(f"VIEW:{900 - index}", result.stdout)
                self.assertEqual(requests, requests_through(index))

    # {
    #   責務: [test_no_prioritized_issue_returns_two: 検証: no prioritized issue returns two]
    #   処理: [1: 検証: no prioritized issue returns two]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_no_prioritized_issue_returns_two(self):
        result, requests = self.run_batch({})
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(requests, requests_through(4))
        self.assertNotIn("VIEW:", result.stdout)

    # {
    #   責務: [test_auth_failure_stops_before_issue_queries: 検証: auth failure stops before issue queries]
    #   処理: [1: 検証: auth failure stops before issue queries]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_auth_failure_stops_before_issue_queries(self):
        result, requests = self.run_batch({PRIORITIES[0]: [1]}, auth_status=1)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(requests, [])
        self.assertNotIn("VIEW:", result.stdout)

    # {
    #   責務: [test_view_failure_preserves_cli_exit_status: 検証: view failure preserves cli exit status]
    #   処理: [1: 検証: view failure preserves cli exit status]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_view_failure_preserves_cli_exit_status(self):
        result, requests = self.run_batch({PRIORITIES[1]: [42]}, view_status=5)
        self.assertEqual(result.returncode, 5, result.stdout + result.stderr)
        self.assertEqual(requests, requests_through(1))

    # {
    #   責務: [test_only_first_number_from_sorted_result_is_selected: 検証: only first number from sorted result is selected]
    #   処理: [1: 検証: only first number from sorted result is selected]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_only_first_number_from_sorted_result_is_selected(self):
        result, requests = self.run_batch({PRIORITIES[2]: [91, 42]})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VIEW:91", result.stdout)
        self.assertNotIn("VIEW:42", result.stdout)
        self.assertEqual(requests, requests_through(2))

    # {
    #   責務: [test_gdscript_p1_is_preferred_over_older_general_p1: 検証: gdscript p1 is preferred over older general p1]
    #   処理: [1: 検証: gdscript p1 is preferred over older general p1]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_gdscript_p1_is_preferred_over_older_general_p1(self):
        result, requests = self.run_batch({PRIORITIES[1]: [22]}, migration=[218])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VIEW:218", result.stdout)
        self.assertNotIn("VIEW:22", result.stdout)
        self.assertEqual(requests, [PRIORITIES[0], PRIORITIES[1] + "+gdscript"])

    # {
    #   責務: [test_emergency_p0_still_precedes_gdscript_p1: 検証: emergency p0 still precedes gdscript p1]
    #   処理: [1: 検証: emergency p0 still precedes gdscript p1]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_emergency_p0_still_precedes_gdscript_p1(self):
        result, requests = self.run_batch({PRIORITIES[0]: [999], PRIORITIES[1]: [22]}, migration=[218])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VIEW:999", result.stdout)
        self.assertEqual(requests, [PRIORITIES[0]])


if __name__ == "__main__":
    unittest.main()
