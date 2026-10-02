from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("e2e_catalog_tool", ROOT / "tools/e2e-catalog/script/check_e2e_catalog.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def write_catalog(root, *, status="missing", reference="-", changes=None):
    row = dict(zip(tool.HEADER, ["KQ-P01", "起動", "隔離セーブ", "Player起動", "fieldへ入る",
                                "no", reference, status, "harness未対応。#201"]))
    row.update(changes or {})
    path = root / "catalog.md"
    path.write_text("| " + " | ".join(tool.HEADER) + " |\n| " + " | ".join(["---"] * 9)
                    + " |\n| " + " | ".join(row.values()) + " |\n", encoding="utf-8")
    return path


def test_repository_catalog_keeps_major_flows_explicitly_missing():
    result = tool.check_catalog(ROOT, ROOT / "docs/testing/E2E_EXPECTATIONS.md")
    assert not result["errors"]
    rows, _ = tool.catalog_rows((ROOT / "docs/testing/E2E_EXPECTATIONS.md").read_text(encoding="utf-8"))
    assert {"KQ-P02", "KQ-P11", "KQ-P19", "KQ-P20", "KQ-P25", "KQ-P29", "KQ-P30", "KQ-D06"} <= {
        row["ID"] for row in rows
    }


def test_deleted_e2e_returns_to_effective_missing_and_can_be_marked_missing(tmp_path):
    test = tmp_path / "tests/e2e/test_start.py"
    test.parent.mkdir(parents=True)
    test.write_text("def test_start():\n    assert True\n", encoding="utf-8")
    catalog = write_catalog(tmp_path, status="covered", reference="`tests/e2e/test_start.py::test_start`")
    assert tool.check_catalog(tmp_path, catalog)["counts"]["covered"] == 1
    test.unlink()
    result = tool.check_catalog(tmp_path, catalog)
    assert result["counts"]["covered"] == 0 and result["counts"]["missing"] == 1
    assert result["missing"][0].startswith("KQ-P01:")
    assert "test file is missing" in result["errors"][0]
    write_catalog(tmp_path)
    assert not tool.check_catalog(tmp_path, catalog)["errors"]


def test_multiple_function_and_class_references_are_checked_without_import(tmp_path):
    path = tmp_path / "tests/e2e/test_example.py"
    path.parent.mkdir(parents=True)
    path.write_text("raise RuntimeError('do not import')\ndef test_one():\n    assert True\n"
                    "class TestGroup:\n    def test_two(self):\n        assert True\n", encoding="utf-8")
    catalog = write_catalog(tmp_path, status="covered", reference=(
        "`tests/e2e/test_example.py::test_one`<br>`tests/e2e/test_example.py::TestGroup::test_two`"))
    assert not tool.check_catalog(tmp_path, catalog)["errors"]
    path.write_text("def test_one():\n    assert True\n", encoding="utf-8")
    assert tool.check_catalog(tmp_path, catalog)["counts"]["missing"] == 1


@pytest.mark.parametrize("reference", ["tests/test_unit.py::test_one", "../outside.py::test_one",
                                      "tests/e2e/file.py", "tests/e2e/file.py::helper"])
def test_wrong_boundary_and_missing_nodes_are_rejected(tmp_path, reference):
    catalog = write_catalog(tmp_path, status="covered", reference=reference)
    result = tool.check_catalog(tmp_path, catalog)
    assert result["errors"] and result["counts"]["missing"] == 1


@pytest.mark.parametrize("changes", [{"Given": "-"}, {"When": ""}, {"Then": "-"},
                                     {"Persistence": "maybe"}, {"Status": "done"},
                                     {"ID": "KQ-INVALID"}, {"理由/次の担当": "-"},
                                     {"E2E": "tests/e2e/future.py::test_one"}])
def test_incomplete_expectations_are_rejected(tmp_path, changes):
    assert tool.check_catalog(tmp_path, write_catalog(tmp_path, changes=changes))["errors"]


def test_duplicate_ids_and_malformed_table_are_errors(tmp_path):
    catalog = write_catalog(tmp_path)
    lines = catalog.read_text(encoding="utf-8").splitlines()
    catalog.write_text("\n".join(lines + [lines[-1], "| broken | row |"]), encoding="utf-8")
    errors = tool.check_catalog(tmp_path, catalog)["errors"]
    assert any("duplicate" in error for error in errors)
    assert any("columns" in error for error in errors)
    assert tool.catalog_rows("no table")[1]


def test_cli_reports_missing_and_fails_for_unreadable_catalog(tmp_path, capsys):
    catalog = write_catalog(tmp_path)
    assert tool.main(["--root", str(tmp_path), "--catalog", str(catalog), "--missing"]) == 0
    assert "KQ-P01: 起動" in capsys.readouterr().out
    assert tool.main(["--root", str(tmp_path), "--catalog", "absent.md"]) == 1
    assert "cannot be read" in capsys.readouterr().out
