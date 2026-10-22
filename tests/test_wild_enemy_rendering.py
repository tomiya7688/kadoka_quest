# {
#   責務: [test_wild_enemy_rendering: test・wild・敵・renderingの公開機能・宣言を定義する]
#   フィールド: []
# }
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


# {
#   責務: [screen: test・wild・敵・renderingの描画先を求める]
#   処理: [1: test・wild・敵・renderingの描画先を求める]
#   引数: [monkeypatch: monkeypatch]
#   戻り値: [result: 描画面（型注釈なし）]
# }
@pytest.fixture
def screen(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    surface = pygame.display.set_mode((1120, 740))
    yield surface
    pygame.display.quit()


# {
#   責務: [session: test・wild・敵・renderingのセッションを求める]
#   処理: [1: test・wild・敵・renderingのセッションを求める]
#   引数: [
#     width: 幅
#     height: 高さ
#   ]
#   戻り値: [result: test・wild・敵・renderingのセッションを求めるための結果（型注釈なし）]
# }
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


# {
#   責務: [wild: test・wild・敵・renderingのwildを求める]
#   処理: [1: test・wild・敵・renderingのwildを求める]
#   引数: [
#     species: 種族
#     x: X座標
#     y: Y座標
#     direction: direction
#   ]
#   戻り値: [result: test・wild・敵・renderingのwildを求めるための結果（型注釈なし）]
# }
def wild(species="slime", x=3, y=3, direction="front"):
    return {"x": x, "y": y, "spawn": {"species_id": species}, "direction": direction}


# {
#   責務: [provider: test・wild・敵・renderingのproviderを求める]
#   処理: [1: test・wild・敵・renderingのproviderを求める]
#   引数: []
#   戻り値: [result: 画像一覧（型注釈なし）]
# }
def provider():
    images = mock.Mock(spec=CharacterImageProvider)
    images.get.return_value = None
    images.appearance.return_value = {"value": "#FA1234"}
    return images


# {
#   責務: [test_multiple_species_and_directions_draw_without_changing_state: 検証: multiple species and directions draw without changing state]
#   処理: [1: 検証: multiple species and directions draw without changing state]
#   引数: [screen: 描画先]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_multiple_species_and_directions_draw_without_changing_state(screen):
    state = session()
    state.hidden_enemies.monsters = [wild("slime", 3, 3, "right"), wild("ghost", 5, 3, "left"), wild("metal_slime", 7, 3, "back")]
    colors = {"slime": (250, 30, 30), "ghost": (30, 250, 30), "metal_slime": (30, 30, 250)}
    images = provider()
    # {
    #   責務: [sprite: test・wild・敵・renderingのspriteを求める]
    #   処理: [1: test・wild・敵・renderingのspriteを求める]
    #   引数: [
    #     species: 種族
    #     kind: 種別
    #     size: 大きさ
    #   ]
    #   戻り値: [result: test・wild・敵・renderingのspriteを求めるための結果（型注釈なし）]
    # }
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


# {
#   責務: [test_missing_artwork_stays_visible_and_removed_enemy_disappears: 検証: missing artwork stays visible and removed enemy disappears]
#   処理: [1: 検証: missing artwork stays visible and removed enemy disappears]
#   引数: [screen: 描画先]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
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


# {
#   責務: [test_camera_clip_includes_partial_sprites_and_culls_distant_ones: 検証: camera clip includes partial sprites and culls distant ones]
#   処理: [1: 検証: camera clip includes partial sprites and culls distant ones]
#   引数: [screen: 描画先]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_camera_clip_includes_partial_sprites_and_culls_distant_ones(screen):
    state = session(50, 30)
    state.player.snap(25, 15)
    # カメラ寸法が変わっても左端へ半分だけ入る個体のクリップを検証します。
    camera_x = 25 - (FIELD_RECT.width // TILE) / 2
    camera_y = 15 - (FIELD_RECT.height // TILE) / 2
    state.hidden_enemies.monsters = [wild(x=camera_x - 0.5, y=10), wild("ghost", 0, 0)]
    images = provider()
    red = pygame.Surface((48, 48))
    red.fill((255, 0, 0))
    images.get.side_effect = lambda species, kind, size: red if species == "slime" else None
    draw_field(screen, state, images, [], 0, now=0)
    y = round(FIELD_RECT.y + (10 - camera_y) * TILE + 9)
    assert screen.get_at((FIELD_RECT.left, y))[:3] == (255, 0, 0)
    assert screen.get_at((FIELD_RECT.left - 1, y))[:3] != (255, 0, 0)
    assert not any(call.args[0] == "ghost" for call in images.get.call_args_list)


# {
#   責務: [test_successful_move_updates_facing_without_changing_chase_rules: 検証: successful move updates facing without changing chase rules]
#   処理: [1: 検証: successful move updates facing without changing chase rules]
#   引数: [
#     player: 主人公
#     direction: direction
#     target: 対象
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
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


# {
#   責務: [test_blocked_or_stationary_enemy_keeps_facing: 検証: blocked or stationary enemy keeps facing]
#   処理: [1: 検証: blocked or stationary enemy keeps facing]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_blocked_or_stationary_enemy_keeps_facing():
    state = session()
    enemy = wild(direction="back")
    state.hidden_enemies.monsters = [enemy]
    assert not state.hidden_enemies.move(enemy, (4, 3), set())
    assert enemy["direction"] == "back"


# {
#   責務: [test_population_starts_facing_front_and_keeps_spawn_data: 検証: population starts facing front and keeps spawn data]
#   処理: [1: 検証: population starts facing front and keeps spawn data]
#   引数: [seed: seed]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_population_starts_facing_front_and_keeps_spawn_data(seed):
    state = session()
    state.hidden_enemies.rng.seed(seed)
    state.hidden_enemies.reset((0, 0), {}, 0)
    assert state.hidden_enemies.monsters
    assert all(enemy["direction"] == "front" for enemy in state.hidden_enemies.monsters)
    assert {enemy["spawn"]["species_id"] for enemy in state.hidden_enemies.monsters} == {"slime", "ghost", "metal_slime"}


# {
#   責務: [test_shipped_field_sprites_are_loadable: 検証: shipped field sprites are loadable]
#   処理: [1: 検証: shipped field sprites are loadable]
#   引数: [
#     screen: 描画先
#     species: 種族
#     direction: direction
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("species", ["slime", "ghost", "metal_slime"])
@pytest.mark.parametrize("direction", ["front", "back", "left", "right"])
def test_shipped_field_sprites_are_loadable(screen, species, direction):
    root = Path(__file__).resolve().parents[1]
    images = CharacterImageProvider(GameRepository(root / "data"), root / "assets")
    sprite = images.get(species, f"field_{direction}", (48, 48))
    assert sprite is not None
    assert sprite.get_bounding_rect().width > 0
    assert max(sprite.get_size()) <= 48
