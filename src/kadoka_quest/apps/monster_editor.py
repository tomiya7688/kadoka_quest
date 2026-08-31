from __future__ import annotations

import copy
from pathlib import Path

import pygame

from kadoka_quest.data.repository import GameRepository, STAT_KEYS
from kadoka_quest.data.species_creator import SpeciesCreator
from kadoka_quest.paths import ASSET_ROOT
from kadoka_quest.ui.common import ACCENT, BAD, BG, GOOD, MUTED, PANEL, PANEL_ALT, SELECTED, TEXT, WARN, Button, ScrollBar, TextField, draw_status_bar, draw_text, draw_wrapped, handle_fields, init_pygame, smoke_frames
from kadoka_quest.ui.pixel_editor import VISUAL_SLOTS, PixelArtEditor


STAT_LABELS = {"attack": "攻撃", "defense": "防御", "speed": "素早さ", "magic": "魔法", "hp": "HP", "mp": "MP"}
AI_PROFILES = ("normal", "support", "trickster", "dice", "maru", "kadoka")
SKILL_KIND_LABELS = {
    "physical": "物理",
    "magic": "魔法",
    "drain_mp": "MP吸収",
    "random": "ランダム",
    "heal": "回復",
    "defend": "防御",
    "evade": "回避",
    "buff": "強化",
    "field": "フィールド",
}
SKILL_ROWS = 9
PIXEL_CANVAS = pygame.Rect(390, 275, 384, 384)
PREVIEW_RECTS = {slot: pygame.Rect(330 + index * 165, 105, 145, 130) for index, (slot, _, _) in enumerate(VISUAL_SLOTS)}
PALETTE_ORIGIN = (805, 315)
PALETTE_COLUMNS = 4
PALETTE_SWATCH_SIZE = (70, 34)
TOOL_RECTS = {
    "pen": pygame.Rect(805, 250, 95, 38),
    "pan": pygame.Rect(910, 250, 105, 38),
}
UNDO_RECT = pygame.Rect(1025, 250, 125, 38)
NEW_SPECIES_ID = "__new_species__"


