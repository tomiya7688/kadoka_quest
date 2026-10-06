# {
#   責務: [test_spawn_settings: test・出現・設定の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_engine.data_validator import DataValidator
from kadoka_engine.spawn_settings import normalize_map_spawns, validate_map_spawns
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [codes: test・出現・設定のcodesを求める]
#   処理: [1: test・出現・設定のcodesを求める]
#   引数: [document: 文書（dict）]
#   戻り値: [result: test・出現・設定のcodesを求めるための結果（set[str]）]
# }
def codes(document: dict) -> set[str]:
    return {issue["code"] for issue in validate_map_spawns(document)}


# {
#   責務: [test_valid_pop_rate: 検証: valid pop rate]
#   処理: [1: 検証: valid pop rate]
#   引数: [rate: rate]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("rate", [0, 100, 12.5])
def test_valid_pop_rate(rate):
    assert validate_map_spawns({"pop_rate": rate}) == []


# {
#   責務: [test_invalid_pop_rate: 検証: invalid pop rate]
#   処理: [1: 検証: invalid pop rate]
#   引数: [rate: rate]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("rate", [-1, 101, True, "50", None, float("nan"), float("inf"), 10**1000])
def test_invalid_pop_rate(rate):
    assert codes({"pop_rate": rate}) == {"map.pop_rate_invalid"}


# {
#   責務: [test_invalid_species_weight: 検証: invalid species weight]
#   処理: [1: 検証: invalid species weight]
#   引数: [weight: 重み]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("weight", [-1, False, "1", None, float("nan"), float("inf"), 10**1000])
def test_invalid_species_weight(weight):
    assert codes({"spawns": [{"species_id": "slime", "weight": weight}]}) == {"map.spawn_weight_invalid"}


# {
#   責務: [test_relative_species_weights_and_empty_tables: 検証: relative species weights and empty tables]
#   処理: [1: 検証: relative species weights and empty tables]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_relative_species_weights_and_empty_tables():
    document = {"spawns": [
        {"species_id": "slime", "weight": 60},
        {"species_id": "ghost", "weight": 30},
        {"species_id": "metal_slime", "weight": 0.5},
        {"species_id": "dice_slime", "weight": 0},
    ]}
    assert validate_map_spawns(document) == []
    assert validate_map_spawns({"spawns": []}) == []
    for spawn in document["spawns"]:
        spawn["weight"] = 0
    document["pop_rate"] = 0
    assert codes(document) == {"map.spawn_weights_zero"}


# {
#   責務: [test_invalid_level_ranges: 検証: invalid level ranges]
#   処理: [1: 検証: invalid level ranges]
#   引数: [
#     minimum: minimum
#     maximum: maximum
#     code: code
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("minimum,maximum,code", [
    (0, 1, "map.spawn_level_invalid"),
    (1, 101, "map.spawn_level_invalid"),
    (True, 3, "map.spawn_level_invalid"),
    (1, 2.0, "map.spawn_level_invalid"),
    ("1", 2, "map.spawn_level_invalid"),
    (None, 2, "map.spawn_level_invalid"),
    (5, 4, "map.spawn_level_range"),
])
def test_invalid_level_ranges(minimum, maximum, code):
    assert codes({"spawns": [{"species_id": "slime", "min_level": minimum, "max_level": maximum}]}) == {code}


# {
#   責務: [test_valid_level_bounds_and_catalog: 検証: valid level bounds and catalog]
#   処理: [1: 検証: valid level bounds and catalog]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_valid_level_bounds_and_catalog():
    document = {"spawns": [{"species_id": "mod_slime", "min_level": 1, "max_level": 100}]}
    assert validate_map_spawns(document) == []
    assert validate_map_spawns(document, {"mod_slime"}) == []
    assert validate_map_spawns(document, {"slime"})[0]["code"] == "map.spawn_species_unknown"
    assert codes({"spawns": [{"species_id": "ball_slime"}]}) == {"map.spawn_starter_only"}


# {
#   責務: [test_invalid_species_id: 検証: invalid species id]
#   処理: [1: 検証: invalid species id]
#   引数: [species: 種族]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("species", [None, "", " ", [], 3])
def test_invalid_species_id(species):
    assert codes({"spawns": [{"species_id": species}]}) == {"map.spawn_species_unknown"}


# {
#   責務: [test_invalid_ai_tables_identify_both_locations: 検証: invalid ai tables identify both locations]
#   処理: [1: 検証: invalid ai tables identify both locations]
#   引数: [weights: 重み一覧]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("weights", [{}, {"idle": 0}, {"random": -1}, {"chase": True},
                                        {"idle": "1"}, {"idle": float("inf")},
                                        {"idle": float("nan")}, {"idle": 10**1000},
                                        {"unknown": 1}, []])
def test_invalid_ai_tables_identify_both_locations(weights):
    document = {"field_ai_weights": weights, "spawns": [
        {"species_id": "slime", "field_ai_weights": weights},
    ]}
    issues = validate_map_spawns(document)
    assert {issue["code"] for issue in issues} == {"map.spawn_ai_weights_invalid"}
    assert [issue["field"] for issue in issues] == ["field_ai_weights", "spawns[0].field_ai_weights"]


