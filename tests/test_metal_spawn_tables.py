from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
import random
import shutil
from unittest import mock

import pytest

from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController
from kadoka_quest.data.map_presets import MapPresetStore
from kadoka_quest.data.repository import GameRepository


DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
EARLY_MAPS = (
    "starting_town", "starting_ranch", "greenwood",
    "fresh_forest", "rokuta_village", "ghost_home",
)
MIDGAME_PRESET = "midgame_field"


def read_map(map_id):
    return json.loads((DATA_ROOT / "maps" / map_id / "map.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("map_id", EARLY_MAPS)
@pytest.mark.parametrize("story_complete", [False, True])
def test_early_maps_never_offer_metal_slime(map_id, story_complete):
    world = read_map(map_id)
    assert "metal_slime" not in {entry["species_id"] for entry in world["spawns"]}
    controller = HiddenEnemyController(FieldEngine(world, {}), random.Random(1))
    controller.set_world(world, {})
    options = controller.spawn_options({"story_complete": story_complete, "ghost_entrance_open": True})
    assert "metal_slime" not in {entry["species_id"] for entry in options}


@pytest.mark.parametrize("map_id,expected", [
    ("greenwood", [("slime", 72, 2, 5), ("ghost", 23, 3, 6)]),
    ("fresh_forest", [("slime", 48, 5, 9), ("ghost", 42, 6, 10)]),
])
def test_ordinary_enemy_weights_and_levels_are_preserved(map_id, expected):
    assert [
        (entry["species_id"], entry["weight"], entry["min_level"], entry["max_level"])
        for entry in read_map(map_id)["spawns"]
    ] == expected


@pytest.mark.parametrize("map_id", ["greenwood", "fresh_forest"])
def test_repeated_field_population_contains_no_metal_slime(map_id):
    world = read_map(map_id)
    blocks = {}
    for path in (DATA_ROOT / "blocks").glob("*.json"):
        block = json.loads(path.read_text(encoding="utf-8"))
        blocks[block["id"]] = block
    for seed in range(20):
        controller = HiddenEnemyController(FieldEngine(world, blocks), random.Random(seed))
        controller.set_world(world, blocks)
        controller.reset((world["start"]["x"], world["start"]["y"]), {}, 0)
        assert controller.monsters
        assert {enemy["spawn"]["species_id"] for enemy in controller.monsters} <= {"slime", "ghost"}


@pytest.mark.parametrize("story_complete", [False, True])
def test_midgame_preset_has_exact_one_percent_metal_probability(story_complete):
    presets = MapPresetStore(DATA_ROOT)
    assert MIDGAME_PRESET in presets.list_ids()
    world = presets.build_map(MIDGAME_PRESET, "test_midgame", "中盤テスト")
    controller = HiddenEnemyController(FieldEngine(world, {}), random.Random(1))
    controller.set_world(world, {})
    options = controller.spawn_options({"story_complete": story_complete})
    assert len(options) == len(world["spawns"]) == 3
    assert all(not entry.get("requires_flag") for entry in options)
    total = sum(entry["weight"] for entry in options)
    metal = sum(entry["weight"] for entry in options if entry["species_id"] == "metal_slime")
    assert total == 100
    assert Fraction(metal, total) == Fraction(1, 100)
    assert all(1 <= entry["min_level"] <= entry["max_level"] <= 100 for entry in options)


def test_midgame_preset_is_not_an_automatically_connected_map():
    repository = GameRepository(DATA_ROOT)
    world = MapPresetStore(DATA_ROOT).get(MIDGAME_PRESET)
    assert MIDGAME_PRESET not in repository.list_maps()
    assert world["events"] == []
    assert world["fixed_mobs"] == []
    assert len(world["tiles"]) == world["height"]
    assert all(len(row) == world["width"] for row in world["tiles"])
    blocks = {item["id"]: item for item in repository.list_blocks()}
    assert all(block_id in blocks for row in world["tiles"] for block_id in row)
    start = world["start"]
    tile = blocks[world["tiles"][start["y"]][start["x"]]]
    assert tile["player_walkable"] and not tile["enemy_spawnable"]


def test_midgame_runtime_uses_full_weight_table_and_samples_rare_metal():
    world = MapPresetStore(DATA_ROOT).get(MIDGAME_PRESET)
    blocks = {item["id"]: item for item in GameRepository(DATA_ROOT).list_blocks()}
    rng = random.Random(141)
    controller = HiddenEnemyController(FieldEngine(world, blocks), rng)
    controller.set_world(world, blocks)
    with mock.patch.object(rng, "choices", wraps=rng.choices) as choose:
        controller.reset((world["start"]["x"], world["start"]["y"]), {}, 0)
    species_calls = [call for call in choose.call_args_list if call.args[0] == world["spawns"]]
    assert len(species_calls) == len(controller.monsters) > 0
    for call in species_calls:
        weights = call.kwargs["weights"]
        assert [weight / sum(weights) for weight in weights] == pytest.approx([0.60, 0.39, 0.01])
    # Seeded smoke check supplements the exact rational probability test above.
    samples = random.Random(141).choices(controller.spawn_options({}), weights=weights, k=100_000)
    hits = sum(entry["species_id"] == "metal_slime" for entry in samples)
    assert 900 <= hits <= 1100


def test_editor_creates_midgame_map_without_changing_existing_maps(tmp_path, monkeypatch):
    import pygame
    from kadoka_quest.apps.map_editor import MapEditor

    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    root = tmp_path / "data"
    shutil.copytree(DATA_ROOT, root)
    before = {path: path.read_bytes() for path in (root / "maps").glob("*/map.json")}
    preset_path = root / "map_presets" / f"{MIDGAME_PRESET}.json"
    original_preset = preset_path.read_bytes()
    repository = GameRepository(root)
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((1, 1))
    try:
        editor = MapEditor(repository, MapPresetStore(root))
        editor.open_preset_dialog()
        editor.select_preset(editor.preset_ids.index(MIDGAME_PRESET))
        editor.preset_map_id.value = "test_midgame"
        editor.preset_map_name.value = "中盤のテスト地域"
        assert editor.create_map_from_selected_preset(), editor.status
        saved = repository.get_map("test_midgame")
        assert saved == editor.map_data
        assert saved["spawns"] == MapPresetStore(root).get(MIDGAME_PRESET)["spawns"]
        assert saved["id"] == "test_midgame"
        assert saved["display_name"] == "中盤のテスト地域"
        assert not editor.dirty
        assert all(path.read_bytes() == content for path, content in before.items())
        assert preset_path.read_bytes() == original_preset
    finally:
        pygame.display.quit()