class MonsterEditor:
    def __init__(self, repository: GameRepository | None = None, asset_root: Path = ASSET_ROOT) -> None:
        self.repository = repository or GameRepository()
        self.asset_root = Path(asset_root)
        self.creator = SpeciesCreator(self.repository, self.asset_root)
        self.species_ids = [NEW_SPECIES_ID, *self.repository.list_species_ids()]
        self.selected = 1 if len(self.species_ids) > 1 else 0
        self.list_offset = 0
        self.level = 1
        self.definition: dict = {}
        self.stats_payload: dict = {}
        self.skills_payload: dict = {}
        self.plus_payload: dict = {}
        self.id_field = TextField(pygame.Rect(945, 130, 190, 42))
        self.name_field = TextField(pygame.Rect(350, 130, 300, 42))
        self.color_field = TextField(pygame.Rect(690, 130, 230, 42))
        self.palette_color_field = TextField(pygame.Rect(805, 525, 145, 38), "#808080")
        self.stat_fields = {
            key: TextField(pygame.Rect(350 + (index % 3) * 190, 270 + (index // 3) * 78, 160, 42), numeric=True)
            for index, key in enumerate(STAT_KEYS)
        }
        self.skill_level = TextField(pygame.Rect(350, 500, 100, 42), "1", numeric=True)
        self.skill_id = TextField(pygame.Rect(475, 500, 280, 42), "attack")
        self.available_skill_index = 0
        self.available_skill_offset = 0
        self.learned_skill_index = 0
        self.learned_skill_offset = 0
        self.status = "種族定義・Lv別能力・習得スキルをゲーム用JSONへ直接保存します。"
        self.visual_mode = False
        self.skill_mode = False
        self.visuals = PixelArtEditor(self.asset_root)
        self.load_selected()

    @property
    def species_id(self) -> str:
        return self.species_ids[self.selected]

    @property
    def creating_new(self) -> bool:
        return self.species_id == NEW_SPECIES_ID

    def load_selected(self) -> None:
        if self.creating_new:
            self.load_new_draft()
            return
        bundle = self.repository.get_species(self.species_id)
        self.definition = copy.deepcopy(bundle.definition)
        self.stats_payload = copy.deepcopy(bundle.stats)
        self.skills_payload = copy.deepcopy(bundle.skills)
        self.plus_payload = copy.deepcopy(bundle.plus)
        self.id_field.value = self.species_id
        self.name_field.value = str(self.definition.get("display_name", self.species_id))
        self.color_field.value = str(self.definition.get("appearance", {}).get("value", "#808080"))
        self.level = 1
        self.available_skill_index = 0
        self.available_skill_offset = 0
        self.learned_skill_index = 0
        self.learned_skill_offset = 0
        self.skill_id.value = next(iter(self.repository.get_skills()), "attack")
        self.load_level_fields()
        self.visuals.load_species(self.definition, self.species_id)

    def load_new_draft(self) -> None:
        self.definition, self.stats_payload, self.skills_payload, self.plus_payload = self.creator.build_draft()
        self.id_field.value = str(self.definition["id"])
        self.name_field.value = str(self.definition["display_name"])
        self.color_field.value = str(self.definition["appearance"]["value"])
        self.level = 1
        self.available_skill_index = 0
        self.available_skill_offset = 0
        self.learned_skill_index = 0
        self.learned_skill_offset = 0
        self.skill_id.value = next(iter(self.repository.get_skills()), "attack")
        self.load_level_fields()
        self.visuals.load_species(self.definition, str(self.definition["id"]))
        self.status = "新しい種族の編集中です。ID・名前・能力を決めて保存すると4つのJSONと画像5枚を作成します。"

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

    def cycle_skill(self, amount: int) -> None:
        skill_ids = list(self.repository.get_skills())
        if not skill_ids:
            return
        self.available_skill_index = (self.available_skill_index + amount) % len(skill_ids)
        self.skill_id.value = skill_ids[self.available_skill_index]
        self.available_skill_offset = max(0, min(self.available_skill_index, len(skill_ids) - SKILL_ROWS))

    def select_available_skill(self, index: int) -> None:
        skill_ids = list(self.repository.get_skills())
        if 0 <= index < len(skill_ids):
            self.available_skill_index = index
            self.skill_id.value = skill_ids[index]

    def remove_skill(self) -> None:
        learnset = self.skills_payload.setdefault("learnset", [])
        if not learnset:
            self.status = "削除する習得スキルがありません。"
            return
        self.learned_skill_index = max(0, min(self.learned_skill_index, len(learnset) - 1))
        removed = learnset.pop(self.learned_skill_index)
        self.learned_skill_index = max(0, min(self.learned_skill_index, len(learnset) - 1))
        self.status = f"Lv{removed['level']}: {removed['skill_id']} を習得表から外しました。保存で確定します。"

    def select_species(self, index: int) -> None:
        if 0 <= index < len(self.species_ids) and index != self.selected:
            self.store_level_fields()
            self.selected = index
            self.load_selected()

    def scroll_list(self, amount: int) -> None:
        self.list_offset = max(0, min(max(0, len(self.species_ids) - 10), self.list_offset + amount))

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
        learnset = self.skills_payload.setdefault("learnset", [])
        existing = next((item for item in learnset if item.get("skill_id") == skill_id), None)
        if existing:
            existing["level"] = level
            action = "習得レベルを変更"
        else:
            learnset.append({"level": level, "skill_id": skill_id})
            action = "追加"
        learnset.sort(key=lambda item: (int(item["level"]), str(item["skill_id"])))
        self.learned_skill_index = next(index for index, item in enumerate(learnset) if item.get("skill_id") == skill_id)
        self.learned_skill_offset = max(0, min(self.learned_skill_index, len(learnset) - SKILL_ROWS))
        self.status = f"Lv{level}: {skill_id} を{action}しました。保存で確定します。"

    def save(self) -> None:
        self.store_level_fields()
        was_creating = self.creating_new
        new_id = self.id_field.value.strip()
        if not new_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in new_id):
            self.status = "IDは半角英小文字・数字・_・-だけで指定してください。"
            return
        old_id = str(self.definition.get("id", self.species_id)) if was_creating else self.species_id
        self.definition["id"] = new_id
        self.definition["display_name"] = self.name_field.value.strip() or new_id
        self.definition.setdefault("appearance", {"type": "color"})["value"] = self.color_field.value.strip()
        if new_id != old_id:
            source = old_id + "_plus_"
            replacement = new_id + "_plus_"
            for stage in self.plus_payload.get("stages", []):
                for option in stage.get("options", []):
                    option["id"] = str(option.get("id", "")).replace(source, replacement)
                    option["requires_any"] = [str(value).replace(source, replacement) for value in option.get("requires_any", [])]
        if was_creating:
            try:
                self.creator.create(
                    self.definition,
                    self.stats_payload,
                    self.skills_payload,
                    self.plus_payload,
                )
            except ValueError as error:
                self.status = str(error)
                return
        else:
            self.repository.save_species_definition(self.definition)
            self.repository.save_species_stats(new_id, self.stats_payload)
            self.repository.save_species_skills(new_id, self.skills_payload)
            self.repository.save_species_plus(new_id, self.plus_payload)
        self.species_ids = [NEW_SPECIES_ID, *self.repository.list_species_ids()]
        self.selected = self.species_ids.index(new_id)
        self.visuals.load_species(self.definition, new_id)
        self.status = (
            f"{new_id} の4ファイルと64×64画像5枚を新規作成しました。"
            if was_creating
            else f"{new_id} の4ファイルを保存しました。"
        )

    def save_visuals(self) -> None:
        if self.creating_new:
            self.status = "新しい種族は先に能力編集画面の保存で作成してください。作成後に画像を保存できます。"
            return
        self.visuals.save_all(self.definition)
        self.repository.save_species_definition(self.definition)
        self.status = "戦闘立ち絵と前後左右のドット絵を保存しました。"

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


def draw_checker(screen: pygame.Surface, rect: pygame.Rect, cell: int = 8) -> None:
    PixelArtEditor.draw_checker(screen, rect, cell)


def draw_visual_editor(screen: pygame.Surface, editor: MonsterEditor) -> None:
    draw_text(screen, f"見た目編集：{editor.definition.get('display_name', editor.species_id)}", (25, 22), 32, ACCENT, True)
    draw_text(screen, "ペン: 左描画・右透明 / 表示移動: ドラッグ / Ctrl+Z: 元に戻す", (515, 32), 16, MUTED)
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

    editor.visuals.draw_canvas(screen, PIXEL_CANVAS)

    for mode, rect in TOOL_RECTS.items():
        pygame.draw.rect(screen, SELECTED if editor.visuals.tool_mode == mode else PANEL_ALT, rect, border_radius=6)
        draw_text(screen, "ペン" if mode == "pen" else "表示移動", (rect.x + 17, rect.y + 10), 15, TEXT, True)
    pygame.draw.rect(screen, PANEL_ALT, UNDO_RECT, border_radius=6)
    draw_text(screen, "元に戻す", (UNDO_RECT.x + 22, UNDO_RECT.y + 10), 15, TEXT, True)

    draw_text(screen, f"色  {len(editor.visuals.palette)}/16", (805, 292), 20, MUTED, True)
    for color, rect in editor.visuals.palette_rects(PALETTE_ORIGIN, PALETTE_COLUMNS, PALETTE_SWATCH_SIZE):
        if color[3] == 0:
            draw_checker(screen, rect, 9)
            draw_text(screen, "透明", (rect.x + 14, rect.y + 12), 14, BG, True)
        else:
            pygame.draw.rect(screen, color, rect, border_radius=5)
        pygame.draw.rect(screen, ACCENT if color == editor.visuals.brush else MUTED, rect, 3, border_radius=5)
    editor.palette_color_field.draw(screen, "追加する色")
    size = editor.visuals.logical_size
    draw_text(screen, f"表示倍率: {editor.visuals.zoom_percent}%", (805, 578), 15, WARN, True)
    draw_text(screen, f"編集中: {size}×{size}px（保存時もこの解像度）", (805, 600), 15, ACCENT, True)
    draw_text(screen, "画像はPNGとして保存され、ゲームへすぐ反映されます。", (805, 630), 15, MUTED)


def draw_skill_editor(
    screen: pygame.Surface,
    editor: MonsterEditor,
    available_scroll: ScrollBar,
    learned_scroll: ScrollBar,
) -> None:
    catalog = editor.repository.get_skills()
    skill_ids = list(catalog)
    learnset = editor.skills_payload.setdefault("learnset", [])
    display_name = editor.definition.get("display_name", editor.species_id)
    draw_text(screen, f"スキル編集：{display_name}", (25, 22), 34, ACCENT, True)
    draw_text(screen, "一覧から選んで追加します。IDを手入力する必要はありません。", (505, 38), 16, MUTED)

    left_panel = pygame.Rect(25, 85, 550, 570)
    right_panel = pygame.Rect(600, 85, 575, 570)
    pygame.draw.rect(screen, PANEL, left_panel, border_radius=10)
    pygame.draw.rect(screen, PANEL, right_panel, border_radius=10)
    draw_text(screen, f"全スキル  {len(skill_ids)}件", (42, 100), 20, MUTED, True)
    draw_text(screen, f"{display_name}の習得表  {len(learnset)}件", (618, 100), 20, MUTED, True)

    for row, skill_id in enumerate(skill_ids[editor.available_skill_offset:editor.available_skill_offset + SKILL_ROWS]):
        index = editor.available_skill_offset + row
        skill = catalog[skill_id]
        rect = pygame.Rect(40, 135 + row * 50, 510, 44)
        pygame.draw.rect(screen, SELECTED if index == editor.available_skill_index else PANEL_ALT, rect, border_radius=6)
        draw_text(screen, skill.get("display_name", skill_id), (rect.x + 10, rect.y + 4), 17, TEXT, True)
        kind = SKILL_KIND_LABELS.get(str(skill.get("kind", "")), str(skill.get("kind", "-")))
        details = f"{skill_id}  ｜  {kind}  ｜  威力 {skill.get('power', '-')}  ｜  MP {skill.get('mp_cost', 0)}"
        draw_text(screen, details, (rect.x + 10, rect.y + 25), 12, MUTED)

    for row, entry in enumerate(learnset[editor.learned_skill_offset:editor.learned_skill_offset + SKILL_ROWS]):
        index = editor.learned_skill_offset + row
        skill_id = str(entry.get("skill_id", ""))
        skill = catalog.get(skill_id, {})
        rect = pygame.Rect(615, 135 + row * 50, 535, 44)
        pygame.draw.rect(screen, SELECTED if index == editor.learned_skill_index else PANEL_ALT, rect, border_radius=6)
        draw_text(screen, f"Lv{int(entry.get('level', 1)):>3}  {skill.get('display_name', skill_id)}", (rect.x + 10, rect.y + 4), 17, TEXT, True)
        kind = SKILL_KIND_LABELS.get(str(skill.get("kind", "")), str(skill.get("kind", "不明")))
        draw_text(screen, f"{skill_id}  ｜  {kind}  ｜  MP {skill.get('mp_cost', 0)}", (rect.x + 10, rect.y + 25), 12, MUTED)

    available_scroll.configure(len(skill_ids), SKILL_ROWS)
    learned_scroll.configure(len(learnset), SKILL_ROWS)
    available_scroll.value = editor.available_skill_offset
    learned_scroll.value = editor.learned_skill_offset
    if available_scroll.maximum:
        available_scroll.draw(screen, pygame.mouse.get_pos())
    if learned_scroll.maximum:
        learned_scroll.draw(screen, pygame.mouse.get_pos())

    editor.skill_level.draw(screen, "選択したスキルの習得レベル")


def main() -> None:
    screen = init_pygame("kadoka quest - モンスターエディタ", (1200, 760))
    clock = pygame.time.Clock()
    editor = MonsterEditor()
    running = True
    smoke = smoke_frames()
    frames = 0
    editor.skill_level.rect = pygame.Rect(615, 605, 170, 42)
    buttons = [
        Button(pygame.Rect(350, 210, 70, 40), "-10", lambda: editor.change_level(-10)),
        Button(pygame.Rect(430, 210, 60, 40), "-1", lambda: editor.change_level(-1)),
        Button(pygame.Rect(580, 210, 60, 40), "+1", lambda: editor.change_level(1)),
        Button(pygame.Rect(650, 210, 70, 40), "+10", lambda: editor.change_level(10)),
        Button(pygame.Rect(350, 500, 180, 42), "AIプロファイル切替", editor.cycle_ai),
        Button(pygame.Rect(545, 500, 180, 42), "スキル編集", lambda: setattr(editor, "skill_mode", True)),
        Button(pygame.Rect(350, 645, 180, 48), "保存", editor.save),
        Button(pygame.Rect(545, 645, 180, 48), "見た目編集", lambda: setattr(editor, "visual_mode", True)),
    ]
    skill_buttons = [
        Button(pygame.Rect(25, 690, 155, 45), "能力編集へ戻る", lambda: setattr(editor, "skill_mode", False)),
        Button(pygame.Rect(800, 605, 170, 42), "選択スキルを追加", editor.add_skill),
        Button(pygame.Rect(985, 605, 165, 42), "習得表から削除", editor.remove_skill),
        Button(pygame.Rect(1020, 690, 155, 45), "全データを保存", editor.save),
    ]
    visual_buttons = [
        Button(pygame.Rect(25, 690, 150, 45), "能力編集へ戻る", lambda: setattr(editor, "visual_mode", False)),
        Button(pygame.Rect(790, 690, 50, 45), "－", editor.visuals.zoom_out),
        Button(pygame.Rect(845, 690, 65, 45), "等倍", editor.visuals.reset_zoom),
        Button(pygame.Rect(915, 690, 50, 45), "＋", editor.visuals.zoom_in),
        Button(pygame.Rect(970, 690, 190, 45), "5種類を保存", editor.save_visuals),
        Button(pygame.Rect(960, 525, 85, 38), "色追加", editor.add_palette_color),
        Button(pygame.Rect(1055, 525, 105, 38), "選択色削除", editor.remove_palette_color),
    ]
    species_scroll = ScrollBar(pygame.Rect(288, 120, 8, 540), total=len(editor.species_ids), page=10)
    available_scroll = ScrollBar(pygame.Rect(559, 135, 8, SKILL_ROWS * 50 - 6), total=len(editor.repository.get_skills()), page=SKILL_ROWS)
    learned_scroll = ScrollBar(pygame.Rect(1158, 135, 8, SKILL_ROWS * 50 - 6), total=0, page=SKILL_ROWS)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if editor.visual_mode:
                        editor.visual_mode = False
                    elif editor.skill_mode:
                        editor.skill_mode = False
                    else:
                        running = False
                elif event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL:
                    editor.save_visuals() if editor.visual_mode else editor.save()
                elif not editor.visual_mode and not editor.skill_mode and event.key == pygame.K_PAGEUP:
                    editor.change_level(-1)
                elif not editor.visual_mode and not editor.skill_mode and event.key == pygame.K_PAGEDOWN:
                    editor.change_level(1)
            if editor.skill_mode:
                skill_ids = list(editor.repository.get_skills())
                learnset = editor.skills_payload.setdefault("learnset", [])
                available_scroll.configure(len(skill_ids), SKILL_ROWS)
                learned_scroll.configure(len(learnset), SKILL_ROWS)
                available_scroll.value = editor.available_skill_offset
                learned_scroll.value = editor.learned_skill_offset
                handled = available_scroll.handle(event)
                handled = learned_scroll.handle(event) or handled
                editor.available_skill_offset = available_scroll.value
                editor.learned_skill_offset = learned_scroll.value
                handled = handle_fields([editor.skill_level], event) or handled
                for button in skill_buttons:
                    handled = button.handle(event) or handled
                if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if 40 <= event.pos[0] < 550 and 135 <= event.pos[1] < 135 + SKILL_ROWS * 50:
                        row = (event.pos[1] - 135) // 50
                        editor.select_available_skill(editor.available_skill_offset + row)
                    elif 615 <= event.pos[0] < 1150 and 135 <= event.pos[1] < 135 + SKILL_ROWS * 50:
                        row = (event.pos[1] - 135) // 50
                        index = editor.learned_skill_offset + row
                        if 0 <= index < len(learnset):
                            editor.learned_skill_index = index
                            editor.skill_level.value = str(learnset[index].get("level", 1))
                if event.type == pygame.MOUSEWHEEL:
                    mouse_x = pygame.mouse.get_pos()[0]
                    if mouse_x < 590:
                        editor.available_skill_offset = max(0, min(available_scroll.maximum, editor.available_skill_offset - event.y))
                    else:
                        editor.learned_skill_offset = max(0, min(learned_scroll.maximum, editor.learned_skill_offset - event.y))
                continue
            if editor.visual_mode:
                handled = handle_fields([editor.palette_color_field], event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_z and event.mod & pygame.KMOD_CTRL:
                    editor.visuals.undo()
                    handled = True
                for button in visual_buttons:
                    handled = button.handle(event) or handled
                if event.type == pygame.MOUSEWHEEL and PIXEL_CANVAS.collidepoint(pygame.mouse.get_pos()):
                    editor.visuals.zoom_in() if event.y > 0 else editor.visuals.zoom_out()
                    handled = True
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        for mode, rect in TOOL_RECTS.items():
                            if rect.collidepoint(event.pos):
                                editor.visuals.set_tool_mode(mode)
                                handled = True
                        if UNDO_RECT.collidepoint(event.pos):
                            editor.visuals.undo()
                            handled = True
                        for slot, rect in PREVIEW_RECTS.items():
                            if rect.collidepoint(event.pos):
                                editor.visuals.select(slot)
                                handled = True
                        for color, rect in editor.visuals.palette_rects(PALETTE_ORIGIN, PALETTE_COLUMNS, PALETTE_SWATCH_SIZE):
                            if rect.collidepoint(event.pos):
                                editor.visuals.brush = color
                                if color[3] > 0:
                                    editor.palette_color_field.value = editor.visuals.color_to_hex(color)
                                handled = True
                    if not handled and editor.visuals.tool_mode == "pen" and event.button in {1, 3}:
                        editor.visuals.begin_stroke()
                        editor.visuals.paint(event.pos, PIXEL_CANVAS, erase=event.button == 3)
                    elif not handled and editor.visuals.tool_mode == "pan" and event.button == 1:
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
            species_scroll.configure(len(editor.species_ids), 10)
            species_scroll.value = editor.list_offset
            scroll_handled = species_scroll.handle(event)
            editor.list_offset = species_scroll.value
            fields = [editor.id_field, editor.name_field, editor.color_field, *editor.stat_fields.values()]
            handled = handle_fields(fields, event) or scroll_handled
            for button in buttons:
                handled = button.handle(event) or handled
            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if event.pos[0] < 290 and 120 <= event.pos[1] < 120 + 10 * 54:
                    row = (event.pos[1] - 120) // 54
                    index = editor.list_offset + row
                    if 0 <= index < len(editor.species_ids):
                        editor.select_species(index)
            if event.type == pygame.MOUSEWHEEL and pygame.mouse.get_pos()[0] < 305:
                editor.scroll_list(-event.y)

        screen.fill(BG)
        if editor.skill_mode:
            draw_skill_editor(screen, editor, available_scroll, learned_scroll)
            for button in skill_buttons:
                button.draw(screen, pygame.mouse.get_pos())
            draw_status_bar(screen, editor.status, pygame.Rect(195, 685, 805, 55), warning="ありません" in editor.status or "してください" in editor.status)
            pygame.display.flip()
            clock.tick(60)
            frames += 1
            if smoke is not None and frames >= smoke:
                running = False
            continue
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
        draw_text(screen, "Ctrl+S 保存  /  PageUp・PageDown レベル変更  /  Esc 終了", (600, 38), 15, MUTED)
        pygame.draw.rect(screen, PANEL, pygame.Rect(20, 85, 280, 630), border_radius=10)
        draw_text(screen, f"種族一覧  {len(editor.species_ids) - 1}件", (35, 91), 15, MUTED, True)
        for row, species_id in enumerate(editor.species_ids[editor.list_offset:editor.list_offset + 10]):
            index = editor.list_offset + row
            rect = pygame.Rect(35, 120 + row * 54, 250, 46)
            pygame.draw.rect(screen, SELECTED if index == editor.selected else PANEL_ALT, rect, border_radius=6)
            if species_id == NEW_SPECIES_ID:
                draw_text(screen, "＋ 新規作成", (rect.x + 16, rect.y + 11), 19, ACCENT, True)
                continue
            bundle = editor.repository.get_species(species_id)
            portrait_path = editor.asset_root / str(bundle.definition.get("portrait_path", ""))
            try:
                portrait = pygame.image.load(str(portrait_path)).convert_alpha()
                portrait = pygame.transform.scale(portrait, (36, 36))
                screen.blit(portrait, (rect.x + 5, rect.y + 5))
            except (OSError, pygame.error):
                pygame.draw.rect(screen, MUTED, pygame.Rect(rect.x + 8, rect.y + 8, 30, 30), border_radius=5)
            draw_text(screen, bundle.definition.get("display_name", species_id), (rect.x + 48, rect.y + 6), 17)
            draw_text(screen, species_id, (rect.x + 48, rect.y + 26), 12, MUTED)
        species_scroll.configure(len(editor.species_ids), 10)
        species_scroll.value = editor.list_offset
        if species_scroll.maximum:
            species_scroll.draw(screen, pygame.mouse.get_pos())

        pygame.draw.rect(screen, PANEL, pygame.Rect(320, 85, 855, 630), border_radius=10)
        editor.id_field.draw(screen, "種族ID")
        editor.name_field.draw(screen, "種族名")
        editor.color_field.draw(screen, "プレースホルダー色")
        draw_text(screen, f"Lv {editor.level}", (505, 218), 24, ACCENT, True)
        for key, field in editor.stat_fields.items():
            field.draw(screen, STAT_LABELS[key])
        draw_text(screen, "装備可否は data/equipment/equipment.json の", (760, 185), 16, MUTED)
        draw_text(screen, "allowed_species_ids で装備品ごとに管理します。", (760, 208), 16, ACCENT)
        draw_text(screen, f"AI: {editor.definition.get('ai_profile', 'normal')}", (350, 555), 19, ACCENT)
        learned = [item for item in editor.skills_payload.get("learnset", []) if int(item["level"]) <= editor.level]
        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(760, 455, 380, 150), border_radius=8)
        draw_text(screen, f"Lv{editor.level}までの習得スキル", (775, 468), 17, MUTED, True)
        catalog = editor.repository.get_skills()
        learned_names = [str(catalog.get(str(item["skill_id"]), {}).get("display_name", item["skill_id"])) for item in learned]
        draw_wrapped(screen, "、".join(learned_names) or "なし", pygame.Rect(775, 500, 350, 85), 15)
        mouse = pygame.mouse.get_pos()
        for button in buttons:
            button.draw(screen, mouse)
        draw_status_bar(screen, editor.status, pygame.Rect(745, 645, 395, 55), warning="できません" in editor.status or "してください" in editor.status)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()

