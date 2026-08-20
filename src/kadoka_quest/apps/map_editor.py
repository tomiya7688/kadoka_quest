from __future__ import annotations

import pygame

from kadoka_quest.data.repository import GameRepository
from kadoka_quest.ui.common import ACCENT, BG, GOOD, MUTED, PANEL, PANEL_ALT, WARN, Button, draw_text, draw_wrapped, init_pygame, smoke_frames


TILE = 22
MAP_RECT = pygame.Rect(20, 85, 924, 616)


def hex_color(value: str) -> tuple[int, int, int]:
    try:
        value = value.lstrip("#")
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))
    except (TypeError, ValueError):
        return (120, 120, 120)


class MapEditor:
    def __init__(self) -> None:
        self.repository = GameRepository()
        self.map_ids = self.repository.list_maps()
        self.map_index = 0
        self.map_id = self.map_ids[self.map_index]
        self.map_data = self.repository.get_map(self.map_id)
        self.blocks = self.repository.list_blocks()
        self.block_by_id = {block["id"]: block for block in self.blocks}
        self.species_ids = self.repository.list_species_ids()
        self.selected_block = self.blocks[0]["id"]
        self.selected_species = 0
        self.camera_x = 0
        self.camera_y = 0
        self.status = "左クリックで配置。矢印キーでマップをスクロールします。"

    def save(self) -> None:
        self.repository.save_map(self.map_data)
        self.status = f"data/maps/{self.map_id}/map.json を保存しました。"

    def add_spawn(self) -> None:
        species_id = self.species_ids[self.selected_species]
        if species_id == "ball_slime":
            self.status = "ボールスライムは初期獲得専用なので出現表へ追加できません。"
            return
        if any(item.get("species_id") == species_id for item in self.map_data.get("spawns", [])):
            self.status = f"{species_id} は既に出現表へ入っています。"
            return
        self.map_data.setdefault("spawns", []).append({"species_id": species_id, "weight": 10, "min_level": 1, "max_level": 5})
        self.status = f"{species_id} を出現表へ追加しました（重み10）。"

    def remove_spawn(self) -> None:
        species_id = self.species_ids[self.selected_species]
        old = len(self.map_data.get("spawns", []))
        self.map_data["spawns"] = [item for item in self.map_data.get("spawns", []) if item.get("species_id") != species_id]
        self.status = f"{species_id} を出現表から削除しました。" if len(self.map_data["spawns"]) < old else "対象は出現表にありません。"

    def move_camera(self, dx: int, dy: int) -> None:
        visible_x = MAP_RECT.width // TILE
        visible_y = MAP_RECT.height // TILE
        self.camera_x = max(0, min(int(self.map_data["width"]) - visible_x, self.camera_x + dx))
        self.camera_y = max(0, min(int(self.map_data["height"]) - visible_y, self.camera_y + dy))

    def change_map(self, amount: int) -> None:
        self.map_index = (self.map_index + amount) % len(self.map_ids)
        self.map_id = self.map_ids[self.map_index]
        self.map_data = self.repository.get_map(self.map_id)
        self.camera_x = 0
        self.camera_y = 0
        self.status = f"{self.map_data['display_name']}を開きました。未保存の変更は切替前に保存してください。"