# {
#   責務: [test_valid_ai_tables: 検証: valid ai tables]
#   処理: [1: 検証: valid ai tables]
#   引数: [weights: 重み一覧]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("weights", [None, {"idle": 1}, {"random": 60, "chase": 0.5, "idle": 0}])
def test_valid_ai_tables(weights):
    assert validate_map_spawns({"field_ai_weights": weights, "spawns": [
        {"species_id": "slime", "field_ai_weights": weights},
    ]}) == []


# {
#   責務: [test_malformed_spawn_structure: 検証: malformed spawn structure]
#   処理: [1: 検証: malformed spawn structure]
#   引数: [
#     spawns: spawns
#     code: code
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("spawns,code", [(None, "map.spawns_invalid"), ({}, "map.spawns_invalid"),
                                       ([None], "map.spawn_invalid"), ([[]], "map.spawn_invalid")])
def test_malformed_spawn_structure(spawns, code):
    assert codes({"spawns": spawns}) == {code}


# {
#   責務: [test_legacy_defaults_are_detached_and_preserve_mod_data: 検証: legacy defaults are detached and preserve mod data]
#   処理: [1: 検証: legacy defaults are detached and preserve mod data]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_legacy_defaults_are_detached_and_preserve_mod_data():
    legacy = {"id": "legacy", "mod_data": {"tags": ["custom"]}, "spawns": [
        {"species_id": "slime", "requires_flag": "custom_flag", "field_ai_weights": None},
    ]}
    before = deepcopy(legacy)
    normalized = normalize_map_spawns(legacy, {"slime"})
    assert legacy == before
    assert normalized["pop_rate"] == 100
    assert normalized["spawns"][0] == dict(legacy["spawns"][0], weight=1, min_level=1, max_level=1)
    assert normalize_map_spawns(normalized) == normalized
    normalized["mod_data"]["tags"].append("new")
    normalized["spawns"][0]["weight"] = 50
    assert legacy == before
    assert normalize_map_spawns({}) == {"pop_rate": 100, "spawns": []}


# {
#   責務: [test_invalid_normalization_does_not_mutate_input: 検証: invalid normalization does not mutate input]
#   処理: [1: 検証: invalid normalization does not mutate input]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_invalid_normalization_does_not_mutate_input():
    document = {"pop_rate": -1, "spawns": [{"species_id": "slime"}]}
    before = deepcopy(document)
    with pytest.raises(ValueError, match="pop_rate"):
        normalize_map_spawns(document)
    assert document == before


# {
#   責務: [test_repository_round_trip_preserves_spawn_contract: 検証: repository round trip preserves spawn contract]
#   処理: [1: 検証: repository round trip preserves spawn contract]
#   引数: [tmp_path: tmp・パス]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_repository_round_trip_preserves_spawn_contract(tmp_path):
    document = normalize_map_spawns({"id": "sample", "pop_rate": 12.5,
        "field_ai_weights": {"chase": 1}, "spawns": [
            {"species_id": "slime", "weight": 0.5, "min_level": 2, "max_level": 9,
             "field_ai_weights": {"random": 3}, "requires_flag": "unlocked"},
        ], "custom": {"value": [1, 2]}})
    repository = GameRepository(tmp_path)
    repository.save_map(document)
    assert repository.get_map("sample") == document


# {
#   責務: [test_validator_reports_contract_errors_with_map_path: 検証: validator reports contract errors with map path]
#   処理: [1: 検証: validator reports contract errors with map path]
#   引数: [tmp_path: tmp・パス]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_validator_reports_contract_errors_with_map_path(tmp_path):
    root = tmp_path / "data"
    shutil.copytree(PROJECT_ROOT / "data", root)
    path = root / "maps" / "fresh_forest" / "map.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["pop_rate"] = 101
    document["field_ai_weights"] = {"idle": 0}
    document["spawns"] = [{"species_id": "slime", "weight": -1}]
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    issues = DataValidator(root).validate()
    for code, field in [("map.pop_rate_invalid", "pop_rate"),
                        ("map.spawn_ai_weights_invalid", "field_ai_weights"),
                        ("map.spawn_weight_invalid", "spawns[0].weight")]:
        issue = next(item for item in issues if item["code"] == code)
        assert "fresh_forest" in issue["path"]
        assert field in issue["message"]


# {
#   責務: [test_bundled_maps_accept_legacy_defaults_without_rewriting: 検証: bundled maps accept legacy defaults without rewriting]
#   処理: [1: 検証: bundled maps accept legacy defaults without rewriting]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_bundled_maps_accept_legacy_defaults_without_rewriting():
    for path in (PROJECT_ROOT / "data" / "maps").glob("*/map.json"):
        original = path.read_bytes()
        document = json.loads(original)
        normalized = normalize_map_spawns(document)
        assert validate_map_spawns(normalized) == []
        assert path.read_bytes() == original
