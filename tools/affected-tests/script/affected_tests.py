#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path


def git_changed(root: Path, base: str | None) -> list[str]:
    command = ["git", "-C", str(root), "diff", "--name-only"]
    if base:
        command.append(base)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def load_config(path: Path | None) -> dict:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def default_candidates(path: str) -> list[str]:
    normalized = path.replace("\\", "/")
    stem = Path(normalized).stem
    candidates: list[str] = []
    if normalized.startswith("src/"):
        relative = normalized[4:]
        candidates.extend((f"tests/{relative}", f"tests/test_{stem}.py"))
    if "/src/" in normalized:
        prefix, relative = normalized.split("/src/", 1)
        candidates.extend((f"{prefix}/tests/{relative}", f"{prefix}/tests/test_{stem}.py"))
    return candidates


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.replace("\\", "/")
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def analyze(root: Path, changed: list[str], config: dict) -> dict:
    mappings = config.get("mappings", [])
    broader_patterns = config.get(
        "broader_patterns",
        ["**/core/**", "**/shared/**", "**/schema.*", "**/api/**", "pyproject.toml"],
    )
    candidates: list[str] = []
    reasons: list[str] = []
    matched_explicit = False
    broader = False

    for path in changed:
        for mapping in mappings:
            if fnmatch.fnmatch(path, mapping.get("source", "")):
                matched_explicit = True
                candidates.extend(mapping.get("tests", []))
                if mapping.get("broader"):
                    broader = True
                    reasons.append(f"broader mapping: {path}")
        candidates.extend(default_candidates(path))
        if any(fnmatch.fnmatch(path, pattern) for pattern in broader_patterns):
            broader = True
            reasons.append(f"broad-impact pattern: {path}")

    candidates = unique(candidates)
    existing = [path for path in candidates if (root / path).is_file()]

    if not changed:
        confidence = "low"
        reasons.append("no changed files")
    elif broader:
        confidence = "medium"
    elif matched_explicit:
        confidence = "high"
    elif existing:
        confidence = "medium"
    else:
        confidence = "low"
        reasons.append("no existing mapped test candidate")

    fallback = "broader" if broader else ("subsystem-or-full" if confidence == "low" else "none")
    return {
        "changed_files": changed,
        "test_candidates": existing,
        "confidence": confidence,
        "fallback": fallback,
        "reasons": unique(reasons),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Select likely affected tests from changed files.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--base", help="git diff base, e.g. origin/main...HEAD")
    parser.add_argument("--changed", nargs="*", help="explicit changed files; bypass git")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    config_path = args.config or root / "tools" / "affected-tests" / "config.json"
    try:
        changed = (
            [item.replace("\\", "/") for item in args.changed]
            if args.changed is not None
            else git_changed(root, args.base)
        )
        result = analyze(root, changed, load_config(config_path if config_path.exists() else None))
    except Exception as exc:
        print(f"affected-tests: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"confidence: {result['confidence']}")
    print(f"fallback: {result['fallback']}")
    print("tests:")
    for path in result["test_candidates"]:
        print(f"- {path}")
    if result["reasons"]:
        print("reasons:")
        for reason in result["reasons"]:
            print(f"- {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
