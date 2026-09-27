from __future__ import annotations

import copy
from pathlib import Path
import random
from unittest import mock

import pygame
import pytest

from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.fixed_mob_controller import FixedMobController
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController
from kadoka_engine.player_field_controller import PlayerFieldController
from kadoka_quest.apps.field_session import FieldSession
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.ui.character_image_provider import CharacterImageProvider
from kadoka_quest.ui.field_renderer import FIELD_RECT, TILE, draw_field


@pytest.fixture
def screen(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    surface = pygame.display.set_mode((1120, 740))
    yield surface
    pygame.display.quit()


def session(width=12, height=12):
    world = {
        "id": "test", "display_name": "表示テスト", "width": width, "height": height,
        "tiles": [["grass"] * width for _ in range(height)],
        "spawns": [{"species_id": name, "weight": 1} for name in ("slime", "ghost", "metal_slime")],
    }
    blocks = {"grass": {
        "appearance": {"type": "color", "value": "#123456"},
        "enemy_walkable": True, "enemy_spawnable": True,
    }}
    field = FieldEngine(world, blocks)
    return FieldSession(field, PlayerFieldController(0, 0),
                        FixedMobController(field, random.Random(1)),
                        HiddenEnemyController(field, random.Random(2)))


def wild(species="slime", x=3, y=3, direction="front"):
    return {"x": x, "y": y, "spawn": {"species_id": species}, "direction": direction}


def provider():
    images = mock.Mock(spec=CharacterImageProvider)
    images.get.return_value = None
    images.appearance.return_value = {"value": "#FA1234"}
    return images


def test_multiple_species_and_directions_draw_without_changing_state(screen):
    state = session()
    state.hidden_enemies.monsters = [wild("slime", 3, 3, "right"), wild("ghost", 5, 3, "left"), wild("metal_slime", 7, 3, "back")]
    colors = {"slime": (250, 30, 30), "ghost": (30, 250, 30), "metal_slime": (30, 30, 250)}
    images = provider()
    def sprite(species, kind, size):
        if species not in colors:
            return None
        surface = pygame.Surface((48, 48))
        surface.fill(colors[species])
        return surface
    images.get.side_effect = sprite
    before = copy.deepcopy(state.hidden_enemies.monsters)
    rng_state = state.hidden_enemies.rng.getstate()
    clip = screen.get_clip()
    draw_field(screen, state, images, [], 0, now=0)
    for enemy in before:
        species = enemy["spawn"]["species_id"]
        images.get.assert_any_call(species, f"field_{enemy['direction']}", (48, 48))
        center = (FIELD_RECT.x + enemy["x"] * TILE + 16, FIELD_RECT.y + enemy["y"] * TILE + 9)
        assert screen.get_at(center)[:3] == colors[species]
    assert state.hidden_enemies.monsters == before
    assert state.hidden_enemies.rng.getstate() == rng_state
    assert screen.get_clip() == clip


def test_missing_artwork_stays_visible_and_removed_enemy_disappears(screen):
    state = session()
    enemy = wild()
    del enemy["direction"]  # Older callers may not provide direction.
    state.hidden_enemies.monsters = [enemy]
    images = provider()
    center = (FIELD_RECT.x + 3 * TILE + 16, FIELD_RECT.y + 3 * TILE + 9)
    draw_field(screen, state, images, [], 0, now=0)
    images.get.assert_any_call("slime", "field_front", (48, 48))
    assert screen.get_at(center)[:3] == (250, 18, 52)
    state.hidden_enemies.remove(enemy)
    draw_field(screen, state, images, [], 0, now=0)
    assert screen.get_at(center)[:3] == (18, 52, 86)


def test_camera_clip_includes_partial_sprites_and_culls_distant_ones(screen):
    state = session(50, 30)
    state.player.snap(25, 15)  # camera origin = (12.5, 6)
    state.hidden_enemies.monsters = [wild(x=12, y=10), wild("ghost", 0, 0)]
    images = provider()
    red = pygame.Surface((48, 48))
    red.fill((255, 0, 0))
    images.get.side_effect = lambda species, kind, size: red if species == "slime" else None
    draw_field(screen, state, images, [], 0, now=0)
    y = FIELD_RECT.y + (10 - 6) * TILE + 9
    assert screen.get_at((FIELD_RECT.left, y))[:3] == (255, 0, 0)
    assert screen.get_at((FIELD_RECT.left - 1, y))[:3] != (255, 0, 0)
    assert not any(call.args[0] == "ghost" for call in images.get.call_args_list)


@pytest.mark.parametrize("player,direction,target", [
    ((5, 3), "right", (4, 3)), ((1, 3), "left", (2, 3)),
    ((3, 1), "back", (3, 2)), ((3, 5), "front", (3, 4)),
])
def test_successful_move_updates_facing_without_changing_chase_rules(player, direction, target):
    state = session()
    enemy = wild(direction="left")
    state.hidden_enemies.monsters = [enemy]
    assert state.hidden_enemies.move(enemy, player, set())
    assert (enemy["x"], enemy["y"]) == target
    assert enemy["direction"] == direction


def test_blocked_or_stationary_enemy_keeps_facing():
    state = session()
    enemy = wild(direction="back")
    state.hidden_enemies.monsters = [enemy]
    assert not state.hidden_enemies.move(enemy, (4, 3), set())
    assert enemy["direction"] == "back"


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_population_starts_facing_front_and_keeps_spawn_data(seed):
    state = session()
    state.hidden_enemies.rng.seed(seed)
    state.hidden_enemies.reset((0, 0), {}, 0)
    assert state.hidden_enemies.monsters
    assert all(enemy["direction"] == "front" for enemy in state.hidden_enemies.monsters)
    assert {enemy["spawn"]["species_id"] for enemy in state.hidden_enemies.monsters} == {"slime", "ghost", "metal_slime"}


@pytest.mark.parametrize("species", ["slime", "ghost", "metal_slime"])
@pytest.mark.parametrize("direction", ["front", "back", "left", "right"])
def test_shipped_field_sprites_are_loadable(screen, species, direction):
    root = Path(__file__).resolve().parents[1]
    images = CharacterImageProvider(GameRepository(root / "data"), root / "assets")
    sprite = images.get(species, f"field_{direction}", (48, 48))
    assert sprite is not None
    assert sprite.get_bounding_rect().width > 0
    assert max(sprite.get_size()) <= 48
