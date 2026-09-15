from __future__ import annotations

import pygame

from kadoka_quest.apps.simulation_roster_service import SimulationRosterService
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.paths import IMPORT_ROOT, SAVE_ROOT
from kadoka_quest.ui.common import ACCENT, BG, GOOD, MUTED, PANEL, PANEL_ALT, SELECTED, TEXT, WARN, Button, draw_text, draw_wrapped, init_pygame, smoke_frames


class SimulationManager:
    """Player-facing manager for simulation-only opponents."""

    def __init__(self) -> None:
        self.repository = GameRepository()
        self.roster = SimulationRosterService(
            SAVE_ROOT / "simulation",
            self.repository,
            IMPORT_ROOT / "simulation",
        )
        self.records = []
        self.selected = 0
        self.opponents: list[str] = []
        self.species_ids = list(self.repository.list_species_ids())
        self.species_index = 0
        self.level = 1
        self.status = "模擬戦専用個体を準備し、相手パーティを1〜4体で編成してください。"
        self.refresh()

    def refresh(self) -> None:
        current = self.selected_record.monster_id if self.selected_record else None
        self.records = self.roster.list_records()
        self.opponents = [monster_id for monster_id in self.opponents if any(r.monster_id == monster_id for r in self.records)]
        if current:
            self.selected = next((i for i, record in enumerate(self.records) if record.monster_id == current), 0)
        self.selected = max(0, min(self.selected, max(0, len(self.records) - 1)))

    @property
    def selected_record(self):
        return self.records[self.selected] if self.records and self.selected < len(self.records) else None

    @property
    def selected_species_id(self) -> str:
        if not self.species_ids:
            raise RuntimeError("種族データがありません。")
        return self.species_ids[self.species_index % len(self.species_ids)]

    def cycle_species(self, amount: int) -> None:
        if self.species_ids:
            self.species_index = (self.species_index + amount) % len(self.species_ids)

    def change_level(self, amount: int) -> None:
        self.level = max(1, min(100, self.level + int(amount)))

    def create_opponent(self) -> None:
        try:
            record = self.roster.create(self.selected_species_id, level=self.level)
        except (OSError, ValueError, KeyError) as exc:
            self.status = f"模擬戦個体を作成できません: {exc}"
            return
        self.refresh()
        self.selected = next((i for i, item in enumerate(self.records) if item.monster_id == record.monster_id), 0)
        self.status = f"{record.name} Lv{record.level} を模擬戦専用個体として作成しました。"

    def import_external(self) -> None:
        try:
            added, skipped = self.roster.import_external()
        except OSError as exc:
            self.status = f"外部個体を取り込めません: {exc}"
            return
        self.refresh()
        self.status = f"imports/simulation から {added}体を取込、{skipped}件をスキップしました。"

    def delete_selected(self) -> None:
        record = self.selected_record
        if record is None:
            return
        self.roster.delete(record.monster_id)
        self.opponents = [monster_id for monster_id in self.opponents if monster_id != record.monster_id]
        self.status = f"{record.name} を模擬戦専用ロスターから削除しました。"
        self.refresh()

    def toggle_selected(self) -> None:
        record = self.selected_record
        if record is None:
            return
        if record.monster_id in self.opponents:
            self.opponents.remove(record.monster_id)
            self.status = f"{record.name} を相手パーティから外しました。"
            return
        if len(self.opponents) >= 4:
            self.status = "相手パーティは4体までです。"
            return
        self.opponents.append(record.monster_id)
        self.status = f"{record.name} を相手パーティへ追加しました。"

    def request_battle(self) -> bool:
        try:
            self.roster.request_battle(self.opponents)
        except (OSError, ValueError, KeyError) as exc:
            self.status = str(exc) or "模擬戦を開始できません。"
            return False
        self.status = "対戦相手を確定しました。受付を閉じて模擬戦を開始します。"
        return True


