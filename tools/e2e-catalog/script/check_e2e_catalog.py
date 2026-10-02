"""Validate expectation rows and source E2E references without importing games."""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[3]
HEADER = ("ID", "機能/画面", "Given", "When", "Then", "Persistence", "E2E", "Status", "理由/次の担当")
STATUSES = ("covered", "missing", "intentionally-not-e2e")
ID_PATTERN = re.compile(r"KQ-[PDX][0-9]{2}")


def catalog_rows(text: str) -> tuple[list[dict[str, str]], list[str]]:
    rows, errors = [], []
    active = False
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip().startswith("|"):
            active = False
            continue
        cells = [cell.strip() for cell in line.strip().split("|")[1:-1]]
        if tuple(cells) == HEADER:
            active = True
            continue
        if not active or all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        if len(cells) != len(HEADER):
            errors.append(f"line {line_number}: expected {len(HEADER)} columns")
            continue
        rows.append(dict(zip(HEADER, cells)))
    if not rows:
        errors.append("catalog has no expectation rows")
    return rows, errors


def _defined_test(path: Path, names: list[str]) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    body = tree.body
    if len(names) == 2:
        classes = [node for node in body if isinstance(node, ast.ClassDef) and node.name == names[0]]
        if not names[0].startswith("Test") or not classes:
            return False
        body = classes[0].body
    return names[-1].startswith("test_") and any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == names[-1]
        for node in body
    )


def test_reference_error(root: Path, reference: str) -> str | None:
    parts = reference.strip().strip("`").split("::")
    if len(parts) not in (2, 3):
        return "expected file::test or file::TestClass::test"
    relative = Path(parts[0])
    if relative.is_absolute() or ".." in relative.parts:
        return "reference must stay inside tests/e2e"
    directory = (root / "tests" / "e2e").resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(directory) or path.suffix != ".py":
        return "reference must be a Python test inside tests/e2e"
    if not path.is_file():
        return "test file is missing"
    try:
        if not _defined_test(path, parts[1:]):
            return "test definition is missing"
    except (OSError, SyntaxError, UnicodeError) as exc:
        return f"test cannot be parsed: {type(exc).__name__}"
    return None


def check_catalog(root: Path, catalog: Path) -> dict:
    rows, errors = catalog_rows(catalog.read_text(encoding="utf-8-sig"))
    counts = dict.fromkeys(STATUSES, 0)
    missing, seen = [], set()
    for row in rows:
        scenario = row["ID"]
        if not ID_PATTERN.fullmatch(scenario) or scenario in seen:
            errors.append(f"{scenario}: invalid or duplicate scenario ID")
        seen.add(scenario)
        for field in ("機能/画面", "Given", "When", "Then", "理由/次の担当"):
            if row[field] in ("", "-"):
                errors.append(f"{scenario}: {field} is required")
        if row["Persistence"] not in ("yes", "no"):
            errors.append(f"{scenario}: Persistence must be yes/no")
        status = row["Status"]
        if status not in STATUSES:
            errors.append(f"{scenario}: unknown status {status}")
            continue
        if status == "covered":
            references = row["E2E"].split("<br>")
            failures = [f"{ref}: {error}" for ref in references
                        if (error := test_reference_error(root, ref))]
            if failures:
                errors.extend(f"{scenario}: {failure}" for failure in failures)
                status = "missing"
        elif row["E2E"] != "-":
            errors.append(f"{scenario}: non-covered rows must use E2E=-")
        counts[status] += 1
        if status == "missing":
            missing.append(f"{scenario}: {row['機能/画面']} ({row['理由/次の担当']})")
    return {"counts": counts, "missing": missing, "errors": errors}


def main(argv: list[str] | None = None) -> int:
    if not sys.stdout.isatty() and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--catalog", type=Path, default=Path("docs/testing/E2E_EXPECTATIONS.md"))
    parser.add_argument("--missing", action="store_true", help="list unresolved scenario IDs")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        result = check_catalog(root, root / args.catalog)
    except (OSError, UnicodeError) as exc:
        print(f"[ERROR] catalog cannot be read: {type(exc).__name__}")
        return 1
    print("coverage: " + ", ".join(f"{status}={count}" for status, count in result["counts"].items()))
    if args.missing:
        for row in result["missing"]:
            print(row)
    for error in result["errors"]:
        print(f"[ERROR] {error}")
    if result["errors"]:
        return 1
    print("[OK] catalog structure and references (test execution is separate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
