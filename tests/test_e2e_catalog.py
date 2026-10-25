# {
#   責務: [test_e2e_catalog: test・e2e・catalogの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("e2e_catalog_tool", ROOT / "tools/e2e-catalog/script/check_e2e_catalog.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


# {
#   責務: [write_catalog: catalogを書き込む]
#   処理: [1: catalogを書き込む]
#   引数: [
#     root: 基準ディレクトリ
#     status: 状態異常
#     reference: reference
#     changes: changes
#   ]
#   戻り値: [result: パス（型注釈なし）]
# }
def write_catalog(root, *, status="missing", reference="-", changes=None):
    row = dict(zip(tool.HEADER, ["KQ-P01", "起動", "隔離セーブ", "Player起動", "fieldへ入る",
                                "no", reference, status, "harness未対応。#201"]))
    row.update(changes or {})
    path = root / "catalog.md"
    path.write_text("| " + " | ".join(tool.HEADER) + " |\n| " + " | ".join(["---"] * 9)
                    + " |\n| " + " | ".join(row.values()) + " |\n", encoding="utf-8")
    return path


# {
#   責務: [test_repository_catalog_keeps_major_flows_explicitly_missing: 検証: repository catalog keeps major flows explicitly missing]
#   処理: [1: 検証: repository catalog keeps major flows explicitly missing]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_repository_catalog_keeps_major_flows_explicitly_missing():
    result = tool.check_catalog(ROOT, ROOT / "docs/testing/E2E_EXPECTATIONS.md")
    assert not result["errors"]
    rows, _ = tool.catalog_rows((ROOT / "docs/testing/E2E_EXPECTATIONS.md").read_text(encoding="utf-8"))
    assert {"KQ-P02", "KQ-P11", "KQ-P19", "KQ-P20", "KQ-P25", "KQ-P29", "KQ-P30", "KQ-D06"} <= {
        row["ID"] for row in rows
    }
    # Godot版のタイトル画面のシナリオは、Godot用harnessのE2Eテストを参照するcoveredとして登録します。
    godot = {row["ID"]: row for row in rows if row["ID"].startswith("KQ-G")}
    assert {"KQ-G01", "KQ-G02", "KQ-G03", "KQ-G04"} <= set(godot)
    for scenario in ("KQ-G01", "KQ-G02", "KQ-G03", "KQ-G04"):
        assert godot[scenario]["Status"] == "covered"
        assert godot[scenario]["E2E"].startswith("`tests/e2e/test_godot_title_journeys.py::")


# {
#   責務: [test_deleted_e2e_returns_to_effective_missing_and_can_be_marked_missing: 検証: deleted e2e returns to effective missing and can be marked missing]
#   処理: [1: 検証: deleted e2e returns to effective missing and can be marked missing]
#   引数: [tmp_path: tmp・パス]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
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


# {
#   責務: [test_multiple_function_and_class_references_are_checked_without_import: 検証: multiple function and class references are checked without import]
#   処理: [1: 検証: multiple function and class references are checked without import]
#   引数: [tmp_path: tmp・パス]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
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


# {
#   責務: [test_wrong_boundary_and_missing_nodes_are_rejected: 検証: wrong boundary and missing nodes are rejected]
#   処理: [1: 検証: wrong boundary and missing nodes are rejected]
#   引数: [
#     tmp_path: tmp・パス
#     reference: reference
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("reference", ["tests/test_unit.py::test_one", "../outside.py::test_one",
                                      "tests/e2e/file.py", "tests/e2e/file.py::helper"])
def test_wrong_boundary_and_missing_nodes_are_rejected(tmp_path, reference):
    catalog = write_catalog(tmp_path, status="covered", reference=reference)
    result = tool.check_catalog(tmp_path, catalog)
    assert result["errors"] and result["counts"]["missing"] == 1


# {
#   責務: [test_incomplete_expectations_are_rejected: 検証: incomplete expectations are rejected]
#   処理: [1: 検証: incomplete expectations are rejected]
#   引数: [
#     tmp_path: tmp・パス
#     changes: changes
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("changes", [{"Given": "-"}, {"When": ""}, {"Then": "-"},
                                     {"Persistence": "maybe"}, {"Status": "done"},
                                     {"ID": "KQ-INVALID"}, {"理由/次の担当": "-"},
                                     {"E2E": "tests/e2e/future.py::test_one"}])
def test_incomplete_expectations_are_rejected(tmp_path, changes):
    assert tool.check_catalog(tmp_path, write_catalog(tmp_path, changes=changes))["errors"]


# {
#   責務: [test_duplicate_ids_and_malformed_table_are_errors: 検証: duplicate ids and malformed table are errors]
#   処理: [1: 検証: duplicate ids and malformed table are errors]
#   引数: [tmp_path: tmp・パス]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_duplicate_ids_and_malformed_table_are_errors(tmp_path):
    catalog = write_catalog(tmp_path)
    lines = catalog.read_text(encoding="utf-8").splitlines()
    catalog.write_text("\n".join(lines + [lines[-1], "| broken | row |"]), encoding="utf-8")
    errors = tool.check_catalog(tmp_path, catalog)["errors"]
    assert any("duplicate" in error for error in errors)
    assert any("columns" in error for error in errors)
    assert tool.catalog_rows("no table")[1]


# {
#   責務: [test_cli_reports_missing_and_fails_for_unreadable_catalog: 検証: cli reports missing and fails for unreadable catalog]
#   処理: [1: 検証: cli reports missing and fails for unreadable catalog]
#   引数: [
#     tmp_path: tmp・パス
#     capsys: capsys
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_cli_reports_missing_and_fails_for_unreadable_catalog(tmp_path, capsys):
    catalog = write_catalog(tmp_path)
    assert tool.main(["--root", str(tmp_path), "--catalog", str(catalog), "--missing"]) == 0
    assert "KQ-P01: 起動" in capsys.readouterr().out
    assert tool.main(["--root", str(tmp_path), "--catalog", "absent.md"]) == 1
    assert "cannot be read" in capsys.readouterr().out
