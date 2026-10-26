# {
#   責務: [test_remote_context: test・remote・判断用コンテキストの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
from unittest.mock import patch
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "tools" / "remote-context" / "script" / "sync_remote_context.py"
SPEC = importlib.util.spec_from_file_location("remote_context", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
remote_context = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(remote_context)


# {
#   責務: [RemoteContextTests: remote・判断用コンテキスト・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class RemoteContextTests(unittest.TestCase):
    # {
    #   責務: [test_run_git_decodes_utf8_output_independent_of_windows_console_locale: 検証: run git decodes utf8 output independent of windows console locale]
    #   処理: [1: 検証: run git decodes utf8 output independent of windows console locale]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_run_git_decodes_utf8_output_independent_of_windows_console_locale(self) -> None:
        completed = subprocess.CompletedProcess(
            args=("git", "diff"), returncode=0, stdout="日本語の差分", stderr=""
        )
        with patch.object(remote_context, "git_executable", return_value="git.exe"), patch.object(
            remote_context.subprocess, "run", return_value=completed
        ) as run:
            result = remote_context.run_git("diff", "--stat")

        self.assertEqual("日本語の差分", result)
        self.assertEqual("utf-8", run.call_args.kwargs["encoding"])
        self.assertEqual("replace", run.call_args.kwargs["errors"])

    # {
    #   責務: [test_active_remote_branches_lists_recent_unmerged_work_only: 進行中ブランチ一覧が比較先・HEAD別名・古いブランチを除き、件数上限で止まることを確認します]
    #   処理: [
    #     1: for-each-refとrev-listの出力を固定値へ差し替えます
    #     2: 新しい未統合ブランチだけが独自コミット数付きで上限件数まで残ることを確認します
    #   ]
    #   引数: [self: リモート差分要約CLIの進行中ブランチ一覧を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_active_remote_branches_lists_recent_unmerged_work_only(self) -> None:
        now = 1_800_000_000
        day = 86400
        listing = "\n".join([
            f"origin/HEAD\t{now}\t2027-01-15\talias",
            f"origin/main\t{now}\t2027-01-15\tmain itself",
            f"origin/codex/unit-a\t{now - day}\t2027-01-14\tfeat: unit a",
            f"origin/claude/unit-b\t{now - 2 * day}\t2027-01-13\tfeat: unit b",
            f"origin/copilot/unit-c\t{now - 3 * day}\t2027-01-12\tfeat: unit c",
            f"origin/old/stale\t{now - 30 * day}\t2026-12-16\told work",
        ])
        calls: list[tuple[str, ...]] = []

        # 実Gitを呼ばず、一覧取得と独自コミット数の問い合わせだけを記録します。
        # {
        #   責務: [fake_git: 実Gitの代わりに、ブランチ一覧または固定の独自コミット数を返して呼出しを記録します]
        #   処理: [1: 引数をcallsへ記録し、for-each-refなら固定一覧、それ以外は独自コミット数3を返します]
        #   引数: [
        #     args: run_gitへ渡されたGitのサブコマンドとオプション（str）
        #     check: run_gitと同じ失敗時例外の指定。代役では使いません（bool）
        #   ]
        #   戻り値: [result: 固定のGit標準出力（str）]
        # }
        def fake_git(*args: str, check: bool = True) -> str:
            calls.append(args)
            return listing if args[0] == "for-each-ref" else "3"

        with patch.object(remote_context, "run_git", side_effect=fake_git):
            rows = remote_context.active_remote_branches("origin", "origin/main", 14, 2, now)

        self.assertEqual(
            [
                "origin/codex/unit-a | 2027-01-14 | ahead 3 | feat: unit a",
                "origin/claude/unit-b | 2027-01-13 | ahead 3 | feat: unit b",
            ],
            rows,
        )
        self.assertIn("--no-merged=origin/main", calls[0])
        self.assertEqual(
            [("rev-list", "--count", "origin/main..origin/codex/unit-a"),
             ("rev-list", "--count", "origin/main..origin/claude/unit-b")],
            calls[1:],
        )
        # 古いブランチは期間外で打ち切り、上限に達していなくても表示しません。
        with patch.object(remote_context, "run_git", side_effect=fake_git):
            rows = remote_context.active_remote_branches("origin", "origin/main", 14, 10, now)
        self.assertNotIn("old/stale", "\n".join(rows))
        self.assertEqual(3, len(rows))
