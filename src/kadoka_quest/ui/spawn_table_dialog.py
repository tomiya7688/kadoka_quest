from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from kadoka_engine.spawn_table import spawn_weight_ratios
from kadoka_quest.ui.common import (
    ACCENT, GOOD, MUTED, PANEL, PANEL_ALT, SELECTED, TEXT,
    Button, ScrollBar, draw_status_bar, draw_text, handle_fields,
)

if TYPE_CHECKING:
    from kadoka_quest.apps.map_editor import MapEditor


TABLE = pygame.Rect(140, 205, 450, 324)
SPECIES = pygame.Rect(640, 200, 390, 120)
TABLE_ROWS = 9
SPECIES_ROWS = 5


def _cell(surface: pygame.Surface, value: object, rect: pygame.Rect, color: tuple[int, int, int] = TEXT) -> None:
    previous = surface.get_clip()
    surface.set_clip(rect.clip(previous))
    draw_text(surface, value, (rect.x + 5, rect.y + 6), 15, color)
    surface.set_clip(previous)


class SpawnTableDialog:
    """Input/rendering only; map changes are delegated to the editor."""

    def __init__(self, editor: MapEditor) -> None:
        self.editor = editor
        self.table_scroll = ScrollBar(pygame.Rect(TABLE.right + 2, TABLE.y, 10, TABLE.height))
        self.species_scroll = ScrollBar(pygame.Rect(SPECIES.right + 2, SPECIES.y, 10, SPECIES.height))

    def _configure(self) -> None:
        self.table_scroll.value = self.editor.spawn_table_offset
        self.table_scroll.configure(len(self.editor.map_data.get("spawns", [])), TABLE_ROWS)
        self.species_scroll.value = self.editor.spawn_species_offset
        self.species_scroll.configure(len(self.editor.species_ids), SPECIES_ROWS)
        self._store_offsets()

    def _store_offsets(self) -> None:
        self.editor.spawn_table_offset = self.table_scroll.value
        self.editor.spawn_species_offset = self.species_scroll.value

    def _discard_guard(self) -> bool:
        if self.editor.spawn_draft_changed():
            self.editor.status = "未反映の入力があります。「編集を反映」か「マップ保存」、または「入力を戻す」を選んでください。"
            return False
        return True

    def close(self) -> None:
        if self._discard_guard():
            self.editor.spawn_dialog_open = False

    def new(self) -> None:
        if self._discard_guard():
            self.editor.new_spawn()

    def revert(self) -> None:
        if self.editor.current_spawn is not None:
            self.editor.select_spawn(self.editor.selected_spawn)
        else:
            self.editor.load_spawn_fields()
        self.editor.status = "未反映の入力を戻しました。反映済みのマップ編集は維持しています。"

    def _buttons(self) -> list[Button]:
        editor = self.editor
        return [
            Button(pygame.Rect(945, 95, 100, 36), "閉じる", self.close),
            Button(pygame.Rect(140, 550, 140, 40), "新規候補", self.new),
            Button(pygame.Rect(295, 550, 140, 40), "選択を削除", editor.remove_spawn),
            Button(pygame.Rect(640, 500, 180, 42),
                   "編集を反映" if editor.current_spawn is not None else "候補を追加", editor.apply_spawn_range),
            Button(pygame.Rect(850, 500, 180, 42), "入力を戻す", self.revert),
            Button(pygame.Rect(850, 555, 180, 42), "マップ保存", editor.save),
        ]

    def handle(self, event: pygame.event.Event, mouse: tuple[int, int] | None = None) -> None:
        editor = self.editor
        self._configure()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return
            if event.key == pygame.K_s and getattr(event, "mod", 0) & pygame.KMOD_CTRL:
                editor.save()
                return
        if handle_fields(editor.spawn_fields, event):
            return
        for scrollbar in (self.table_scroll, self.species_scroll):
            if scrollbar.handle(event):
                self._store_offsets()
                return
        if event.type == pygame.MOUSEWHEEL:
            position = mouse if mouse is not None else pygame.mouse.get_pos()
            for area, scrollbar in ((TABLE, self.table_scroll), (SPECIES, self.species_scroll)):
                if area.inflate(24, 0).collidepoint(position):
                    scrollbar.value = max(0, min(scrollbar.maximum, scrollbar.value - event.y))
            self._store_offsets()
            return
        for button in self._buttons():
            if button.handle(event):
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if TABLE.collidepoint(event.pos) and self._discard_guard():
                editor.select_spawn(editor.spawn_table_offset + (event.pos[1] - TABLE.y) // 36)
            elif SPECIES.collidepoint(event.pos):
                index = editor.spawn_species_offset + (event.pos[1] - SPECIES.y) // 24
                if 0 <= index < len(editor.species_ids):
                    # Change the draft species, not the selected table row.
                    editor.selected_species = index

    def draw(self, surface: pygame.Surface, mouse: tuple[int, int]) -> None:
        editor = self.editor
        self._configure()
        surface.fill((8, 12, 20))
        panel = pygame.Rect(110, 65, 965, 635)
        pygame.draw.rect(surface, PANEL, panel, border_radius=14)
        pygame.draw.rect(surface, ACCENT, panel, 2, border_radius=14)
        _cell(surface, f"出現テーブル：{editor.map_data['display_name']}", pygame.Rect(140, 94, 790, 35), ACCENT)
        draw_text(surface, "候補を選んで編集 → 反映 → マップ保存（Ctrl+S）", (140, 140), 18, MUTED)
        for label, x in (("種族", 140), ("重み", 335), ("Lv", 425), ("比率*", 505)):
            draw_text(surface, label, (x + 5, 180), 16, MUTED)
        spawns = editor.map_data.get("spawns", [])
        ratios = spawn_weight_ratios(spawns)
        for row, entry in enumerate(spawns[editor.spawn_table_offset:editor.spawn_table_offset + TABLE_ROWS]):
            index = editor.spawn_table_offset + row
            y = TABLE.y + row * 36
            pygame.draw.rect(surface, SELECTED if index == editor.selected_spawn else PANEL_ALT,
                             pygame.Rect(TABLE.x, y, TABLE.width, 33), border_radius=5)
            ratio = f"{ratios[index]:.2%}" if ratios is not None else "無効"
            values = (entry.get("species_id", "?"), entry.get("weight", 1),
                      f"{entry.get('min_level', 1)}–{entry.get('max_level', 1)}", ratio)
            for value, x, width in zip(values, (140, 335, 425, 505), (195, 90, 80, 85)):
                _cell(surface, value, pygame.Rect(x, y, width, 33))
        if not spawns:
            draw_text(surface, "候補なし（野生モンスターは出現しません）", (145, 218), 17, MUTED)
        draw_text(surface, "変更先の種族（スクロールで選択）", (640, 175), 16, MUTED)
        for row, species_id in enumerate(editor.species_ids[editor.spawn_species_offset:editor.spawn_species_offset + SPECIES_ROWS]):
            index = editor.spawn_species_offset + row
            rect = pygame.Rect(SPECIES.x, SPECIES.y + row * 24, SPECIES.width, 23)
            pygame.draw.rect(surface, SELECTED if index == editor.selected_species else PANEL_ALT, rect)
            label = species_id + ("（初期専用・登録不可）" if species_id == "ball_slime" else "")
            _cell(surface, label, rect, GOOD if index == editor.selected_species else MUTED)
        editor.spawn_weight.draw(surface, "相対重み（合計100不要）")
        editor.spawn_min_level.draw(surface, "最小Lv")
        editor.spawn_max_level.draw(surface, "最大Lv")
        for scrollbar in (self.table_scroll, self.species_scroll):
            scrollbar.draw(surface, mouse)
        for button in self._buttons():
            button.draw(surface, mouse)
        draw_text(surface, "* 全候補の重み比。出現フラグ・ポップ率は未考慮", (140, 600), 14, MUTED)
        draw_status_bar(surface, editor.status, pygame.Rect(140, 628, 890, 58))
