from __future__ import annotations

import copy

import pygame

from kadoka_quest.data.repository import GameRepository, STAT_KEYS
from kadoka_quest.paths import ASSET_ROOT
from kadoka_quest.ui.common import ACCENT, BAD, BG, GOOD, MUTED, PANEL, PANEL_ALT, TEXT, WARN, Button, TextField, draw_text, draw_wrapped, init_pygame, smoke_frames
from kadoka_quest.ui.pixel_editor import PALETTE, VISUAL_SLOTS, PixelArtEditor


STAT_LABELS = {"attack": "攻撃", "defense": "防御", "speed": "素早さ", "magic": "魔法", "hp": "HP", "mp": "MP"}
AI_PROFILES = ("normal", "support", "trickster", "dice", "maru", "kadoka")
PIXEL_CANVAS = pygame.Rect(390, 275, 384, 384)
PREVIEW_RECTS = {slot: pygame.Rect(330 + index * 165, 105, 145, 130) for index, (slot, _, _) in enumerate(VISUAL_SLOTS)}
PALETTE_RECTS = {color: pygame.Rect(835 + (index % 2) * 88, 320 + (index // 2) * 58, 70, 45) for index, color in enumerate(PALETTE)}


class MonsterEditor:
    def __init__(self) -> None:
        self.repository = GameRepository()
        self.species_ids = self.repository.list_species_ids()
        self.selected = 0
        self.level = 1
        self.definition: dict = {}
        self.stats_payload: dict = {}
        self.skills_payload: dict = {}
        self.plus_payload: dict = {}
        self.id_field = TextField(pygame.Rect(945, 130, 190, 42))
        self.name_field = TextField(pygame.Rect(350, 130, 300, 42))
        self.color_field = TextField(pygame.Rect(690, 130, 230, 42))
        self.stat_fields = {
            key: TextField(pygame.Rect(350 + (index % 3) * 190, 270 + (index // 3) * 78, 160, 42), numeric=True)
            for index, key in enumerate(STAT_KEYS)
        }
        self.skill_level = TextField(pygame.Rect(350, 500, 100, 42), "1", numeric=True)
        self.skill_id = TextField(pygame.Rect(475, 500, 280, 42), "attack")
        self.status = "種族定義・Lv別能力・習得スキルをゲーム用JSONへ直接保存します。"
        self.visual_mode = False
        self.visuals = PixelArtEditor(ASSET_ROOT)
        self.load_selected()

    @property
    def species_id(self) -> str:
        return self.species_ids[self.selected]

    def load_selected(self) -> None:
        bundle = self.repository.get_species(self.species_id)
        self.definition = copy.deepcopy(bundle.definition)
        self.stats_payload = copy.deepcopy(bundle.stats)
        self.skills_payload = copy.deepcopy(bundle.skills)
        self.plus_payload = copy.deepcopy(bundle.plus)
        self.id_field.value = self.species_id
        self.name_field.value = str(self.definition.get("display_name", self.species_id))
        self.color_field.value = str(self.definition.get("appearance", {}).get("value", "#808080"))
        self.level = 1
        self.load_level_fields()
        self.visuals.load_species(self.definition, self.species_id)

    def store_level_fields(self) -> None:
        level_stats = self.stats_payload["levels"][str(self.level)]
        for key, field in self.stat_fields.items():
            try:
                level_stats[key] = max(1, int(field.value))
            except ValueError:
                pass

    def load_level_fields(self) -> None:
        level_stats = self.stats_payload["levels"][str(self.level)]
        for key, field in self.stat_fields.items():
            field.value = str(level_stats[key])

    def change_level(self, amount: int) -> None:
        self.store_level_fields()
        self.level = max(1, min(100, self.level + amount))
        self.load_level_fields()

    def cycle_ai(self) -> None:
        current = str(self.definition.get("ai_profile", "normal"))
        index = AI_PROFILES.index(current) if current in AI_PROFILES else 0
        self.definition["ai_profile"] = AI_PROFILES[(index + 1) % len(AI_PROFILES)]

    def toggle_equipment(self, category: str) -> None:
        values = list(self.definition.get("equipment_categories", []))
        if category in values:
            values.remove(category)
        else:
            values.append(category)
        self.definition["equipment_categories"] = values

    def add_skill(self) -> None:
        try:
            level = max(1, min(100, int(self.skill_level.value)))
        except ValueError:
            self.status = "習得レベルは1〜100の数字にしてください。"
            return
        skill_id = self.skill_id.value.strip()
        if skill_id not in self.repository.get_skills():
            self.status = f"skills.json に {skill_id} がありません。"
            return
        entry = {"level": level, "skill_id": skill_id}
        learnset = self.skills_payload.setdefault("learnset", [])
        if entry not in learnset:
            learnset.append(entry)
            learnset.sort(key=lambda item: (int(item["level"]), str(item["skill_id"])))
        self.status = f"Lv{level}: {skill_id} を追加しました。保存で確定します。"

    def save(self) -> None:
        self.store_level_fields()
        new_id = self.id_field.value.strip()
        if not new_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in new_id):
            self.status = "IDは半角英小文字・数字・_・-だけで指定してください。"
            return
        old_id = self.species_id
        self.definition["id"] = new_id
        self.definition["display_name"] = self.name_field.value.strip() or new_id
        self.definition.setdefault("appearance", {"type": "color"})["value"] = self.color_field.value.strip()
        self.repository.save_species_definition(self.definition)
        if new_id != old_id:
            source = old_id + "_plus_"
            replacement = new_id + "_plus_"
            for stage in self.plus_payload.get("stages", []):
                for option in stage.get("options", []):
                    option["id"] = str(option.get("id", "")).replace(source, replacement)
                    option["requires_any"] = [str(value).replace(source, replacement) for value in option.get("requires_any", [])]
        self.repository.save_species_stats(new_id, self.stats_payload)
        self.repository.save_species_skills(new_id, self.skills_payload)
        self.repository.save_species_plus(new_id, self.plus_payload)
        self.species_ids = self.repository.list_species_ids()
        self.selected = self.species_ids.index(new_id)
        self.status = f"{new_id} の4ファイルを保存しました。IDを変えた場合は新種族として追加されます。"

    def save_visuals(self) -> None:
        self.visuals.save_all(self.definition)
        self.repository.save_species_definition(self.definition)
        self.status = "戦闘立ち絵と前後左右のドット絵を保存しました。"


def draw_checker(screen: pygame.Surface, rect: pygame.Rect, cell: int = 8) -> None:
    for y in range(rect.y, rect.bottom, cell):
        for x in range(rect.x, rect.right, cell):
            color = (205, 205, 205) if ((x - rect.x) // cell + (y - rect.y) // cell) % 2 == 0 else (150, 150, 150)
            pygame.draw.rect(screen, color, pygame.Rect(x, y, min(cell, rect.right - x), min(cell, rect.bottom - y)))


def draw_visual_editor(screen: pygame.Surface, editor: MonsterEditor) -> None:
    draw_text(screen, f"見た目編集：{editor.definition.get('display_name', editor.species_id)}", (25, 22), 32, ACCENT, True)
    draw_text(screen, "上の5種類を選択して編集します。左クリック: 描く / 右クリック: 透明", (515, 32), 16, MUTED)
    mouse = pygame.mouse.get_pos()
    for slot, label, _ in VISUAL_SLOTS:
        rect = PREVIEW_RECTS[slot]
        pygame.draw.rect(screen, (55, 94, 122) if slot == editor.visuals.selected else PANEL, rect, border_radius=8)
        draw_checker(screen, pygame.Rect(rect.x + 38, rect.y + 27, 70, 70), 7)
        preview = pygame.transform.scale(editor.visuals.images[slot], (70, 70))
        screen.blit(preview, (rect.x + 38, rect.y + 27))
        draw_text(screen, label, (rect.x + 38, rect.y + 103), 16, TEXT, True)
        if slot in editor.visuals.dirty:
            draw_text(screen, "*", (rect.right - 20, rect.y + 7), 18, WARN, True)

    pygame.draw.rect(screen, PANEL, PIXEL_CANVAS.inflate(20, 20), border_radius=8)
    draw_checker(screen, PIXEL_CANVAS, 12)
    image = editor.visuals.images[editor.visuals.selected]
    size = image.get_width()
    cell = PIXEL_CANVAS.width / size
    for y in range(size):
        for x in range(size):
            color = image.get_at((x, y))
            if color.a:
                left = round(PIXEL_CANVAS.x + x * cell)
                top = round(PIXEL_CANVAS.y + y * cell)
                right = round(PIXEL_CANVAS.x + (x + 1) * cell)
                bottom = round(PIXEL_CANVAS.y + (y + 1) * cell)
                pygame.draw.rect(screen, color, pygame.Rect(left, top, right - left, bottom - top))
    grid_color = (72, 78, 88)
    for index in range(size + 1):
        x = round(PIXEL_CANVAS.x + index * cell)
        y = round(PIXEL_CANVAS.y + index * cell)
        pygame.draw.line(screen, grid_color, (x, PIXEL_CANVAS.y), (x, PIXEL_CANVAS.bottom), 1)
        pygame.draw.line(screen, grid_color, (PIXEL_CANVAS.x, y), (PIXEL_CANVAS.right, y), 1)

    draw_text(screen, "色", (835, 278), 22, MUTED, True)
    for color, rect in PALETTE_RECTS.items():
        if color[3] == 0:
            draw_checker(screen, rect, 9)
            draw_text(screen, "透明", (rect.x + 14, rect.y + 12), 14, BG, True)
        else:
            pygame.draw.rect(screen, color, rect, border_radius=5)
        pygame.draw.rect(screen, ACCENT if color == editor.visuals.brush else MUTED, rect, 3, border_radius=5)
    draw_text(screen, "画像はPNGとして保存され、ゲームへすぐ反映されます。", (805, 630), 15, MUTED)


def main() -> None:
    screen = init_pygame("kadoka quest - モンスターエディタ", (1200, 760))
    clock = pygame.time.Clock()
    editor = MonsterEditor()
    running = True
    smoke = smoke_frames()
    frames = 0
    buttons = [
        Button(pygame.Rect(350, 210, 70, 40), "-10", lambda: editor.change_level(-10)),
        Button(pygame.Rect(430, 210, 60, 40), "-1", lambda: editor.change_level(-1)),
        Button(pygame.Rect(580, 210, 60, 40), "+1", lambda: editor.change_level(1)),
        Button(pygame.Rect(650, 210, 70, 40), "+10", lambda: editor.change_level(10)),
        Button(pygame.Rect(350, 575, 180, 42), "AIプロファイル切替", editor.cycle_ai),
        Button(pygame.Rect(780, 500, 150, 42), "スキル追加", editor.add_skill),
        Button(pygame.Rect(350, 645, 180, 48), "保存", editor.save),
        Button(pygame.Rect(545, 645, 180, 48), "見た目編集", lambda: setattr(editor, "visual_mode", True)),
    ]
    visual_buttons = [
        Button(pygame.Rect(25, 690, 150, 45), "能力編集へ戻る", lambda: setattr(editor, "visual_mode", False)),
        Button(pygame.Rect(970, 690, 190, 45), "5種類を保存", editor.save_visuals),
    ]
    equipment_rects = {category: pygame.Rect(760 + index * 120, 210, 105, 40) for index, category in enumerate(("sword", "clothes", "staff"))}

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if editor.visual_mode:
                        editor.visual_mode = False
                    else:
                        running = False
                elif event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL:
                    editor.save_visuals() if editor.visual_mode else editor.save()
            if editor.visual_mode:
                handled = False
                for button in visual_buttons:
                    handled = button.handle(event) or handled
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        for slot, rect in PREVIEW_RECTS.items():
                            if rect.collidepoint(event.pos):
                                editor.visuals.select(slot)
                                handled = True
                        for color, rect in PALETTE_RECTS.items():
                            if rect.collidepoint(event.pos):
                                editor.visuals.brush = color
                                handled = True
                    if not handled and event.button in {1, 3}:
                        editor.visuals.paint(event.pos, PIXEL_CANVAS, erase=event.button == 3)
                elif event.type == pygame.MOUSEMOTION and any(event.buttons):
                    editor.visuals.paint(event.pos, PIXEL_CANVAS, erase=bool(event.buttons[2]))
                continue
            handled = editor.id_field.handle(event) or editor.name_field.handle(event) or editor.color_field.handle(event)
            handled = editor.skill_level.handle(event) or editor.skill_id.handle(event) or handled
            for field in editor.stat_fields.values():
                handled = field.handle(event) or handled
            for button in buttons:
                handled = button.handle(event) or handled
            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if event.pos[0] < 290 and 100 <= event.pos[1] < 100 + len(editor.species_ids) * 52:
                    index = (event.pos[1] - 100) // 52
                    if 0 <= index < len(editor.species_ids):
                        editor.store_level_fields()
                        editor.selected = index
                        editor.load_selected()
                for category, rect in equipment_rects.items():
                    if rect.collidepoint(event.pos):
                        editor.toggle_equipment(category)

        screen.fill(BG)
        if editor.visual_mode:
            draw_visual_editor(screen, editor)
            for button in visual_buttons:
                button.draw(screen, pygame.mouse.get_pos())
            pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(195, 690, 755, 45), border_radius=6)
            draw_wrapped(screen, editor.status, pygame.Rect(210, 698, 725, 30), 15)
            pygame.display.flip()
            clock.tick(60)
            frames += 1
            if smoke is not None and frames >= smoke:
                running = False
            continue
        draw_text(screen, "モンスターエディタ", (25, 25), 36, ACCENT, True)
        pygame.draw.rect(screen, PANEL, pygame.Rect(20, 85, 280, 630), border_radius=10)
        for index, species_id in enumerate(editor.species_ids):
            bundle = editor.repository.get_species(species_id)
            rect = pygame.Rect(35, 100 + index * 52, 250, 44)
            pygame.draw.rect(screen, (55, 94, 122) if index == editor.selected else PANEL_ALT, rect, border_radius=6)
            draw_text(screen, bundle.definition.get("display_name", species_id), (48, rect.y + 11), 18)
            draw_text(screen, species_id, (175, rect.y + 14), 13, MUTED)

        pygame.draw.rect(screen, PANEL, pygame.Rect(320, 85, 855, 630), border_radius=10)
        draw_text(screen, "IDを変更して保存すると新種族", (350, 98), 16, MUTED)
        editor.id_field.draw(screen, "種族ID")
        editor.name_field.draw(screen, "種族名")
        editor.color_field.draw(screen, "プレースホルダー色")
        draw_text(screen, f"Lv {editor.level}", (505, 218), 24, ACCENT, True)
        for key, field in editor.stat_fields.items():
            field.draw(screen, STAT_LABELS[key])
        draw_text(screen, "装備可能カテゴリ", (760, 185), 18, MUTED)
        allowed = set(editor.definition.get("equipment_categories", []))
        for category, rect in equipment_rects.items():
            pygame.draw.rect(screen, GOOD if category in allowed else BAD, rect, border_radius=6)
            draw_text(screen, category, (rect.x + 12, rect.y + 10), 16, BG, True)
        editor.skill_level.draw(screen, "習得Lv")
        editor.skill_id.draw(screen, "スキルID")
        draw_text(screen, f"AI: {editor.definition.get('ai_profile', 'normal')}", (550, 586), 19, ACCENT)
        learned = [item for item in editor.skills_payload.get("learnset", []) if int(item["level"]) <= editor.level]
        draw_text(screen, "現在までの習得:", (760, 575), 17, MUTED)
        draw_wrapped(screen, ", ".join(item["skill_id"] for item in learned) or "なし", pygame.Rect(760, 603, 380, 55), 15)
        mouse = pygame.mouse.get_pos()
        for button in buttons:
            button.draw(screen, mouse)
        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(545, 655, 595, 45), border_radius=6)
        draw_wrapped(screen, editor.status, pygame.Rect(560, 663, 565, 32), 15)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()

