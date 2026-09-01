from __future__ import annotations

import pygame

from kadoka_quest.data.repository import GameRepository
from kadoka_quest.paths import ASSET_ROOT
from kadoka_quest.ui.common import (
    ACCENT, BAD, BG, GOOD, MUTED, PANEL, PANEL_ALT, SELECTED, TEXT,
    Button, ScrollBar, TextField, draw_status_bar, draw_text, handle_fields,
    init_pygame, smoke_frames,
)
from kadoka_quest.ui.pixel_editor import PixelArtEditor


PIXEL_CANVAS = pygame.Rect(300, 170, 448, 448)
PALETTE_ORIGIN = (790, 205)
PALETTE_COLUMNS = 4
PALETTE_SWATCH_SIZE = (60, 36)
TOOL_RECTS = {
    "pen": pygame.Rect(790, 115, 60, 40),
    "fill": pygame.Rect(858, 115, 70, 40),
    "pan": pygame.Rect(936, 115, 70, 40),
}
TOOL_LABELS = {"pen": "ペン", "fill": "塗る", "pan": "移動"}
UNDO_RECT = pygame.Rect(1014, 115, 61, 40)


class BlockEditor:
    def __init__(self) -> None:
        self.repository = GameRepository()
        self.blocks: list[dict] = []
        self.selected = 0
        self.list_offset = 0
        self.visual_mode = False
        self.status = "左からブロックを選び、ゲームが読むJSONを直接編集します。"
        self.id_field = TextField(pygame.Rect(350, 130, 260, 42))
        self.name_field = TextField(pygame.Rect(650, 130, 280, 42))
        self.appearance_field = TextField(pygame.Rect(350, 235, 580, 42))
        self.palette_color_field = TextField(pygame.Rect(790, 420, 130, 38), "#808080")
        self.image_path_field = TextField(pygame.Rect(210, 690, 305, 42))
        self.color_tolerance_field = TextField(pygame.Rect(525, 690, 60, 42), "24", numeric=True)
        self.appearance_type = "color"
        self.flags = {
            "player_walkable": True,
            "enemy_spawnable": True,
            "enemy_walkable": True,
        }
        self.visuals = PixelArtEditor(ASSET_ROOT)
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
            "id": f"new_block_{index}", "display_name": "新しいブロック",
            "player_walkable": True, "enemy_spawnable": False, "enemy_walkable": True,
            "appearance": {"type": "color", "value": "#808080"},
        })
        self.status = "新規ブロック。保存すると data/blocks に追加されます。"

    def payload(self) -> dict:
        return {
            "schema_version": 1,
            "id": self.id_field.value.strip(),
            "display_name": self.name_field.value.strip() or self.id_field.value.strip(),
            **self.flags,
            "appearance": {"type": self.appearance_type, "value": self.appearance_field.value.strip()},
        }

    def save(self) -> None:
        block = self.payload()
        try:
            self.repository.save_block(block)
            self.status = f"{block['id']}.json を保存しました。"
            self.refresh()
            self.selected = next((i for i, item in enumerate(self.blocks) if item["id"] == block["id"]), 0)
        except (OSError, ValueError, KeyError) as exc:
            self.status = f"保存できません: {exc}"

    @staticmethod
    def _color(value: str) -> tuple[int, int, int]:
        try:
            color = pygame.Color(value)
            return color.r, color.g, color.b
        except ValueError:
            return 128, 128, 128

    def open_visual_editor(self) -> None:
        block_id = self.id_field.value.strip() or "new_block"
        current_color = self._color(self.appearance_field.value) if self.appearance_type == "color" else (128, 128, 128)
        relative = self.appearance_field.value.strip() if self.appearance_type == "path" else f"appearance/blocks/{block_id}.png"
        if not relative.lower().endswith(".png"):
            relative = f"appearance/blocks/{block_id}.png"
        self.appearance_type = "path"
        self.appearance_field.value = relative
        self.visuals.load_block(relative, current_color)
        self.visual_mode = True
        self.status = "モンスターエディタと同じドットエディターでブロック画像を編集しています。"

    def save_visual(self) -> None:
        self.visuals.save_images()
        self.appearance_type = "path"
        self.appearance_field.value = self.visuals.paths["appearance"]
        self.save()
        self.status = f"64×64 PNG と {self.id_field.value}.json を保存しました。"

    def add_palette_color(self) -> None:
        try:
            color = self.visuals.add_palette_color(self.palette_color_field.value)
        except ValueError as error:
            self.status = str(error)
            return
        self.palette_color_field.value = self.visuals.color_to_hex(color)
        self.status = f"ペン色 {self.palette_color_field.value} を選択しました。"

    def remove_palette_color(self) -> None:
        removed = self.visuals.brush
        if not self.visuals.remove_palette_color():
            self.status = "透明色と最後のペン色は削除できません。"
            return
        self.palette_color_field.value = self.visuals.color_to_hex(self.visuals.brush)
        self.status = f"ペン色 {self.visuals.color_to_hex(removed)} を削除しました。"

    def import_visual_image(self) -> None:
        try:
            tolerance = self.visuals.parse_tolerance(self.color_tolerance_field.value)
            changed = self.visuals.import_image(self.image_path_field.value, tolerance)
        except ValueError as error:
            self.status = str(error)
            return
        self.status = f"画像を64×64内へ読み込み、近似色を{changed}ピクセル統合しました。"

    def merge_visual_colors(self) -> None:
        try:
            tolerance = self.visuals.parse_tolerance(self.color_tolerance_field.value)
        except ValueError as error:
            self.status = str(error)
            return
        changed = self.visuals.merge_similar_colors(tolerance)
        self.status = f"近似色を{changed}ピクセル統合しました。"

    def scroll_list(self, amount: int) -> None:
        self.list_offset = max(0, min(max(0, len(self.blocks) - 10), self.list_offset + amount))


