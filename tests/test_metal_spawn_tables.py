from __future__ import annotations

import json
from pathlib import Path
import random

import pytest

from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController


DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
EARLY_MAPS = (
    "starting_town", "starting_ranch", "greenwood",
    "fresh_forest", "rokuta_village", "ghost_home",
)


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
