# {
#   責務: [field_renderer: フィールドSessionの地形とキャラクターを広いゲーム画面へ描き、ゲーム状態を変更しません]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Sequence

import pygame

from kadoka_engine.grid_movement import GridMovement
from kadoka_quest.apps.field_session import FieldSession
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.ui.character_image_provider import CharacterImageProvider
from kadoka_quest.ui.game_ui import BG, TEXT, draw_frame, draw_text

FIELD_RECT = pygame.Rect(24, 64, 1072, 640)
TILE = 32


# {
#   責務: [_hex_color: 地形または代替キャラクターの16進色をRGBへ変換します]
#   処理: [1: 16進色の三成分を読み、不正な色には灰色を返します]
#   引数: [value: 先頭の#を省略できる6桁の16進色]
#   戻り値: [result: RGBの三成分。不正な入力では灰色]
# }
def _hex_color(value: str) -> tuple[int, int, int]:
    try:
        clean = value.lstrip("#")
        return tuple(int(clean[index:index + 2], 16) for index in (0, 2, 4))
    except (AttributeError, TypeError, ValueError):
        return (130, 130, 130)


# {
#   責務: [draw_field: 地形とフィールドの個体をカメラ内へ描き、現在地の名称を表示します]
#   処理: [
#     1: 主人公の表示位置からカメラ範囲を決めて地形を描きます
#     2: 野生個体・固定個体・主人公を同じ描画範囲へ重ねます
#     3: 描画先のクリップを復元して現在地の名称を表示します
#   ]
#   引数: [
#     screen: 描画先（pygame.Surface）
#     session: セッション（FieldSession）
#     images: キャラクター画像を返すProvider
#     party: 呼び出し互換のパーティ一覧。常設表示はせず、メニュー側で描きます
#     selected_index: 呼び出し互換の選択番号。メニュー側で選択個体を描きます
#     now: 移動補間に使うミリ秒。省略時はpygameの現在時刻
#   ]
#   戻り値: [result: なし。Session・個体・乱数状態を変更しません]
# }
def draw_field(
    screen: pygame.Surface,
    session: FieldSession,
    images: CharacterImageProvider,
    party: Sequence[MonsterRecord],
    selected_index: int,
    now: int | None = None,
) -> None:
    """Render a field snapshot; gameplay decisions stay in the core layer."""
    # カメラの拡大は表示範囲だけを変え、移動や出現の規則には触れません。
    now = pygame.time.get_ticks() if now is None else int(now)
    visible_x = min(FIELD_RECT.width // TILE, int(session.map_data["width"]))
    visible_y = min(FIELD_RECT.height // TILE, int(session.map_data["height"]))
    player_visual_x, player_visual_y = session.player.visual.position(now)
    camera_x = max(0.0, min(float(session.map_data["width"] - visible_x), player_visual_x - visible_x / 2))
    camera_y = max(0.0, min(float(session.map_data["height"] - visible_y), player_visual_y - visible_y / 2))
    draw_frame(screen, FIELD_RECT.inflate(8, 8))
    pygame.draw.rect(screen, BG, FIELD_RECT)
    previous_clip = screen.get_clip()
    screen.set_clip(FIELD_RECT)
    start_x, start_y = int(camera_x), int(camera_y)
    end_x = min(int(session.map_data["width"]), int(camera_x + visible_x) + 2)
    end_y = min(int(session.map_data["height"]), int(camera_y + visible_y) + 2)
    for gy in range(start_y, end_y):
        for gx in range(start_x, end_x):
            block_id = session.map_data["tiles"][gy][gx]
            block = session.blocks.get(block_id, {})
            appearance = block.get("appearance", {})
            override = session.map_data.get("block_color_overrides", {}).get(block_id)
            color = _hex_color(override) if override else (
                _hex_color(appearance.get("value", "#777777"))
                if appearance.get("type") == "color"
                else (110, 95, 125)
            )
            left = round(FIELD_RECT.x + (gx - camera_x) * TILE)
            top = round(FIELD_RECT.y + (gy - camera_y) * TILE)
            right = round(FIELD_RECT.x + (gx + 1 - camera_x) * TILE)
            bottom = round(FIELD_RECT.y + (gy + 1 - camera_y) * TILE)
            pygame.draw.rect(screen, color, pygame.Rect(left, top, right - left, bottom - top))

    # 全個体の画像を同じカメラとクリップで描き、画面外の野生画像取得を避けます。
    for monster in session.hidden_enemies.monsters:
        sx = round((float(monster["x"]) - camera_x) * TILE + FIELD_RECT.x)
        sy = round((float(monster["y"]) - camera_y) * TILE + FIELD_RECT.y)
        sprite_rect = pygame.Rect(0, 0, 48, 48)
        sprite_rect.center = (sx + TILE // 2, sy + TILE // 2 - 7)
        if not FIELD_RECT.colliderect(sprite_rect):
            continue
        species_id = str(monster["spawn"]["species_id"])
        direction = str(monster.get("direction", "front"))
        sprite = images.get(species_id, f"field_{direction}", (48, 48))
        if sprite:
            screen.blit(sprite, sprite.get_rect(center=sprite_rect.center))
        else:
            # Missing MOD artwork must not make an encounter invisible again.
            color = _hex_color(images.appearance(species_id).get("value", "#888888"))
            marker = pygame.Rect(0, 0, 24, 24)
            marker.center = sprite_rect.center
            pygame.draw.rect(screen, color, marker)
            pygame.draw.rect(screen, BG, marker, 2)
            dx, dy = {"left": (-1, 0), "right": (1, 0), "back": (0, -1)}.get(direction, (0, 1))
            pygame.draw.rect(screen, BG, (marker.centerx + dx * 7 - 2, marker.centery + dy * 7 - 2, 4, 4))

    for npc in session.fixed_mobs.npcs:
        movement = npc.get("_movement")
        npc_x, npc_y = (
            movement.position(now)
            if isinstance(movement, GridMovement)
            else (float(npc["x"]), float(npc["y"]))
        )
        sx = round((npc_x - camera_x) * TILE + FIELD_RECT.x)
        sy = round((npc_y - camera_y) * TILE + FIELD_RECT.y)
        if FIELD_RECT.collidepoint((sx + TILE // 2, sy + TILE // 2)):
            sprite = images.get(
                str(npc["species_id"]), f"field_{npc.get('direction', 'front')}", (48, 48)
            )
            if sprite:
                screen.blit(sprite, sprite.get_rect(center=(sx + TILE // 2, sy + TILE // 2 - 7)))

    px = round((player_visual_x - camera_x) * TILE + FIELD_RECT.x)
    py = round((player_visual_y - camera_y) * TILE + FIELD_RECT.y)
    player_sprite = images.get("hero", f"field_{session.player.direction}", (48, 48))
    if player_sprite:
        screen.blit(player_sprite, player_sprite.get_rect(center=(px + 16, py + 9)))
    else:
        pygame.draw.rect(screen, TEXT, (px + 6, py + 4, 20, 24))
        pygame.draw.rect(screen, BG, (px + 10, py + 10, 4, 4))
        pygame.draw.rect(screen, BG, (px + 18, py + 10, 4, 4))
    screen.set_clip(previous_clip)

    # 地図名だけを常設し、編成や操作説明はFieldOverlayのメニューへ集約します。
    draw_text(screen, session.map_data["display_name"], (24, 20), 16, TEXT)