def draw_visual_editor(screen: pygame.Surface, editor: BlockEditor) -> None:
    draw_text(screen, f"ブロック見た目編集：{editor.name_field.value}", (28, 25), 32, ACCENT, True)
    draw_text(screen, "ペン・塗りつぶし: 左着色/右透明 / 表示移動: ドラッグ / Ctrl+Z", (430, 37), 16, MUTED)
    editor.visuals.draw_canvas(screen, PIXEL_CANVAS)
    for mode, rect in TOOL_RECTS.items():
        pygame.draw.rect(screen, SELECTED if editor.visuals.tool_mode == mode else PANEL_ALT, rect, border_radius=6)
        draw_text(screen, TOOL_LABELS[mode], (rect.x + 12, rect.y + 11), 14, TEXT, True)
    pygame.draw.rect(screen, PANEL_ALT, UNDO_RECT, border_radius=6)
    draw_text(screen, "戻す", (UNDO_RECT.x + 17, UNDO_RECT.y + 11), 15, TEXT, True)
    draw_text(screen, f"色  {len(editor.visuals.palette)}/16", (790, 175), 21, MUTED, True)
    for color, rect in editor.visuals.palette_rects(PALETTE_ORIGIN, PALETTE_COLUMNS, PALETTE_SWATCH_SIZE):
        if color[3] == 0:
            PixelArtEditor.draw_checker(screen, rect, 9)
            draw_text(screen, "透明", (rect.x + 18, rect.y + 14), 14, BG, True)
        else:
            pygame.draw.rect(screen, color, rect, border_radius=5)
        pygame.draw.rect(screen, ACCENT if color == editor.visuals.brush else MUTED, rect, 3, border_radius=5)
    editor.palette_color_field.draw(screen, "追加する色")
    draw_text(screen, f"64×64px / 表示 {editor.visuals.zoom_percent}%", (790, 550), 17, ACCENT, True)
    draw_text(screen, "保存先", (790, 582), 15, MUTED, True)
    draw_text(screen, editor.appearance_field.value, (790, 607), 13, TEXT)
    editor.image_path_field.draw(screen, "読み込む画像パス")
    editor.color_tolerance_field.draw(screen, "色差")


