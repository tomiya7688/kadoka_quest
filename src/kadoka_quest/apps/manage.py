from __future__ import annotations

from datetime import datetime
from pathlib import Path
import random

import pygame

from kadoka_quest.core.ai import TACTICS
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.data.jsonio import read_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore
from kadoka_quest.paths import IMPORT_ROOT
from kadoka_quest.ui.common import ACCENT, BAD, BG, GOOD, MUTED, PANEL, PANEL_ALT, WARN, Button, draw_text, draw_wrapped, init_pygame, smoke_frames


class Manager:
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
        self.species_ids = self.repository.list_species_ids()
        self.selected_species = 0
        self.presets: list[Path] = []
        self.selected_preset = 0
        self.status = "所有上限・プリセット数の上限はありません。個体は1体1フォルダです。"
        self.refresh()

    def refresh(self) -> None:
        current_id = self.records[self.selected].monster_id if self.records and self.selected < len(self.records) else None
        self.records = self.monsters.list_records()
        if current_id:
            self.selected = next((index for index, record in enumerate(self.records) if record.monster_id == current_id), 0)
        self.selected = max(0, min(self.selected, max(0, len(self.records) - 1)))
        self.presets = self.parties.list_presets()
        self.selected_preset = max(0, min(self.selected_preset, max(0, len(self.presets) - 1)))

    @property
    def selected_record(self):
        return self.records[self.selected] if self.records else None

    def create(self) -> None:
        species_id = self.species_ids[self.selected_species]
        record = self.monsters.create(species_id, source="manager")
        self.status = f"{record.name} を作成しました。所有数は {len(self.records) + 1} 体です。"
        self.refresh()
        self.selected = next(index for index, item in enumerate(self.records) if item.monster_id == record.monster_id)

    def add_party(self) -> None:
        record = self.selected_record
        if not record:
            return
        party = list(self.state.get("current_party", []))
        if record.monster_id in party:
            self.status = "既に現在パーティへ入っています。"
        elif len(party) >= 4:
            self.status = "戦闘パーティは主人公を含め4枠です。"
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
        self.status = f"{record.name} をパーティから外しました。個体は所有したままです。"

    def reset_ai(self) -> None:
        record = self.selected_record
        if not record:
            return
        self.monsters.reset_ai(record.monster_id)
        self.status = f"{record.name} のAIだけ初期化しました。名前・Lv・＋・装備は維持されています。"
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
        self.status = f"{path.name} を新規保存しました。プリセット数に上限はありません。"
        self.refresh()
        self.selected_preset = self.presets.index(path)

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
        self.status = f"{path.name} を読み込みました。存在しないIDや空欄は空き枠になります（空き{missing}）。"

    def acquire(self) -> None:
        try:
            added, skipped = self.monsters.acquire_from_scan(IMPORT_ROOT / "acquire")
            self.status = f"再走査完了：{added}体を獲得、{skipped}件を重複または不正としてスキップ。"
            self.refresh()
        except (OSError, ValueError, KeyError) as exc:
            self.status = f"再走査できません: {exc}"

    def simulation(self) -> None:
        imported = self.monsters.discover_external(IMPORT_ROOT / "simulation")
        party = StateStore.party_records(self.state, self.monsters)
        if not imported:
            self.status = "imports/simulation に monster.json と ai.json を含む個体フォルダを置いてください。"
            return
        if not party:
            self.status = "現在パーティが空です。"
            return
        try:
            engine = BattleEngine(self.repository, party, imported, random.Random(7), learning_enabled=False)
            for _ in range(100):
                engine.run_round()
                if engine.outcome:
                    break
            self.status = f"模擬戦: {engine.outcome or '100ターン引き分け'} / {engine.round_number}ターン。AI更新なし。最後: {' '.join(engine.log[-2:])}"
        except (OSError, ValueError, KeyError) as exc:
            self.status = f"模擬戦インポートを読めません: {exc}"


