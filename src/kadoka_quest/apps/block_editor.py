from __future__ import annotations

import pygame

from kadoka_quest.data.repository import GameRepository
from kadoka_quest.ui.common import ACCENT, BAD, BG, GOOD, MUTED, PANEL, PANEL_ALT, Button, TextField, draw_text, draw_wrapped, init_pygame, smoke_frames


class BlockEditor:
    def __init__(self) -> None:
        self.repository = GameRepository()
        self.blocks: list[dict] = []
        self.selected = 0
        self.status = "左からブロックを選び、ゲームが読むJSONを直接編集します。"
        self.id_field = TextField(pygame.Rect(350, 130, 260, 42))
        self.name_field = TextField(pygame.Rect(650, 130, 280, 42))
        self.appearance_field = TextField(pygame.Rect(350, 235, 580, 42))
        self.appearance_type = "color"
        self.flags = {
            "player_walkable": True,
            "enemy_spawnable": True,
            "enemy_walkable": True,
        }
        self.refresh()

    def refresh(self) -> None:
        self.blocks = self.repository.list_blocks()
        if self.blocks:
            self.selected = max(0, min(self.selected, len(self.blocks) - 1))
            self.load(self.blocks[self.selected])

    def load(self, block: dict) -> None:
        self.id_field.value = str(block.get("id", ""))
        self.name_field.value = str(block.get("display_name", ""))
        appearance = block.get("appearance", {})
        self.appearance_type = str(appearance.get("type", "color"))
        self.appearance_field.value = str(appearance.get("value", "#808080"))
        for key in self.flags:
            self.flags[key] = bool(block.get(key, False))

    def new(self) -> None:
        index = 1
        existing = {str(block.get("id")) for block in self.blocks}
        while f"new_block_{index}" in existing:
            index += 1
        self.load({
            "id": f"new_block_{index}",
            "display_name": "新しいブロック",
            "player_walkable": True,
            "enemy_spawnable": False,
            "enemy_walkable": True,
            "appearance": {"type": "color", "value": "#808080"},
        })
        self.status = "新規ブロック。保存すると data/blocks に追加されます。"

    def save(self) -> None:
        block = {
            "schema_version": 1,
            "id": self.id_field.value.strip(),
            "display_name": self.name_field.value.strip() or self.id_field.value.strip(),
            **self.flags,
            "appearance": {"type": self.appearance_type, "value": self.appearance_field.value.strip()},
        }
        try:
            self.repository.save_block(block)
            self.status = f"{block['id']}.json を保存しました。"
            self.refresh()
            self.selected = next((i for i, item in enumerate(self.blocks) if item["id"] == block["id"]), 0)
        except (OSError, ValueError, KeyError) as exc:
            self.status = f"保存できません: {exc}"


def main() -> None:
    screen = init_pygame("kadoka quest - ブロックエディタ", (1000, 700))
    clock = pygame.time.Clock()
    editor = BlockEditor()
    running = True
    frames = 0
    smoke = smoke_frames()

    def toggle_flag(key: str) -> None:
        editor.flags[key] = not editor.flags[key]

    buttons = [
        Button(pygame.Rect(350, 305, 180, 45), "見た目: 色/パス", lambda: setattr(editor, "appearance_type", "path" if editor.appearance_type == "color" else "color")),
        Button(pygame.Rect(350, 445, 180, 48), "新規", editor.new),
        Button(pygame.Rect(550, 445, 180, 48), "保存", editor.save),
    ]
    flag_rects = {
        "player_walkable": pygame.Rect(350, 380, 175, 42),
        "enemy_spawnable": pygame.Rect(540, 380, 175, 42),
        "enemy_walkable": pygame.Rect(730, 380, 175, 42),
    }
    flag_labels = {"player_walkable": "自機が移動可能", "enemy_spawnable": "敵が湧く", "enemy_walkable": "敵が移動可能"}

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            handled = editor.id_field.handle(event) or editor.name_field.handle(event) or editor.appearance_field.handle(event)
            for button in buttons:
                handled = button.handle(event) or handled
            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if event.pos[0] < 305 and 105 <= event.pos[1] < 105 + len(editor.blocks) * 48:
                    index = (event.pos[1] - 105) // 48
                    if 0 <= index < len(editor.blocks):
                        editor.selected = index
                        editor.load(editor.blocks[index])
                for key, rect in flag_rects.items():
                    if rect.collidepoint(event.pos):
                        toggle_flag(key)

        screen.fill(BG)
        draw_text(screen, "ブロックエディタ", (35, 25), 36, ACCENT, True)
        draw_text(screen, "通行・出現・見た目を1ファイルで定義", (350, 72), 19, MUTED)
        pygame.draw.rect(screen, PANEL, pygame.Rect(25, 90, 285, 570), border_radius=10)
        for index, block in enumerate(editor.blocks):
            rect = pygame.Rect(38, 105 + index * 48, 260, 40)
            pygame.draw.rect(screen, (52, 82, 105) if index == editor.selected else PANEL_ALT, rect, border_radius=6)
            draw_text(screen, block.get("display_name", block.get("id")), (50, rect.y + 8), 19)

        pygame.draw.rect(screen, PANEL, pygame.Rect(330, 90, 645, 570), border_radius=10)
        editor.id_field.draw(screen, "ID（半角英小文字）")
        editor.name_field.draw(screen, "表示名")
        editor.appearance_field.draw(screen, f"見た目の値（{editor.appearance_type}）")
        for key, rect in flag_rects.items():
            pygame.draw.rect(screen, GOOD if editor.flags[key] else BAD, rect, border_radius=7)
            draw_text(screen, flag_labels[key], (rect.x + 10, rect.y + 10), 17, BG, True)
        mouse = pygame.mouse.get_pos()
        for button in buttons:
            button.draw(screen, mouse)
        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(350, 535, 580, 90), border_radius=8)
        draw_wrapped(screen, editor.status, pygame.Rect(368, 551, 545, 60), 18)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()