def main() -> None:
    screen = init_pygame("kadoka quest - マップエディタ", (1200, 760))
    clock = pygame.time.Clock()
    editor = MapEditor()
    running = True
    smoke = smoke_frames()
    frames = 0
    buttons = [
        Button(pygame.Rect(975, 625, 95, 42), "保存", editor.save),
        Button(pygame.Rect(1080, 625, 95, 42), "終了", lambda: None),
        Button(pygame.Rect(975, 550, 95, 38), "出現追加", editor.add_spawn),
        Button(pygame.Rect(1080, 550, 95, 38), "出現削除", editor.remove_spawn),
        Button(pygame.Rect(960, 20, 105, 38), "前の地図", lambda: editor.change_map(-1)),
        Button(pygame.Rect(1075, 20, 105, 38), "次の地図", lambda: editor.change_map(1)),
    ]

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_LEFT:
                    editor.move_camera(-3, 0)
                elif event.key == pygame.K_RIGHT:
                    editor.move_camera(3, 0)
                elif event.key == pygame.K_UP:
                    editor.move_camera(0, -3)
                elif event.key == pygame.K_DOWN:
                    editor.move_camera(0, 3)
                elif event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL:
                    editor.save()
                elif event.key == pygame.K_PAGEUP:
                    editor.change_map(-1)
                elif event.key == pygame.K_PAGEDOWN:
                    editor.change_map(1)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if MAP_RECT.collidepoint(event.pos):
                    grid_x = editor.camera_x + (event.pos[0] - MAP_RECT.x) // TILE
                    grid_y = editor.camera_y + (event.pos[1] - MAP_RECT.y) // TILE
                    if 0 <= grid_x < editor.map_data["width"] and 0 <= grid_y < editor.map_data["height"]:
                        editor.map_data["tiles"][grid_y][grid_x] = editor.selected_block
                        editor.status = f"({grid_x}, {grid_y}) に {editor.selected_block} を配置。"
                for index, block in enumerate(editor.blocks):
                    rect = pygame.Rect(970, 95 + index * 43, 205, 36)
                    if rect.collidepoint(event.pos):
                        editor.selected_block = block["id"]
                for index, species_id in enumerate(editor.species_ids):
                    rect = pygame.Rect(970, 382 + index * 24, 205, 22)
                    if rect.collidepoint(event.pos):
                        editor.selected_species = index
                if buttons[1].rect.collidepoint(event.pos):
                    running = False
                else:
                    for button in buttons:
                        button.handle(event)

        screen.fill(BG)
        draw_text(screen, f"マップエディタ：{editor.map_data['display_name']}", (22, 22), 34, ACCENT, True)
        draw_text(screen, f"表示原点 {editor.camera_x}, {editor.camera_y}", (690, 35), 18, MUTED)
        pygame.draw.rect(screen, PANEL, MAP_RECT.inflate(8, 8), border_radius=8)
        visible_x = MAP_RECT.width // TILE
        visible_y = MAP_RECT.height // TILE
        for screen_y in range(visible_y):
            grid_y = editor.camera_y + screen_y
            if grid_y >= editor.map_data["height"]:
                break
            for screen_x in range(visible_x):
                grid_x = editor.camera_x + screen_x
                if grid_x >= editor.map_data["width"]:
                    break
                block_id = editor.map_data["tiles"][grid_y][grid_x]
                block = editor.block_by_id.get(block_id, {})
                appearance = block.get("appearance", {})
                color = hex_color(appearance.get("value", "#777777")) if appearance.get("type") == "color" else (110, 95, 125)
                rect = pygame.Rect(MAP_RECT.x + screen_x * TILE, MAP_RECT.y + screen_y * TILE, TILE, TILE)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)
        for event_data in editor.map_data.get("events", []):
            sx = (int(event_data["x"]) - editor.camera_x) * TILE + MAP_RECT.x
            sy = (int(event_data["y"]) - editor.camera_y) * TILE + MAP_RECT.y
            if MAP_RECT.collidepoint((sx + 2, sy + 2)):
                pygame.draw.rect(screen, WARN, pygame.Rect(sx + 5, sy + 5, TILE - 10, TILE - 10), border_radius=3)

        pygame.draw.rect(screen, PANEL, pygame.Rect(960, 75, 225, 635), border_radius=10)
        draw_text(screen, "ブロック", (975, 78), 20, MUTED, True)
        for index, block in enumerate(editor.blocks):
            rect = pygame.Rect(970, 95 + index * 43, 205, 36)
            selected = block["id"] == editor.selected_block
            pygame.draw.rect(screen, (55, 94, 122) if selected else PANEL_ALT, rect, border_radius=6)
            appearance = block.get("appearance", {})
            swatch = hex_color(appearance.get("value", "#777777")) if appearance.get("type") == "color" else (110, 95, 125)
            pygame.draw.rect(screen, swatch, pygame.Rect(rect.x + 7, rect.y + 7, 22, 22), border_radius=3)
            draw_text(screen, block.get("display_name", block["id"]), (rect.x + 38, rect.y + 8), 17)

        draw_text(screen, "生息モンスター", (975, 352), 19, MUTED, True)
        active_spawns = {item.get("species_id") for item in editor.map_data.get("spawns", [])}
        for index, species_id in enumerate(editor.species_ids):
            rect = pygame.Rect(970, 382 + index * 24, 205, 22)
            if index == editor.selected_species:
                pygame.draw.rect(screen, (55, 94, 122), rect, border_radius=4)
            draw_text(screen, ("● " if species_id in active_spawns else "○ ") + species_id, (975, rect.y + 2), 15, GOOD if species_id in active_spawns else MUTED)

        mouse = pygame.mouse.get_pos()
        for button in buttons:
            button.draw(screen, mouse)
        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(25, 716, 1150, 34), border_radius=7)
        draw_wrapped(screen, editor.status, pygame.Rect(38, 722, 1125, 25), 16)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()