def main() -> None:
    screen = init_pygame("kadoka quest - 個体・パーティ管理", (1240, 780))
    clock = pygame.time.Clock()
    manager = Manager()
    running = True
    smoke = smoke_frames()
    frames = 0
    buttons = [
        Button(pygame.Rect(455, 160, 180, 42), "パーティへ追加", manager.add_party),
        Button(pygame.Rect(650, 160, 180, 42), "パーティから外す", manager.remove_party),
        Button(pygame.Rect(455, 220, 180, 42), "行動指針を切替", manager.cycle_tactic),
        Button(pygame.Rect(650, 220, 180, 42), "AIをリセット", manager.reset_ai),
        Button(pygame.Rect(455, 330, 180, 42), "個体を新規作成", manager.create),
        Button(pygame.Rect(455, 520, 150, 42), "編成を保存", manager.save_preset),
        Button(pygame.Rect(620, 520, 150, 42), "編成を更新", manager.update_preset),
        Button(pygame.Rect(785, 520, 150, 42), "編成を読込", manager.load_preset),
        Button(pygame.Rect(970, 610, 230, 42), "個体フォルダを再走査", manager.acquire),
        Button(pygame.Rect(970, 665, 230, 42), "インポート個体と模擬戦", manager.simulation),
    ]

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.MOUSEWHEEL:
                manager.offset = max(0, min(max(0, len(manager.records) - 10), manager.offset - event.y))
            handled = False
            for button in buttons:
                handled = button.handle(event) or handled
            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for row in range(10):
                    index = manager.offset + row
                    if index < len(manager.records) and pygame.Rect(25, 110 + row * 56, 390, 48).collidepoint(event.pos):
                        manager.selected = index
                for index, species_id in enumerate(manager.species_ids):
                    if pygame.Rect(455 + (index % 4) * 118, 390 + (index // 4) * 42, 108, 34).collidepoint(event.pos):
                        manager.selected_species = index
                for index, path in enumerate(manager.presets[:5]):
                    if pygame.Rect(455, 580 + index * 30, 450, 25).collidepoint(event.pos):
                        manager.selected_preset = index

        screen.fill(BG)
        draw_text(screen, "個体・パーティ管理", (24, 24), 36, ACCENT, True)
        draw_text(screen, f"所有 {len(manager.records)}体（上限なし）", (25, 78), 18, MUTED)
        pygame.draw.rect(screen, PANEL, pygame.Rect(15, 95, 415, 610), border_radius=10)
        party_ids = set(manager.state.get("current_party", []))
        for row in range(10):
            index = manager.offset + row
            if index >= len(manager.records):
                break
            record = manager.records[index]
            rect = pygame.Rect(25, 110 + row * 56, 390, 48)
            pygame.draw.rect(screen, (55, 94, 122) if index == manager.selected else PANEL_ALT, rect, border_radius=6)
            draw_text(screen, ("★ " if record.monster_id in party_ids else "") + record.name, (38, rect.y + 7), 18, GOOD if record.monster_id in party_ids else None or (238, 242, 247))
            draw_text(screen, f"Lv{record.level} / {record.species_id} / {record.ai.get('tactic', 'balanced')}", (190, rect.y + 15), 13, MUTED)

        pygame.draw.rect(screen, PANEL, pygame.Rect(445, 95, 510, 610), border_radius=10)
        record = manager.selected_record
        if record:
            draw_text(screen, record.name, (465, 110), 28, ACCENT, True)
            draw_text(screen, f"{record.monster_id}  Lv{record.level}  +{len(record.plus_choices)}", (465, 140), 15, MUTED)
            draw_text(screen, f"AI戦闘数 {record.ai.get('battles', 0)} / 行動数 {record.ai.get('actions', 0)}", (850, 142), 14, MUTED)
        draw_text(screen, "作成する種族", (455, 365), 18, MUTED, True)
        for index, species_id in enumerate(manager.species_ids):
            rect = pygame.Rect(455 + (index % 4) * 118, 390 + (index // 4) * 42, 108, 34)
            pygame.draw.rect(screen, GOOD if index == manager.selected_species else PANEL_ALT, rect, border_radius=5)
            draw_text(screen, species_id, (rect.x + 7, rect.y + 9), 13, BG if index == manager.selected_species else MUTED, index == manager.selected_species)
        draw_text(screen, "保存パーティ（ID参照）", (455, 555), 17, MUTED, True)
        for index, path in enumerate(manager.presets[:5]):
            rect = pygame.Rect(455, 580 + index * 30, 450, 25)
            if index == manager.selected_preset:
                pygame.draw.rect(screen, (55, 94, 122), rect, border_radius=4)
            draw_text(screen, path.name, (463, rect.y + 4), 14)

        pygame.draw.rect(screen, PANEL, pygame.Rect(970, 95, 245, 455), border_radius=10)
        draw_text(screen, "現在パーティ", (985, 112), 21, ACCENT, True)
        party = StateStore.party_records(manager.state, manager.monsters)
        for index in range(4):
            rect = pygame.Rect(985, 155 + index * 62, 215, 50)
            pygame.draw.rect(screen, PANEL_ALT, rect, border_radius=6)
            if index < len(party):
                draw_text(screen, f"{index + 1}. {party[index].name}", (997, rect.y + 8), 17)
                draw_text(screen, party[index].species_id, (997, rect.y + 29), 13, MUTED)
            else:
                draw_text(screen, f"{index + 1}. 空き", (997, rect.y + 14), 16, MUTED)
        draw_wrapped(screen, "imports/acquire は通常獲得、imports/simulation はAIを育てない読み取り専用の模擬戦です。", pygame.Rect(985, 420, 210, 105), 15, WARN)

        mouse = pygame.mouse.get_pos()
        for button in buttons:
            button.draw(screen, mouse)
        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(20, 720, 1195, 45), border_radius=8)
        draw_wrapped(screen, manager.status, pygame.Rect(35, 728, 1160, 32), 16)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()


