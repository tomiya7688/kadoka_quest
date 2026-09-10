from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pygame

from kadoka_quest.core.ai import TACTICS
from kadoka_quest.core.monster import calculate_stats
from kadoka_quest.data.jsonio import read_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore
from kadoka_quest.paths import ASSET_ROOT
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


STAT_LABELS = {
    "attack": "攻撃",
    "defense": "防御",
    "speed": "素早さ",
    "magic": "魔力",
    "hp": "HP",
    "mp": "MP",
}


class RanchManager:
    """Player-facing ownership and party management used by the in-world ranch."""

    def __init__(self) -> None:
        self.repository = GameRepository()
        self.monsters = MonsterStore(repository=self.repository)
        self.states = StateStore()
        self.state = self.states.load()
        self.states.ensure_starters(self.state, self.monsters)
        self.parties = PartyStore()
        self.records = []
        self.selected = 0
        self.offset = 0
        self.tab = "individual"
        self.presets: list[Path] = []
        self.selected_preset = 0
        self.preset_offset = 0
        self.status = "牧場では所有個体とパーティを管理できます。"
        self.refresh()

    def refresh(self) -> None:
        current_id = self.records[self.selected].monster_id if self.records and self.selected < len(self.records) else None
        self.records = self.monsters.list_records()
        if current_id:
            self.selected = next((index for index, record in enumerate(self.records) if record.monster_id == current_id), 0)
        self.selected = max(0, min(self.selected, max(0, len(self.records) - 1)))
        self.offset = max(0, min(self.offset, max(0, len(self.records) - 10)))
        self.presets = self.parties.list_presets()
        self.selected_preset = max(0, min(self.selected_preset, max(0, len(self.presets) - 1)))
        self.preset_offset = max(0, min(self.preset_offset, max(0, len(self.presets) - 8)))

    @property
    def selected_record(self):
        return self.records[self.selected] if self.records else None

    def add_party(self) -> None:
        record = self.selected_record
        if not record:
            return
        party = list(self.state.get("current_party", []))
        if record.monster_id in party:
            self.status = "既に現在パーティへ入っています。"
        elif len(party) >= 4:
            self.status = "戦闘パーティは4枠です。"
        else:
            party.append(record.monster_id)
            self.state["current_party"] = party
            self.states.save(self.state)
            self.status = f"{record.name} をパーティへ追加しました。"

    def remove_party(self) -> None:
        record = self.selected_record
        if not record:
            return
        self.state["current_party"] = [item for item in self.state.get("current_party", []) if item != record.monster_id]
        self.states.save(self.state)
        self.status = f"{record.name} をパーティから外しました。個体は牧場に残ります。"

    def reset_ai(self) -> None:
        record = self.selected_record
        if not record:
            return
        self.monsters.reset_ai(record.monster_id)
        self.status = f"{record.name} のAIだけ初期化しました。"
        self.refresh()

    def cycle_tactic(self) -> None:
        record = self.selected_record
        if not record:
            return
        current = str(record.ai.get("tactic", "balanced"))
        index = TACTICS.index(current) if current in TACTICS else 0
        next_tactic = TACTICS[(index + 1) % len(TACTICS)]
        self.monsters.set_tactic(record.monster_id, next_tactic)
        self.status = f"{record.name} の行動指針を {next_tactic} に変更しました。"
        self.refresh()

    def save_preset(self) -> None:
        name = "編成_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.parties.save(name, list(self.state.get("current_party", [])))
        self.status = f"{path.name} を保存しました。"
        self.refresh()
        self.selected_preset = self.presets.index(path)
        self.preset_offset = max(0, self.selected_preset - 7)

    def update_preset(self) -> None:
        if not self.presets:
            self.save_preset()
            return
        path = self.presets[self.selected_preset]
        name = str(read_json(path).get("name", path.stem))
        self.parties.update(path, name, list(self.state.get("current_party", [])))
        self.status = f"{path.name} を現在編成で更新しました。"

    def load_preset(self) -> None:
        if not self.presets:
            self.status = "保存済みプリセットがありません。"
            return
        path = self.presets[self.selected_preset]
        loaded = self.parties.load(path, self.monsters)
        self.state["current_party"] = [record.monster_id for record in loaded if record]
        self.states.save(self.state)
        missing = sum(1 for record in loaded if record is None)
        self.status = f"{path.name} を読み込みました（空き{missing}）。"