def main() -> None:
    screen = init_pygame("kadoka quest - ブロックエディタ", (1100, 760))
    clock = pygame.time.Clock()
    editor = BlockEditor()
    running = True
    frames = 0
    smoke = smoke_frames()

    buttons = [
        Button(pygame.Rect(350, 305, 180, 45), "見た目: 色/パス", lambda: setattr(editor, "appearance_type", "path" if editor.appearance_type == "color" else "color")),
        Button(pygame.Rect(550, 305, 180, 45), "ドット絵編集", editor.open_visual_editor),
        Button(pygame.Rect(350, 445, 180, 48), "新規", editor.new),
        Button(pygame.Rect(550, 445, 180, 48), "保存", editor.save),
    ]
    visual_buttons = [
        Button(pygame.Rect(30, 685, 170, 45), "設定画面へ戻る", lambda: setattr(editor, "visual_mode", False)),
        Button(pygame.Rect(760, 685, 55, 45), "－", editor.visuals.zoom_out),
        Button(pygame.Rect(825, 685, 75, 45), "等倍", editor.visuals.reset_zoom),
        Button(pygame.Rect(910, 685, 55, 45), "＋", editor.visuals.zoom_in),
        Button(pygame.Rect(975, 685, 100, 45), "保存", editor.save_visual),
        Button(pygame.Rect(930, 420, 65, 38), "色追加", editor.add_palette_color),
        Button(pygame.Rect(1005, 420, 70, 38), "削除", editor.remove_palette_color),
        Button(pygame.Rect(595, 690, 80, 45), "画像読込", editor.import_visual_image),
        Button(pygame.Rect(682, 690, 68, 45), "色統合", editor.merge_visual_colors),
    ]
    flag_rects = {
        "player_walkable": pygame.Rect(350, 380, 175, 42),
        "enemy_spawnable": pygame.Rect(540, 380, 175, 42),
        "enemy_walkable": pygame.Rect(730, 380, 175, 42),
    }
    flag_labels = {"player_walkable": "自機が移動可能", "enemy_spawnable": "敵が湧く", "enemy_walkable": "敵が移動可能"}
    list_scroll = ScrollBar(pygame.Rect(292, 125, 8, 480), total=len(editor.blocks), page=10)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if editor.visual_mode:
                    editor.visual_mode = False
                else:
                    running = False
            if editor.visual_mode:
                handled = handle_fields(
                    [editor.palette_color_field, editor.image_path_field, editor.color_tolerance_field],
                    event,
                )
                handled = any(button.handle(event) for button in visual_buttons) or handled
                if event.type == pygame.KEYDOWN and event.key == pygame.K_z and event.mod & pygame.KMOD_CTRL:
                    editor.visuals.undo()
                    handled = True
                if event.type == pygame.MOUSEWHEEL and PIXEL_CANVAS.collidepoint(pygame.mouse.get_pos()):
                    editor.visuals.zoom_in() if event.y > 0 else editor.visuals.zoom_out()
                    handled = True
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for mode, rect in TOOL_RECTS.items():
                        if rect.collidepoint(event.pos):
                            editor.visuals.set_tool_mode(mode)
                            handled = True
                    if UNDO_RECT.collidepoint(event.pos):
                        editor.visuals.undo()
                        handled = True
                    for color, rect in editor.visuals.palette_rects(PALETTE_ORIGIN, PALETTE_COLUMNS, PALETTE_SWATCH_SIZE):
                        if rect.collidepoint(event.pos):
                            editor.visuals.brush = color
                            if color[3] > 0:
                                editor.palette_color_field.value = editor.visuals.color_to_hex(color)
                            handled = True
                if not handled and event.type == pygame.MOUSEBUTTONDOWN:
                    if editor.visuals.tool_mode == "pen" and event.button in {1, 3}:
                        editor.visuals.begin_stroke()
                        editor.visuals.paint(event.pos, PIXEL_CANVAS, erase=event.button == 3)
                    elif editor.visuals.tool_mode == "fill" and event.button in {1, 3}:
                        editor.visuals.fill(event.pos, PIXEL_CANVAS, erase=event.button == 3)
                    elif editor.visuals.tool_mode == "pan" and event.button == 1:
                        editor.visuals.begin_pan(event.pos, PIXEL_CANVAS)
                elif event.type == pygame.MOUSEMOTION:
                    if editor.visuals.tool_mode == "pen" and any(event.buttons):
                        editor.visuals.paint(event.pos, PIXEL_CANVAS, erase=bool(event.buttons[2]))
                    elif editor.visuals.tool_mode == "pan" and event.buttons[0]:
                        editor.visuals.pan_to(event.pos, PIXEL_CANVAS)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button in {1, 3}:
                        editor.visuals.end_stroke()
                    if event.button == 1:
                        editor.visuals.end_pan()
                continue
            if event.type == pygame.KEYDOWN and event.mod & pygame.KMOD_CTRL:
                if event.key == pygame.K_s:
                    editor.save()
                elif event.key == pygame.K_n:
                    editor.new()
            list_scroll.configure(len(editor.blocks), 10)
            list_scroll.value = editor.list_offset
            scroll_handled = list_scroll.handle(event)
            editor.list_offset = list_scroll.value
            handled = handle_fields([editor.id_field, editor.name_field, editor.appearance_field], event) or scroll_handled
            for button in buttons:
                handled = button.handle(event) or handled
            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if event.pos[0] < 305 and 125 <= event.pos[1] < 605:
                    index = editor.list_offset + (event.pos[1] - 125) // 48
                    if 0 <= index < len(editor.blocks):
                        editor.selected = index
                        editor.load(editor.blocks[index])
                for key, rect in flag_rects.items():
                    if rect.collidepoint(event.pos):
                        editor.flags[key] = not editor.flags[key]
            if event.type == pygame.MOUSEWHEEL and pygame.mouse.get_pos()[0] < 310:
                editor.scroll_list(-event.y)

        screen.fill(BG)
        if editor.visual_mode:
            draw_visual_editor(screen, editor)
            for button in visual_buttons:
                button.draw(screen, pygame.mouse.get_pos())
            pygame.display.flip()
            clock.tick(60)
            frames += 1
            if smoke is not None and frames >= smoke:
                running = False
            continue

        draw_text(screen, "ブロックエディタ", (35, 25), 36, ACCENT, True)
        draw_text(screen, "通行・出現・見た目を1ファイルで定義", (350, 72), 19, MUTED)
        draw_text(screen, "Ctrl+N 新規 / Ctrl+S 保存 / Esc 終了", (680, 32), 15, MUTED)
        pygame.draw.rect(screen, PANEL, pygame.Rect(25, 90, 285, 570), border_radius=10)
        draw_text(screen, f"ブロック一覧  {len(editor.blocks)}件", (40, 96), 15, MUTED, True)
        for row, block in enumerate(editor.blocks[editor.list_offset:editor.list_offset + 10]):
            index = editor.list_offset + row
            rect = pygame.Rect(38, 125 + row * 48, 246, 40)
            pygame.draw.rect(screen, SELECTED if index == editor.selected else PANEL_ALT, rect, border_radius=6)
            appearance = block.get("appearance", {})
            swatch = editor._color(str(appearance.get("value", "#808080"))) if appearance.get("type") == "color" else (110, 95, 125)
            pygame.draw.rect(screen, swatch, pygame.Rect(rect.x + 8, rect.y + 8, 24, 24), border_radius=4)
            draw_text(screen, block.get("display_name", block.get("id")), (rect.x + 42, rect.y + 5), 17)
            draw_text(screen, block.get("id", ""), (rect.x + 42, rect.y + 24), 11, MUTED)
        list_scroll.configure(len(editor.blocks), 10)
        list_scroll.value = editor.list_offset
        if list_scroll.maximum:
            list_scroll.draw(screen, pygame.mouse.get_pos())

        pygame.draw.rect(screen, PANEL, pygame.Rect(330, 90, 745, 570), border_radius=10)
        editor.id_field.draw(screen, "ID（半角英小文字）")
        editor.name_field.draw(screen, "表示名")
        editor.appearance_field.draw(screen, f"見た目の値（{editor.appearance_type}）")
        draw_text(screen, "地形ルール", (350, 350), 17, MUTED, True)
        for key, rect in flag_rects.items():
            pygame.draw.rect(screen, GOOD if editor.flags[key] else BAD, rect, border_radius=7)
            draw_text(screen, f"{'ON' if editor.flags[key] else 'OFF'}  {flag_labels[key]}", (rect.x + 9, rect.y + 10), 15, BG, True)
        for button in buttons:
            button.draw(screen, pygame.mouse.get_pos())
        draw_status_bar(screen, editor.status, pygame.Rect(350, 575, 680, 55), warning=editor.status.startswith("保存できません"))
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()
