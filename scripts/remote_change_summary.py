"""Fetch and compactly summarize remote Git changes for one work cycle."""

from __future__ import annotations

import argparse
from collections import Counter
import os
from pathlib import Path
from shutil import which
import subprocess
import sys
from typing import Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def git_executable(*, environment: dict[str, str] | None = None) -> str:
    configured = (environment or os.environ).get("KADOKA_GIT_EXECUTABLE", "")
    if configured:
        return configured
    discovered = which("git")
    if discovered:
        return discovered
    raise RuntimeError("Gitが見つかりません。KADOKA_GIT_EXECUTABLE を設定してください。")


def run_git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        (git_executable(), *arguments),
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {detail}")
    return result.stdout.strip()


def changed_paths(name_status: str) -> list[str]:
    paths: list[str] = []
    for line in name_status.splitlines():
        columns = line.split("\t")
        if len(columns) < 2:
            continue
        paths.append(columns[-1])
    return paths


def area_for(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith(".github/"):
        return "GitHub / CI"
    if normalized.startswith("docs/"):
        return "ドキュメント"
    if normalized.startswith("tests/"):
        return "テスト"
    if normalized.startswith("scripts/"):
        return "スクリプト"
    if normalized.startswith("src/kadoka_engine/"):
        return "再利用エンジン"
    if normalized.startswith("src/kadoka_quest/apps/"):
        return "ゲームアプリ"
    if normalized.startswith("src/kadoka_quest/ui/"):
        return "UI / 入力"
    if normalized.startswith("src/kadoka_quest/data/"):
        return "データ層"
    if normalized.startswith("src/kadoka_quest/"):
        return "ゲームコア"
    if normalized.startswith("data/"):
        return "ゲームデータ"
    return "その他"


def dirty_paths(porcelain: str) -> set[str]:
    return {
        line[3:].replace("\\", "/")
        for line in porcelain.splitlines()
        if len(line) >= 4
    }


def render_summary(
    *,
    base: str,
    remote: str,
    merge_base: str,
    total_remote_commits: int,
    remote_commits: Iterable[str],
    paths: Iterable[str],
    dirty: Iterable[str],
) -> str:
    path_list = list(paths)
    dirty_set = {path.replace("\\", "/") for path in dirty}
    changed_set = {path.replace("\\", "/") for path in path_list}
    overlap = sorted(changed_set & dirty_set)
    areas = Counter(area_for(path) for path in path_list)
    commit_list = list(remote_commits)

    lines = [
        "# リモート変更要約",
        "",
        f"比較: `{base}` ← `{remote}`（共通祖先 `{merge_base}`）",
        f"リモートコミット: {total_remote_commits}件 / 変更ファイル: {len(path_list)}件",
        "",
        "## 変更領域",
    ]
    lines.extend(f"- {area}: {count}件" for area, count in sorted(areas.items()))
    lines.extend(("", f"## 最新コミット（表示 {len(commit_list)}件）"))
    lines.extend(f"- {commit}" for commit in commit_list)
    lines.extend(("", "## ローカル作業ツリー"))
    lines.append(f"- 未コミット変更: {len(dirty_set)}件")
    if overlap:
        lines.append("- 重複（マージ前に退避または確認）:")
        lines.extend(f"  - `{path}`" for path in overlap)
    else:
        lines.append("- リモート変更との同一ファイル重複: なし")
    return "\n".join(lines) + "\n"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", default="origin/main", help="比較対象のリモート参照")
    parser.add_argument("--base", default="HEAD", help="比較元のGit参照")
    parser.add_argument("--max-commits", type=int, default=12, help="表示するコミット数")
    parser.add_argument("--no-fetch", action="store_true", help="git fetch を実行しない")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if arguments.max_commits < 1:
        raise SystemExit("--max-commits は1以上にしてください。")
    if not arguments.no_fetch:
        remote_name = arguments.remote.split("/", 1)[0]
        run_git(REPOSITORY_ROOT, "fetch", remote_name, "--prune")

    merge_base = run_git(REPOSITORY_ROOT, "merge-base", arguments.base, arguments.remote)
    commits = run_git(
        REPOSITORY_ROOT,
        "log",
        f"--max-count={arguments.max_commits}",
        "--format=%h %s",
        f"{merge_base}..{arguments.remote}",
    ).splitlines()
    total_commits = int(
        run_git(REPOSITORY_ROOT, "rev-list", "--count", f"{merge_base}..{arguments.remote}")
    )
    paths = changed_paths(
        run_git(REPOSITORY_ROOT, "diff", "--name-status", f"{merge_base}..{arguments.remote}")
    )
    dirty = dirty_paths(run_git(REPOSITORY_ROOT, "status", "--porcelain"))
    print(
        render_summary(
            base=arguments.base,
            remote=arguments.remote,
            merge_base=merge_base[:12],
            total_remote_commits=total_commits,
            remote_commits=commits,
            paths=paths,
            dirty=dirty,
        ),
        end="",
    )


if __name__ == "__main__":
    main()