def main() -> None:
    screen = init_pygame("kadoka quest - 牧場", (1160, 740))
    clock = pygame.time.Clock()
    manager = RanchManager()
    running = True
    smoke = smoke_frames()
    frames = 0
    portrait_cache: dict[tuple[str, int], pygame.Surface] = {}

    def portrait(species_id: str, size: int) -> pygame.Surface | None:
        key = (species_id, size)
        if key in portrait_cache:
            return portrait_cache[key]
        try:
            bundle = manager.repository.get_species(species_id)
            source = pygame.image.load(str(ASSET_ROOT / str(bundle.definition.get("portrait_path", "")))).convert_alpha()
            portrait_cache[key] = pygame.transform.scale(source, (size, size))
            return portrait_cache[key]
        except (OSError, pygame.error, KeyError):
            return None

    tab_buttons = [
        Button(pygame.Rect(455, 25, 180, 42), "個体情報", lambda: setattr(manager, "tab", "individual")),
        Button(pygame.Rect(645, 25, 190, 42), "パーティ編成", lambda: setattr(manager, "tab", "party")),
    ]
    individual_buttons = [
        Button(pygame.Rect(455, 315, 155, 42), "パーティへ追加", manager.add_party),
        Button(pygame.Rect(620, 315, 155, 42), "パーティから外す", manager.remove_party),
        Button(pygame.Rect(785, 315, 155, 42), "行動指針を切替", manager.cycle_tactic),
        Button(pygame.Rect(950, 315, 155, 42), "AIをリセット", manager.reset_ai),
    ]
    party_buttons = [
        Button(pygame.Rect(805, 555, 100, 42), "新規保存", manager.save_preset),
        Button(pygame.Rect(915, 555, 90, 42), "上書き", manager.update_preset),
        Button(pygame.Rect(1015, 555, 90, 42), "読込", manager.load_preset),
        Button(pygame.Rect(455, 595, 170, 42), "選択個体を追加", manager.add_party),
        Button(pygame.Rect(635, 595, 170, 42), "選択個体を外す", manager.remove_party),
    ]
    owned_scroll = ScrollBar(pygame.Rect(412, 120, 9, 520), "vertical", total=len(manager.records), page=9)
    preset_scroll = ScrollBar(pygame.Rect(1107, 150, 9, 376), "vertical", total=len(manager.presets), page=8)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            owned_scroll.configure(len(manager.records), 9)
            preset_scroll.configure(len(manager.presets), 8)
            owned_scroll.value = manager.offset
            preset_scroll.value = manager.preset_offset
            handled = owned_scroll.handle(event)
            active_buttons = individual_buttons if manager.tab == "individual" else party_buttons
            if manager.tab == "party":
                handled = preset_scroll.handle(event) or handled
            manager.offset = owned_scroll.value
            manager.preset_offset = preset_scroll.value
            for button in tab_buttons + active_buttons:
                handled = button.handle(event) or handled

            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if 25 <= event.pos[0] < 405 and 120 <= event.pos[1] < 606:
                    row = (event.pos[1] - 120) // 54
                    index = manager.offset + row
                    if 0 <= index < len(manager.records):
                        manager.selected = index
                elif manager.tab == "party" and 805 <= event.pos[0] < 1105 and 150 <= event.pos[1] < 526:
                    row = (event.pos[1] - 150) // 47
                    index = manager.preset_offset + row
                    if 0 <= index < len(manager.presets):
                        manager.selected_preset = index

            if event.type == pygame.MOUSEWHEEL:
                mouse_x, _ = pygame.mouse.get_pos()
                if mouse_x < 435:
                    manager.offset = max(0, min(owned_scroll.maximum, manager.offset - event.y))
                elif manager.tab == "party":
                    manager.preset_offset = max(0, min(preset_scroll.maximum, manager.preset_offset - event.y))

        screen.fill(BG)
        draw_text(screen, "モンスター牧場", (24, 24), 34, ACCENT, True)
        draw_text(screen, f"所有 {len(manager.records)}体", (25, 72), 16, MUTED)
        for button, tab in zip(tab_buttons, ("individual", "party")):
            button.draw(screen, pygame.mouse.get_pos())
            if manager.tab == tab:
                pygame.draw.rect(screen, ACCENT, pygame.Rect(button.rect.x + 12, button.rect.bottom - 4, button.rect.width - 24, 4), border_radius=2)

        pygame.draw.rect(screen, PANEL, pygame.Rect(15, 90, 415, 565), border_radius=10)
        draw_text(screen, "所有個体", (30, 98), 17, MUTED, True)
        party_ids = set(manager.state.get("current_party", []))
        for row, record in enumerate(manager.records[manager.offset:manager.offset + 9]):
            index = manager.offset + row
            rect = pygame.Rect(25, 120 + row * 54, 378, 47)
            pygame.draw.rect(screen, SELECTED if index == manager.selected else PANEL_ALT, rect, border_radius=6)
            image = portrait(record.species_id, 38)
            if image:
                screen.blit(image, (rect.x + 5, rect.y + 5))
            marker = "★ " if record.monster_id in party_ids else ""
            draw_text(screen, marker + record.name, (rect.x + 50, rect.y + 5), 17, GOOD if marker else TEXT, True)
            draw_text(screen, f"Lv{record.level}  {record.species_id}  AI:{record.ai.get('tactic', 'balanced')}", (rect.x + 50, rect.y + 27), 12, MUTED)
        owned_scroll.configure(len(manager.records), 9)
        owned_scroll.value = manager.offset
        if owned_scroll.maximum:
            owned_scroll.draw(screen, pygame.mouse.get_pos())

        pygame.draw.rect(screen, PANEL, pygame.Rect(445, 90, 700, 565), border_radius=10)
        record = manager.selected_record
        if manager.tab == "individual":
            draw_text(screen, "個体情報", (455, 108), 24, ACCENT, True)
            if record:
                image = portrait(record.species_id, 120)
                if image:
                    screen.blit(image, (455, 145))
                draw_text(screen, record.name, (595, 145), 28, TEXT, True)
                draw_text(screen, f"{record.species_id} / Lv{record.level} / +{len(record.plus_choices)}", (595, 182), 16, MUTED)
                draw_text(screen, f"装備: {record.equipment_id or 'なし'} / 行動指針: {record.ai.get('tactic', 'balanced')}", (595, 210), 15, MUTED)
                draw_text(screen, f"AI戦闘 {record.ai.get('battles', 0)}回・行動 {record.ai.get('actions', 0)}回", (595, 238), 15, MUTED)
                stats = calculate_stats(manager.repository, record)
                for index, key in enumerate(("hp", "mp", "attack", "defense", "speed", "magic")):
                    x = 860 + (index % 2) * 125
                    y = 142 + (index // 2) * 43
                    pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(x, y, 115, 35), border_radius=5)
                    draw_text(screen, f"{STAT_LABELS[key]} {stats[key]}", (x + 8, y + 8), 14)
            for button in individual_buttons:
                button.draw(screen, pygame.mouse.get_pos())
            draw_wrapped(
                screen,
                "新しい個体の作成、外部個体の取り込み、模擬戦などの開発用機能は牧場にはありません。",
                pygame.Rect(455, 400, 650, 55),
                16,
                MUTED,
            )
        else:
            draw_text(screen, "現在パーティ（4枠）", (455, 108), 24, ACCENT, True)
            party = StateStore.party_records(manager.state, manager.monsters)
            for index in range(4):
                rect = pygame.Rect(455, 150 + index * 90, 325, 76)
                pygame.draw.rect(screen, PANEL_ALT, rect, border_radius=7)
                if index < len(party):
                    member = party[index]
                    image = portrait(member.species_id, 58)
                    if image:
                        screen.blit(image, (rect.x + 8, rect.y + 9))
                    draw_text(screen, f"{index + 1}. {member.name}", (rect.x + 78, rect.y + 10), 18, GOOD, True)
                    draw_text(screen, f"Lv{member.level} {member.species_id}", (rect.x + 78, rect.y + 40), 13, MUTED)
                else:
                    draw_text(screen, f"{index + 1}. 空き", (rect.x + 20, rect.y + 25), 17, MUTED)
            draw_text(screen, f"保存パーティ {len(manager.presets)}件", (805, 108), 20, ACCENT, True)
            for row, path in enumerate(manager.presets[manager.preset_offset:manager.preset_offset + 8]):
                index = manager.preset_offset + row
                data = read_json(path)
                rect = pygame.Rect(805, 150 + row * 47, 300, 40)
                pygame.draw.rect(screen, SELECTED if index == manager.selected_preset else PANEL_ALT, rect, border_radius=5)
                draw_text(screen, str(data.get("name", path.stem)), (rect.x + 10, rect.y + 8), 14)
            preset_scroll.configure(len(manager.presets), 8)
            preset_scroll.value = manager.preset_offset
            if preset_scroll.maximum:
                preset_scroll.draw(screen, pygame.mouse.get_pos())
            for button in party_buttons:
                button.draw(screen, pygame.mouse.get_pos())

        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(15, 670, 1130, 50), border_radius=8)
        draw_wrapped(screen, manager.status, pygame.Rect(30, 682, 1100, 28), 15)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
