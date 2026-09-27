from __future__ import annotations

import copy
import random
from unittest import mock

import pytest

from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController


def controller(seed=147, vision_range=8):
    world = {"width": 15, "height": 15, "tiles": [["floor"] * 15 for _ in range(15)]}
    blocks = {"floor": {"enemy_walkable": True}, "wall": {"enemy_walkable": False}}
    result = HiddenEnemyController(FieldEngine(world, blocks), random.Random(seed), vision_range=vision_range)
    result.set_world(world, blocks)
    return result


def actor(ai="chase", x=5, y=5):
    return {"x": x, "y": y, "ai": ai, "direction": "back", "next_move_tick": 1000}


@pytest.mark.parametrize("player", [(8, 5), (5, 8), (1, 1)])
def test_idle_never_moves_or_consumes_randomness(player):
    field = controller()
    enemy = actor("idle")
    field.monsters = [enemy]
    rng_state = field.rng.getstate()
    for now in (999, 1000, 2000, 100000):
        assert not field.update(player, set(), now)
        assert not field.move_all(player, set())
        assert (enemy["x"], enemy["y"], enemy["direction"]) == (5, 5, "back")
        assert not enemy["chasing_player"]
    assert field.rng.getstate() == rng_state
    assert enemy["next_move_tick"] == 100950


def test_random_uses_all_cardinal_directions_and_wait_even_with_player_in_sight():
    destinations = set()
    for seed in range(100):
        field = controller(seed)
        enemy = actor("random")
        field.monsters = [enemy]
        field.update((8, 5), set(), 1000)
        destinations.add((enemy["x"], enemy["y"]))
        assert enemy["sees_player"]
        assert not enemy["chasing_player"]
        assert enemy["next_move_tick"] == 1950
    assert destinations == {(5, 5), (4, 5), (6, 5), (5, 4), (5, 6)}


@pytest.mark.parametrize("player,target,direction", [
    ((8, 5), (6, 5), "right"), ((2, 5), (4, 5), "left"),
    ((5, 2), (5, 4), "back"), ((5, 8), (5, 6), "front"),
])
def test_chase_obeys_tick_and_approaches_visible_player(player, target, direction):
    field = controller()
    enemy = actor()
    field.monsters = [enemy]
    before = copy.deepcopy(enemy)
    assert not field.update(player, set(), 999)
    assert enemy == before
    assert field.update(player, set(), 1000)
    assert (enemy["x"], enemy["y"]) == target
    assert enemy["direction"] == direction
    assert enemy["chasing_player"]
    assert enemy["next_move_tick"] == 1320
    assert not field.update(player, set(), 1319)


@pytest.mark.parametrize("player,wall,vision", [
    ((8, 5), None, 3), ((8, 5), (6, 5), 8), ((8, 8), None, 8),
    ((14, 5), None, 8),
])
def test_chase_requires_clear_axis_path_and_configured_range(player, wall, vision):
    field = controller(vision_range=vision)
    if wall:
        field.map_data["tiles"][wall[1]][wall[0]] = "wall"
    enemy = actor()
    field.monsters = [enemy]
    in_sight = player == (8, 5) and wall is None
    with mock.patch.object(field.rng, "shuffle", wraps=field.rng.shuffle) as shuffle:
        field.update(player, set(), 1000)
    assert enemy["chasing_player"] == in_sight
    assert shuffle.call_count == (0 if in_sight else 1)
    assert enemy["next_move_tick"] == (1320 if in_sight else 1950)


def test_lost_sight_returns_to_slow_wandering_and_clears_chasing_state():
    field = controller()
    enemy = actor()
    field.monsters = [enemy]
    field.update((8, 5), set(), 1000)
    assert enemy["chasing_player"]
    field.update((10, 10), set(), 1320)
    assert not enemy["chasing_player"]
    assert not enemy["sees_player"]
    assert enemy["next_move_tick"] == 2270


@pytest.mark.parametrize("blocker", ["player", "fixed", "wild"])
def test_chasers_cannot_enter_occupied_tiles(blocker):
    field = controller()
    enemy = actor()
    field.monsters = [enemy]
    fixed = {(6, 5)} if blocker == "fixed" else set()
    if blocker == "wild":
        field.monsters.append(actor("idle", 6, 5))
    player = (6, 5) if blocker == "player" else (8, 5)
    assert not field.move(enemy, player, fixed)
    assert (enemy["x"], enemy["y"]) == (5, 5)
    assert enemy["direction"] == "back"


def test_two_wanderers_competing_for_same_tile_do_not_overlap():
    field = controller()
    field.monsters = [actor("random", 5, 4), actor("random", 5, 6)]
    priorities = iter([(0, 1), (0, -1)])
    def prefer_shared_tile(directions):
        directions[:] = [next(priorities), (0, 0)]
    with mock.patch.object(field.rng, "shuffle", side_effect=prefer_shared_tile):
        assert field.move_all((12, 5), set())
    assert [(enemy["x"], enemy["y"]) for enemy in field.monsters] == [(5, 5), (5, 6)]


def test_seeded_mixed_population_stays_in_bounds_and_never_overlaps():
    def simulate():
        field = controller()
        field.map_data["tiles"][4][4] = "wall"
        field.monsters = [actor(kind, 2 + index, 5) for index, kind in enumerate(
            ["random", "chase", "idle"] * 3
        )]
        fixed = {(1, 1), (4, 6)}
        player = (12, 5)
        for tick in range(1000, 20000, 100):
            field.update(player, fixed, tick)
            positions = [(enemy["x"], enemy["y"]) for enemy in field.monsters]
            assert len(set(positions)) == len(positions)
            assert not set(positions) & (fixed | {player})
            assert all(field.field.tile_allows(x, y, "enemy_walkable") for x, y in positions)
        return field.monsters
    assert simulate() == simulate()


def test_legacy_missing_ai_keeps_chase_and_unknown_ai_wanders():
    field = controller()
    legacy = actor()
    del legacy["ai"]
    field.monsters = [legacy]
    field.update((8, 5), set(), 1000)
    assert legacy["chasing_player"] and legacy["next_move_tick"] == 1320
    unknown = actor("not_supported")
    field.monsters = [unknown]
    field.update((8, 5), set(), 1000)
    assert not unknown["chasing_player"] and unknown["next_move_tick"] == 1950
