from __future__ import annotations

import pygame

from kadoka_quest.apps.simulation_facility_service import SimulationFacilityService
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.paths import IMPORT_ROOT
from kadoka_quest.ui.common import (
    ACCENT,
    BG,
    GOOD,
    MUTED,
    PANEL,
    PANEL_ALT,
    SELECTED,
    TEXT,
    Button,
    ScrollBar,
    draw_text,
    draw_wrapped,
    init_pygame,
    smoke_frames,
)


class SimulationManager:
    """Player-facing editor for the roster isolated in imports/simulation."""

    def __init__(self) -> None:
        self.repository = GameRepository()
        self.facility = SimulationFacilityService(self.repository, IMPORT_ROOT / "simulation")
        self.species_ids = self.repository.list_species_ids()
        self.selected_species = 0
        self.level = 1
        self.records = []
        self.selected = 0
        self.offset = 0
        self.status = "模擬戦専用個体を管理します。牧場の所有個体には追加されません。"
        self.refresh()

    @property
    def species_id(self) -> str:
        return self.species_ids[self.selected_species] if self.species_ids else "slime"

    @property
    def selected_record(self):
        return self.records[self.selected] if self.records else None

    def refresh(self) -> None:
        selected_id = self.selected_record.monster_id if self.selected_record else None
        self.records = self.facility.list_individuals()
        if selected_id:
            self.selected = next((i for i, record in enumerate(self.records) if record.monster_id == selected_id), 0)
        self.selected = max(0, min(self.selected, max(0, len(self.records) - 1)))
        self.offset = max(0, min(self.offset, max(0, len(self.records) - 9)))

    def change_species(self, step: int) -> None:
        if self.species_ids:
            self.selected_species = (self.selected_species + step) % len(self.species_ids)

    def change_level(self, step: int) -> None:
        self.level = max(1, min(100, self.level + step))

    def create(self) -> None:
        try:
            record = self.facility.create_individual(self.species_id, self.level)
        except (OSError, ValueError, KeyError) as exc:
            self.status = f"作成できません: {exc}"
            return
        self.refresh()
        self.selected = next(i for i, item in enumerate(self.records) if item.monster_id == record.monster_id)
        self.status = f"{record.name} Lv{record.level} を模擬戦専用個体として作成しました。"

    def toggle_opponent(self) -> None:
        record = self.selected_record
        if record is None:
            return
        selected = self.facility.opponent_ids()
        if record.monster_id in selected:
            selected.remove(record.monster_id)
            if not selected:
                self.facility.clear_opponents()
            else:
                self.facility.set_opponents(selected)
            self.status = f"{record.name} を相手編成から外しました。"
        else:
            self.facility.set_opponents([*selected, record.monster_id])
            self.status = f"{record.name} を相手編成へ追加しました。"

    def delete(self) -> None:
        record = self.selected_record
        if record is None:
            return
        if self.facility.delete_individual(record.monster_id):
            self.status = f"{record.name} を模擬戦専用個体から削除しました。"
            self.refresh()


def main() -> None:
    screen = init_pygame("kadoka quest - 模擬戦受付", (1120, 740))
    clock = pygame.time.Clock()
    manager = SimulationManager()
    running = True
    smoke = smoke_frames()
    frames = 0
    buttons = [
        Button(pygame.Rect(475, 220, 48, 42), "←", lambda: manager.change_species(-1)),
        Button(pygame.Rect(810, 220, 48, 42), "→", lambda: manager.change_species(1)),
        Button(pygame.Rect(570, 280, 48, 42), "-", lambda: manager.change_level(-1)),
        Button(pygame.Rect(725, 280, 48, 42), "+", lambda: manager.change_level(1)),
        Button(pygame.Rect(545, 350, 250, 48), "模擬戦個体を作成", manager.create),
        Button(pygame.Rect(475, 445, 180, 45), "相手編成へ切替", manager.toggle_opponent),
        Button(pygame.Rect(670, 445, 180, 45), "選択個体を削除", manager.delete),
        Button(pygame.Rect(865, 445, 190, 45), "外部フォルダを再読込", manager.refresh),
    ]
    scroll = ScrollBar(pygame.Rect(412, 120, 9, 520), "vertical", total=0, page=9)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            scroll.configure(len(manager.records), 9)
            scroll.value = manager.offset
            handled = scroll.handle(event)
            manager.offset = scroll.value
            for button in buttons:
                handled = button.handle(event) or handled
            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if 25 <= event.pos[0] < 405 and 120 <= event.pos[1] < 606:
                    index = manager.offset + (event.pos[1] - 120) // 54
                    if 0 <= index < len(manager.records):
                        manager.selected = index
            if event.type == pygame.MOUSEWHEEL and pygame.mouse.get_pos()[0] < 435:
                manager.offset = max(0, min(scroll.maximum, manager.offset - event.y))

        screen.fill(BG)
        draw_text(screen, "模擬戦受付", (24, 24), 34, ACCENT, True)
        draw_text(screen, "専用個体のみ。牧場・通常冒険の所有個体には混ざりません。", (25, 70), 16, MUTED)
        pygame.draw.rect(screen, PANEL, pygame.Rect(15, 90, 415, 565), border_radius=10)
        draw_text(screen, f"模擬戦個体 {len(manager.records)}体", (30, 98), 17, MUTED, True)
        opponent_ids = set(manager.facility.opponent_ids())
        for row, record in enumerate(manager.records[manager.offset:manager.offset + 9]):
            index = manager.offset + row
            rect = pygame.Rect(25, 120 + row * 54, 378, 47)
            pygame.draw.rect(screen, SELECTED if index == manager.selected else PANEL_ALT, rect, border_radius=6)
            marker = "VS " if record.monster_id in opponent_ids else "   "
            draw_text(screen, marker + record.name, (rect.x + 10, rect.y + 6), 17, GOOD if marker.strip() else TEXT, True)
            draw_text(screen, f"Lv{record.level}  {record.species_id}  AI:{record.ai.get('tactic', 'balanced')}", (rect.x + 15, rect.y + 27), 12, MUTED)
        scroll.configure(len(manager.records), 9)
        scroll.value = manager.offset
        if scroll.maximum:
            scroll.draw(screen, pygame.mouse.get_pos())

        pygame.draw.rect(screen, PANEL, pygame.Rect(445, 90, 660, 565), border_radius=10)
        draw_text(screen, "新規作成", (475, 118), 25, ACCENT, True)
        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(535, 210, 265, 55), border_radius=7)
        draw_text(screen, manager.species_id, (555, 226), 20, TEXT, True)
        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(630, 275, 88, 52), border_radius=7)
        draw_text(screen, f"Lv {manager.level}", (644, 292), 18, TEXT, True)
        for button in buttons:
            button.draw(screen, pygame.mouse.get_pos())
        record = manager.selected_record
        if record:
            draw_text(screen, "選択中", (475, 520), 20, ACCENT, True)
            draw_text(screen, f"{record.name} / {record.species_id} / Lv{record.level}", (475, 552), 19, TEXT, True)
            draw_text(screen, "VS 表示は現在の相手パーティです。", (475, 584), 15, MUTED)
        else:
            draw_wrapped(screen, "外部個体は imports/simulation に monster.json と ai.json を持つフォルダとして置き、「外部フォルダを再読込」を選びます。", pygame.Rect(475, 520, 570, 70), 16, MUTED)
        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(15, 670, 1090, 50), border_radius=8)
        draw_wrapped(screen, manager.status, pygame.Rect(30, 682, 1060, 28), 15)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()
