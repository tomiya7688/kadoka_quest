from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from kadoka_quest.core.grid_movement import GridMovement
from kadoka_quest.ui.common import ACCENT, BG, MUTED, PANEL, PANEL_ALT, draw_text

if TYPE_CHECKING:
    from kadoka_quest.apps.game import KadokaQuest


FIELD_RECT = pygame.Rect(20, 70, 800, 576)
TILE = 32


def _hex_color(value: str) -> tuple[int, int, int]:
    try:
        clean = value.lstrip("#")
        return tuple(int(clean[index:index + 2], 16) for index in (0, 2, 4))
    except (AttributeError, TypeError, ValueError):
        return (130, 130, 130)


def draw_field(screen: pygame.Surface, game: KadokaQuest, now: int | None = None) -> None:
    """Render a field snapshot; gameplay decisions stay in the core layer."""
    now = pygame.time.get_ticks() if now is None else int(now)
    visible_x = min(FIELD_RECT.width // TILE, int(game.map_data["width"]))
    visible_y = min(FIELD_RECT.height // TILE, int(game.map_data["height"]))
    player_visual_x, player_visual_y = game.player_movement.position(now)
    camera_x = max(0.0, min(float(game.map_data["width"] - visible_x), player_visual_x - visible_x / 2))
    camera_y = max(0.0, min(float(game.map_data["height"] - visible_y), player_visual_y - visible_y / 2))
    pygame.draw.rect(screen, PANEL, FIELD_RECT.inflate(8, 8), border_radius=8)
    pygame.draw.rect(screen, PANEL, FIELD_RECT)
    previous_clip = screen.get_clip()
    screen.set_clip(FIELD_RECT)
    start_x, start_y = int(camera_x), int(camera_y)
    end_x = min(int(game.map_data["width"]), int(camera_x + visible_x) + 2)
    end_y = min(int(game.map_data["height"]), int(camera_y + visible_y) + 2)
    for gy in range(start_y, end_y):
        for gx in range(start_x, end_x):
            block_id = game.map_data["tiles"][gy][gx]
            block = game.blocks.get(block_id, {})
            appearance = block.get("appearance", {})
            override = game.map_data.get("block_color_overrides", {}).get(block_id)
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

    for npc in game.home_npcs:
        movement = npc.get("_movement")
        npc_x, npc_y = (
            movement.position(now)
            if isinstance(movement, GridMovement)
            else (float(npc["x"]), float(npc["y"]))
        )
        sx = round((npc_x - camera_x) * TILE + FIELD_RECT.x)
        sy = round((npc_y - camera_y) * TILE + FIELD_RECT.y)
        if FIELD_RECT.collidepoint((sx + TILE // 2, sy + TILE // 2)):
            sprite = game.character_image(
                str(npc["species_id"]), f"field_{npc.get('direction', 'front')}", (48, 48)
            )
            if sprite:
                screen.blit(sprite, sprite.get_rect(center=(sx + TILE // 2, sy + TILE // 2 - 7)))

    px = round((player_visual_x - camera_x) * TILE + FIELD_RECT.x)
    py = round((player_visual_y - camera_y) * TILE + FIELD_RECT.y)
    player_sprite = game.character_image("hero", f"field_{game.player_direction}", (48, 48))
    if player_sprite:
        screen.blit(player_sprite, player_sprite.get_rect(center=(px + 16, py + 9)))
    else:
        pygame.draw.circle(screen, (255, 238, 125), (px + 16, py + 16), 12)
        pygame.draw.circle(screen, BG, (px + 16, py + 16), 12, 2)
    screen.set_clip(previous_clip)

    pygame.draw.rect(screen, PANEL, pygame.Rect(840, 70, 260, 576), border_radius=10)
    draw_text(screen, game.map_data["display_name"], (855, 85), 23, ACCENT, True)
    draw_text(screen, f"座標 {game.player_x}, {game.player_y}", (855, 118), 16, MUTED)
    draw_text(screen, "パーティ", (855, 155), 20, MUTED, True)
    party = game.party()
    for index in range(4):
        rect = pygame.Rect(852, 185 + index * 67, 235, 58)
        pygame.draw.rect(screen, (55, 94, 122) if index == game.selected_party else PANEL_ALT, rect, border_radius=7)
        if index < len(party):
            record = party[index]
            icon = game.character_image(record.species_id, "portrait", (30, 30))
            if icon:
                screen.blit(icon, icon.get_rect(center=(872, rect.centery)))
            else:
                definition = game.repository.get_species(record.species_id).definition
                color = _hex_color(definition["appearance"]["value"])
                pygame.draw.circle(screen, color, (872, rect.centery), 13)
            draw_text(screen, record.name, (893, rect.y + 8), 17)
            draw_text(screen, f"Lv{record.level} / {record.ai.get('tactic', 'balanced')}", (893, rect.y + 31), 13, MUTED)
        else:
            draw_text(screen, f"{index + 1}. 空き", (868, rect.y + 18), 16, MUTED)
    draw_text(screen, "操作", (855, 475), 19, MUTED, True)
    controls = (
        "Space 調べる／岩に入る\n"
        "L ものを拾う / 1-4 個体選択\n"
        "T 行動指針 / R AIリセット\n"
        "F5 個体獲得 / F6 模擬戦\n"
        "F7 編成保存 / F8 編成読込\n"
        "管理は街のモンスター牧場で行う"
    )
    for line_index, line in enumerate(controls.splitlines()):
        draw_text(screen, line, (855, 505 + line_index * 20), 13, MUTED)
