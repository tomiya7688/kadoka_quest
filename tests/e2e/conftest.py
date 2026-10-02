import json
import shutil

import pytest

from .harness import PROJECT_ROOT, ScenarioRunner


@pytest.fixture
def scenario_runner(tmp_path):
    return ScenarioRunner(tmp_path / "e2e")


@pytest.fixture
def saved_start(tmp_path):
    """Given an openly editable saved position, not a runtime state mutation."""
    def create(map_id, x, y):
        root = tmp_path / f"given-{map_id}-{x}-{y}"
        root.mkdir(exist_ok=True)
        state = {"schema_version": 1, "map_id": map_id, "player": {"x": x, "y": y},
                 "current_party": [], "flags": {"ghost_entrance_open": False},
                 "inventory": {"orange": 3}}
        (root / "state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        return root
    return create


@pytest.fixture
def field_data_fixture(tmp_path):
    """Canonical species/blocks plus a small, explicit JSON scenario map."""
    root = tmp_path / "data"
    shutil.copytree(PROJECT_ROOT / "data", root)

    def create(obstacle=None, door=None):
        tiles = [["wall" if x in {0, 9} or y in {0, 7} else "path" for x in range(10)] for y in range(8)]
        world = {"schema_version": 1, "id": "e2e_field", "display_name": "E2E検証の草原",
                 "width": 10, "height": 8, "start": {"x": 2, "y": 3}, "tiles": tiles,
                 "spawns": [], "pop_rate": 0, "fixed_mobs": [], "events": []}
        if obstacle == "wall":
            tiles[3][3] = "wall"
        elif obstacle in {"rock", "sign"}:
            world["events"].append({"id": obstacle, "type": "message", "x": 3, "y": 3,
                                    "blocking": True, "blocked_text": f"{obstacle}は通れません。"})
        elif obstacle == "fixed_mob":
            world["fixed_mobs"].append({"id": "visitor", "species_id": "ghost", "x": 3, "y": 3,
                                        "ai": "idle", "interaction": "talk", "dialogue": ["こんにちは"]})
        elif obstacle == "wild_mob":
            tiles[3][3] = "grass"  # The only spawnable tile: deterministic, no actor injection.
            world["pop_rate"] = 100
            world["spawns"] = [{"species_id": "slime", "min_level": 1, "max_level": 1,
                                "weight": 1, "field_ai_weights": {"idle": 100}}]
        if door:
            world["events"].append({"id": "door", "type": "transition", "activation": door,
                                    "x": 3, "y": 3,
                                    "target": {"map_id": "starting_town", "x": 18, "y": 14}})
        folder = root / "maps" / "e2e_field"
        folder.mkdir(exist_ok=True)
        (folder / "map.json").write_text(json.dumps(world, ensure_ascii=False), encoding="utf-8")
        return root
    return create