def main() -> None:
    screen = init_pygame("kadoka quest - 模擬戦受付", (1100, 720))
    clock = pygame.time.Clock()
    manager = SimulationManager()
    running = True
    smoke = smoke_frames()
    frames = 0

    def close() -> None:
        nonlocal running
        running = False

    def start() -> None:
        nonlocal running
        if manager.request_battle():
            running = False

    buttons = [
        Button(pygame.Rect(455, 175, 120, 40), "種族 <", lambda: manager.cycle_species(-1)),
        Button(pygame.Rect(580, 175, 120, 40), "種族 >", lambda: manager.cycle_species(1)),
        Button(pygame.Rect(455, 225, 70, 40), "Lv-10", lambda: manager.change_level(-10)),
        Button(pygame.Rect(530, 225, 70, 40), "Lv-1", lambda: manager.change_level(-1)),
        Button(pygame.Rect(605, 225, 70, 40), "Lv+1", lambda: manager.change_level(1)),
        Button(pygame.Rect(680, 225, 70, 40), "Lv+10", lambda: manager.change_level(10)),
        Button(pygame.Rect(760, 175, 150, 40), "専用個体を作成", manager.create_opponent),
        Button(pygame.Rect(920, 175, 150, 40), "外部個体を取込", manager.import_external),
        Button(pygame.Rect(455, 315, 180, 42), "相手へ追加 / 外す", manager.toggle_selected),
        Button(pygame.Rect(645, 315, 130, 42), "選択個体を削除", manager.delete_selected),
        Button(pygame.Rect(800, 585, 130, 48), "模擬戦開始", start),
        Button(pygame.Rect(940, 585, 130, 48), "閉じる", close),
    ]

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            handled = False
            for button in buttons:
                handled = button.handle(event) or handled
            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for row, _ in enumerate(manager.records[:10]):
                    rect = pygame.Rect(25, 105 + row * 50, 390, 43)
                    if rect.collidepoint(event.pos):
                        manager.selected = row
                        break

        screen.fill(BG)
        draw_text(screen, "模擬戦受付", (24, 22), 34, ACCENT, True)
        draw_text(screen, "通常の牧場とは別管理です。ここで作った個体は冒険へ持ち出せません。", (220, 33), 16, MUTED)

        pygame.draw.rect(screen, PANEL, pygame.Rect(15, 82, 415, 560), border_radius=10)
        draw_text(screen, f"模擬戦専用個体 {len(manager.records)}体", (25, 92), 18, ACCENT, True)
        for row, record in enumerate(manager.records[:10]):
            rect = pygame.Rect(25, 125 + row * 48, 390, 41)
            selected = row == manager.selected
            pygame.draw.rect(screen, SELECTED if selected else PANEL_ALT, rect, border_radius=6)
            marker = "★" if record.monster_id in manager.opponents else " "
            draw_text(screen, f"{marker} {record.name}", (rect.x + 10, rect.y + 6), 16, GOOD if marker == "★" else TEXT, True)
            draw_text(screen, f"Lv{record.level} / {record.species_id}", (rect.x + 220, rect.y + 8), 13, MUTED)

        pygame.draw.rect(screen, PANEL, pygame.Rect(445, 82, 640, 560), border_radius=10)
        draw_text(screen, "模擬戦個体の作成", (455, 100), 21, ACCENT, True)
        species_id = manager.selected_species_id if manager.species_ids else "-"
        display_name = species_id
        if manager.species_ids:
            display_name = str(manager.repository.get_species(species_id).definition.get("display_name", species_id))
        draw_text(screen, f"種族: {display_name} ({species_id}) / Lv{manager.level}", (455, 140), 17, TEXT)
        draw_text(screen, "外部取込元: imports/simulation", (760, 230), 14, MUTED)

        record = manager.selected_record
        draw_text(screen, "選択中", (455, 285), 18, ACCENT, True)
        draw_text(screen, f"{record.name} / Lv{record.level} / {record.species_id}" if record else "個体なし", (545, 286), 17, TEXT)

        draw_text(screen, "相手パーティ", (455, 385), 21, ACCENT, True)
        lookup = {record.monster_id: record for record in manager.records}
        for index in range(4):
            rect = pygame.Rect(455 + (index % 2) * 300, 425 + (index // 2) * 70, 285, 55)
            pygame.draw.rect(screen, PANEL_ALT, rect, border_radius=6)
            if index < len(manager.opponents) and manager.opponents[index] in lookup:
                opponent = lookup[manager.opponents[index]]
                draw_text(screen, f"{index + 1}. {opponent.name}", (rect.x + 12, rect.y + 8), 16, GOOD, True)
                draw_text(screen, f"Lv{opponent.level} {opponent.species_id}", (rect.x + 12, rect.y + 31), 13, MUTED)
            else:
                draw_text(screen, f"{index + 1}. 空き", (rect.x + 12, rect.y + 17), 15, MUTED)

        for button in buttons:
            button.draw(screen, pygame.mouse.get_pos())
        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(15, 655, 1070, 50), border_radius=8)
        draw_wrapped(screen, manager.status, pygame.Rect(30, 666, 1040, 30), 15, WARN if "でき" in manager.status else TEXT)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()
