# {
#   責務: [manage: manageの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import random

import pygame

from kadoka_quest.core.ai import TACTICS
from kadoka_quest.apps.ai_inspector import AiInspector
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.monster import calculate_stats
from kadoka_quest.data.jsonio import read_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore
from kadoka_quest.paths import ASSET_ROOT, IMPORT_ROOT
from kadoka_quest.ui.ai_tendency_panel import draw_ai_tendencies
from kadoka_quest.ui.common import ACCENT, BG, GOOD, MUTED, PANEL, PANEL_ALT, SELECTED, TEXT, WARN, Button, ScrollBar, draw_status_bar, draw_text, draw_wrapped, init_pygame, smoke_frames


STAT_LABELS = {"attack": "攻撃", "defense": "防御", "speed": "素早さ", "magic": "魔力", "hp": "HP", "mp": "MP"}


# {
#   責務: [Manager: managerの状態と振る舞いを担当する]
#   フィールド: [
#     repository: データ取得先
#     monsters: モンスター一覧
#     states: states
#     state: 状態
#     parties: parties
#     records: 個体レコード一覧
#     selected: 選択中
#     offset: 表示位置
#     tab: tab
#     species_ids: 種族・識別子一覧
#     selected_species: 選択中・種族
#     species_offset: 種族・表示位置
#     presets: プリセット一覧
#     selected_preset: 選択中・プリセット
#     preset_offset: プリセット・表示位置
#     status: 状態異常
#     skills: スキル一覧
#   ]
# }
class Manager:
    # {
    #   責務: [__init__: managerが利用する初期状態と依存を設定する]
    #   処理: [1: managerが利用する初期状態と依存を設定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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
        self.species_ids = self.repository.list_species_ids()
        self.selected_species = 0
        self.species_offset = 0
        self.presets: list[Path] = []
        self.selected_preset = 0
        self.preset_offset = 0
        self.status = "所有上限・プリセット数の上限はありません。個体は1体1フォルダです。"
        self.refresh()

    # {
    #   責務: [refresh: managerを更新内容を読み直す]
    #   処理: [1: managerを更新内容を読み直す]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def refresh(self) -> None:
        self.skills = self.repository.get_skills()
        current_id = self.records[self.selected].monster_id if self.records and self.selected < len(self.records) else None
        self.records = self.monsters.list_records()
        if current_id:
            self.selected = next((index for index, record in enumerate(self.records) if record.monster_id == current_id), 0)
        self.selected = max(0, min(self.selected, max(0, len(self.records) - 1)))
        self.offset = max(0, min(self.offset, max(0, len(self.records) - 10)))
        self.presets = self.parties.list_presets()
        self.selected_preset = max(0, min(self.selected_preset, max(0, len(self.presets) - 1)))
        self.preset_offset = max(0, min(self.preset_offset, max(0, len(self.presets) - 8)))

    # {
    #   責務: [selected_record: managerの選択中・個体レコードを求める]
    #   処理: [1: managerの選択中・個体レコードを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: managerの選択中・個体レコードを求めるための結果（型注釈なし）]
    # }
    @property
    def selected_record(self):
        return self.records[self.selected] if self.records else None

    # {
    #   責務: [selected_tendencies: managerの選択中・tendenciesを求める]
    #   処理: [1: managerの選択中・tendenciesを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: managerの選択中・tendenciesを求めるための結果（list[dict]）]
    # }
    @property
    def selected_tendencies(self) -> list[dict]:
        record = self.selected_record
        return AiInspector.summarize_tendencies(record.ai, self.skills) if record else []

    # {
    #   責務: [create: managerを作成する]
    #   処理: [1: managerを作成する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def create(self) -> None:
        species_id = self.species_ids[self.selected_species]
        record = self.monsters.create(species_id, source="manager")
        self.status = f"{record.name} を作成しました。所有数は {len(self.records) + 1} 体です。"
        self.refresh()
        self.selected = next(index for index, item in enumerate(self.records) if item.monster_id == record.monster_id)
        self.offset = max(0, self.selected - 9)

    # {
    #   責務: [add_party: パーティを追加する]
    #   処理: [1: パーティを追加する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [remove_party: パーティを取り除く]
    #   処理: [1: パーティを取り除く]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def remove_party(self) -> None:
        record = self.selected_record
        if not record:
            return
        self.state["current_party"] = [item for item in self.state.get("current_party", []) if item != record.monster_id]
        self.states.save(self.state)
        self.status = f"{record.name} をパーティから外しました。個体は所有したままです。"

    # {
    #   責務: [reset_ai: AIの初期状態へ戻す]
    #   処理: [1: AIの初期状態へ戻す]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def reset_ai(self) -> None:
        record = self.selected_record
        if not record:
            return
        self.monsters.reset_ai(record.monster_id)
        self.status = f"{record.name} のAIだけ初期化しました。名前・Lv・＋・装備は維持されています。"
        self.refresh()

    # {
    #   責務: [cycle_tactic: tacticを順に切り替える]
    #   処理: [1: tacticを順に切り替える]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [save_preset: プリセットを保存する]
    #   処理: [1: プリセットを保存する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_preset(self) -> None:
        name = "編成_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.parties.save(name, list(self.state.get("current_party", [])))
        self.status = f"{path.name} を新規保存しました。プリセット数に上限はありません。"
        self.refresh()
        self.selected_preset = self.presets.index(path)
        self.preset_offset = max(0, self.selected_preset - 7)

    # {
    #   責務: [update_preset: プリセットを更新する]
    #   処理: [1: プリセットを更新する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def update_preset(self) -> None:
        if not self.presets:
            self.save_preset()
            return
        path = self.presets[self.selected_preset]
        name = str(read_json(path).get("name", path.stem))
        self.parties.update(path, name, list(self.state.get("current_party", [])))
        self.status = f"{path.name} を現在編成で更新しました。"

    # {
    #   責務: [load_preset: プリセットを読み込む]
    #   処理: [1: プリセットを読み込む]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [acquire: managerのacquireを求める]
    #   処理: [1: managerのacquireを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def acquire(self) -> None:
        try:
            added, skipped = self.monsters.acquire_from_scan(IMPORT_ROOT / "acquire")
            self.status = f"再走査完了：{added}体を獲得、{skipped}件を重複または不正としてスキップ。"
            self.refresh()
        except (OSError, ValueError, KeyError) as exc:
            self.status = f"再走査できません: {exc}"

    # {
    #   責務: [simulation: managerのsimulationを求める]
    #   処理: [1: managerのsimulationを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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


# {
#   責務: [main: manageのエントリ処理を実行する]
#   処理: [1: manageのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def main() -> None:
    screen = init_pygame("kadoka quest - 個体・パーティ管理", (1240, 780))
    clock = pygame.time.Clock()
    manager = Manager()
    running = True
    smoke = smoke_frames()
    frames = 0
    portrait_cache: dict[tuple[str, int], pygame.Surface] = {}

    # {
    #   責務: [portrait: manageのportraitを求める]
    #   処理: [1: manageのportraitを求める]
    #   引数: [
    #     species_id: 種族・識別子（str）
    #     size: 大きさ（int）
    #   ]
    #   戻り値: [result: manageのportraitを求めるための結果（pygame.Surface | None）]
    # }
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
        Button(pygame.Rect(455, 25, 150, 42), "個体情報", lambda: setattr(manager, "tab", "individual")),
        Button(pygame.Rect(615, 25, 170, 42), "パーティ編成", lambda: setattr(manager, "tab", "party")),
        Button(pygame.Rect(795, 25, 210, 42), "取り込み・模擬戦", lambda: setattr(manager, "tab", "tools")),
    ]
    individual_buttons = [
        Button(pygame.Rect(470, 300, 165, 42), "パーティへ追加", manager.add_party),
        Button(pygame.Rect(650, 300, 165, 42), "パーティから外す", manager.remove_party),
        Button(pygame.Rect(830, 300, 165, 42), "行動指針を切替", manager.cycle_tactic),
        Button(pygame.Rect(1010, 300, 165, 42), "AIをリセット", manager.reset_ai),
        Button(pygame.Rect(950, 540, 220, 35), "選択した種族を作成", manager.create),
    ]
    party_buttons = [
        Button(pygame.Rect(835, 555, 105, 42), "新規保存", manager.save_preset),
        Button(pygame.Rect(950, 555, 105, 42), "上書き", manager.update_preset),
        Button(pygame.Rect(1065, 555, 105, 42), "読込", manager.load_preset),
        Button(pygame.Rect(470, 605, 190, 45), "選択個体を追加", manager.add_party),
        Button(pygame.Rect(675, 605, 190, 45), "選択個体を外す", manager.remove_party),
    ]
    tool_buttons = [
        Button(pygame.Rect(500, 285, 300, 48), "個体フォルダを再走査", manager.acquire),
        Button(pygame.Rect(860, 285, 300, 48), "インポート個体と模擬戦", manager.simulation),
    ]
    owned_scroll = ScrollBar(pygame.Rect(412, 120, 9, 540), "vertical", total=len(manager.records), page=10)
    species_scroll = ScrollBar(pygame.Rect(1192, 580, 9, 92), "vertical", total=len(manager.species_ids), page=8)
    preset_scroll = ScrollBar(pygame.Rect(1177, 150, 9, 376), "vertical", total=len(manager.presets), page=8)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.WINDOWFOCUSGAINED or (event.type == pygame.KEYDOWN and event.key == pygame.K_F5):
                manager.refresh()

            owned_scroll.configure(len(manager.records), 10)
            species_scroll.configure(len(manager.species_ids), 8)
            preset_scroll.configure(len(manager.presets), 8)
            owned_scroll.value = manager.offset
            species_scroll.value = manager.species_offset
            preset_scroll.value = manager.preset_offset
            handled = owned_scroll.handle(event)
            if manager.tab == "individual":
                handled = species_scroll.handle(event) or handled
                active_buttons = individual_buttons
            elif manager.tab == "party":
                handled = preset_scroll.handle(event) or handled
                active_buttons = party_buttons
            else:
                active_buttons = tool_buttons
            manager.offset = owned_scroll.value
            manager.species_offset = species_scroll.value
            manager.preset_offset = preset_scroll.value
            for button in tab_buttons + active_buttons:
                handled = button.handle(event) or handled

            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if 25 <= event.pos[0] < 405 and 120 <= event.pos[1] < 660:
                    row = (event.pos[1] - 120) // 54
                    index = manager.offset + row
                    if 0 <= index < len(manager.records):
                        manager.selected = index
                if manager.tab == "individual" and 470 <= event.pos[0] < 1180 and 580 <= event.pos[1] < 672:
                    column = (event.pos[0] - 470) // 177
                    row = (event.pos[1] - 580) // 46
                    index = manager.species_offset + row * 4 + column
                    if 0 <= index < len(manager.species_ids):
                        manager.selected_species = index
                elif manager.tab == "party" and 835 <= event.pos[0] < 1170 and 150 <= event.pos[1] < 526:
                    row = (event.pos[1] - 150) // 47
                    index = manager.preset_offset + row
                    if 0 <= index < len(manager.presets):
                        manager.selected_preset = index
                elif manager.tab == "party" and 470 <= event.pos[0] < 810 and 150 <= event.pos[1] < 510:
                    slot = (event.pos[1] - 150) // 90
                    party = StateStore.party_records(manager.state, manager.monsters)
                    if 0 <= slot < len(party):
                        manager.selected = next((i for i, item in enumerate(manager.records) if item.monster_id == party[slot].monster_id), manager.selected)
                        manager.offset = max(0, min(manager.selected, len(manager.records) - 10))

            if event.type == pygame.MOUSEWHEEL:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if mouse_x < 435:
                    manager.offset = max(0, min(owned_scroll.maximum, manager.offset - event.y))
                elif manager.tab == "individual" and mouse_y >= 560:
                    manager.species_offset = max(0, min(species_scroll.maximum, manager.species_offset - event.y * 4))
                elif manager.tab == "party" and mouse_x >= 820:
                    manager.preset_offset = max(0, min(preset_scroll.maximum, manager.preset_offset - event.y))

        screen.fill(BG)
        draw_text(screen, "個体・パーティ管理", (24, 24), 34, ACCENT, True)
        draw_text(screen, f"所有 {len(manager.records)}体・上限なし", (25, 72), 16, MUTED)
        for button, tab in zip(tab_buttons, ("individual", "party", "tools")):
            button.draw(screen, pygame.mouse.get_pos())
            if manager.tab == tab:
                pygame.draw.rect(screen, ACCENT, pygame.Rect(button.rect.x + 12, button.rect.bottom - 4, button.rect.width - 24, 4), border_radius=2)

        pygame.draw.rect(screen, PANEL, pygame.Rect(15, 90, 415, 615), border_radius=10)
        draw_text(screen, "所有個体", (30, 98), 17, MUTED, True)
        party_ids = set(manager.state.get("current_party", []))
        for row, record in enumerate(manager.records[manager.offset:manager.offset + 10]):
            index = manager.offset + row
            rect = pygame.Rect(25, 120 + row * 54, 378, 47)
            pygame.draw.rect(screen, SELECTED if index == manager.selected else PANEL_ALT, rect, border_radius=6)
            image = portrait(record.species_id, 38)
            if image:
                screen.blit(image, (rect.x + 5, rect.y + 5))
            marker = "★ " if record.monster_id in party_ids else ""
            draw_text(screen, marker + record.name, (rect.x + 50, rect.y + 5), 17, GOOD if marker else TEXT, True)
            draw_text(screen, f"Lv{record.level}  {record.species_id}  AI:{record.ai.get('tactic', 'balanced')}", (rect.x + 50, rect.y + 27), 12, MUTED)
        owned_scroll.configure(len(manager.records), 10)
        owned_scroll.value = manager.offset
        if owned_scroll.maximum:
            owned_scroll.draw(screen, pygame.mouse.get_pos())

        pygame.draw.rect(screen, PANEL, pygame.Rect(445, 90, 770, 615), border_radius=10)
        record = manager.selected_record
        if manager.tab == "individual":
            draw_text(screen, "個体情報", (470, 108), 24, ACCENT, True)
            if record:
                image = portrait(record.species_id, 120)
                if image:
                    screen.blit(image, (470, 145))
                draw_text(screen, record.name, (610, 145), 28, TEXT, True)
                draw_text(screen, f"{record.species_id}  /  Lv{record.level}  /  +{len(record.plus_choices)}", (610, 180), 16, MUTED)
                draw_text(screen, f"装備: {record.equipment_id or 'なし'}  /  行動指針: {record.ai.get('tactic', 'balanced')}", (610, 207), 15, MUTED)
                draw_text(screen, f"AI戦闘 {record.ai.get('battles', 0)}回・行動 {record.ai.get('actions', 0)}回", (610, 232), 15, MUTED)
                stats = calculate_stats(manager.repository, record)
                for index, key in enumerate(("hp", "mp", "attack", "defense", "speed", "magic")):
                    x = 895 + (index % 2) * 135
                    y = 142 + (index // 2) * 43
                    pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(x, y, 125, 35), border_radius=5)
                    draw_text(screen, f"{STAT_LABELS[key]} {stats[key]}", (x + 8, y + 8), 14)
            draw_ai_tendencies(screen, manager.selected_tendencies, pygame.Rect(470, 350, 705, 180), columns=3)
            draw_text(screen, "新しい個体を作成", (470, 545), 19, MUTED, True)
            draw_text(screen, "種族を選択して作成", (680, 549), 14, MUTED)
            for row in range(2):
                for column in range(4):
                    index = manager.species_offset + row * 4 + column
                    if index >= len(manager.species_ids):
                        continue
                    species_id = manager.species_ids[index]
                    bundle = manager.repository.get_species(species_id)
                    rect = pygame.Rect(470 + column * 177, 580 + row * 46, 165, 39)
                    pygame.draw.rect(screen, GOOD if index == manager.selected_species else PANEL_ALT, rect, border_radius=6)
                    image = portrait(species_id, 30)
                    if image:
                        screen.blit(image, (rect.x + 5, rect.y + 4))
                    draw_text(screen, bundle.definition.get("display_name", species_id), (rect.x + 42, rect.y + 10), 14, BG if index == manager.selected_species else TEXT, index == manager.selected_species)
            species_scroll.configure(len(manager.species_ids), 8)
            species_scroll.value = manager.species_offset
            if species_scroll.maximum:
                species_scroll.draw(screen, pygame.mouse.get_pos())
            for button in individual_buttons:
                button.draw(screen, pygame.mouse.get_pos())

        elif manager.tab == "party":
            draw_text(screen, "現在パーティ（4枠）", (470, 108), 24, ACCENT, True)
            party = StateStore.party_records(manager.state, manager.monsters)
            for index in range(4):
                rect = pygame.Rect(470, 150 + index * 90, 340, 76)
                pygame.draw.rect(screen, PANEL_ALT, rect, border_radius=7)
                if index < len(party):
                    member = party[index]
                    image = portrait(member.species_id, 58)
                    if image:
                        screen.blit(image, (rect.x + 8, rect.y + 9))
                    draw_text(screen, f"{index + 1}. {member.name}", (rect.x + 78, rect.y + 10), 18, GOOD, True)
                    draw_text(screen, f"Lv{member.level}  {member.species_id}  AI:{member.ai.get('tactic', 'balanced')}", (rect.x + 78, rect.y + 40), 13, MUTED)
                else:
                    draw_text(screen, f"{index + 1}. 空き", (rect.x + 20, rect.y + 25), 17, MUTED)
            draw_text(screen, f"保存パーティ  {len(manager.presets)}件・上限なし", (835, 108), 20, ACCENT, True)
            for row, path in enumerate(manager.presets[manager.preset_offset:manager.preset_offset + 8]):
                index = manager.preset_offset + row
                data = read_json(path)
                members = sum(1 for item in data.get("members", []) if item)
                rect = pygame.Rect(835, 150 + row * 47, 330, 40)
                pygame.draw.rect(screen, SELECTED if index == manager.selected_preset else PANEL_ALT, rect, border_radius=6)
                draw_text(screen, str(data.get("name", path.stem)), (rect.x + 9, rect.y + 5), 15, TEXT, True)
                draw_text(screen, f"{members}/4体  {path.name}", (rect.x + 9, rect.y + 23), 11, MUTED)
            preset_scroll.configure(len(manager.presets), 8)
            preset_scroll.value = manager.preset_offset
            if preset_scroll.maximum:
                preset_scroll.draw(screen, pygame.mouse.get_pos())
            draw_text(screen, "左の所有個体を選択して追加・除外します。パーティの枠をクリックするとその個体を選択します。", (470, 530), 14, MUTED)
            for button in party_buttons:
                button.draw(screen, pygame.mouse.get_pos())

        else:
            draw_text(screen, "取り込み・模擬戦", (470, 108), 24, ACCENT, True)
            pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(470, 155, 330, 110), border_radius=8)
            draw_text(screen, "個体フォルダの再走査", (490, 172), 19, TEXT, True)
            draw_wrapped(screen, "imports/acquire に置いた個体フォルダを通常獲得します。重複IDや不正データはスキップします。", pygame.Rect(490, 205, 290, 52), 14, MUTED)
            pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(830, 155, 330, 110), border_radius=8)
            draw_text(screen, "インポート個体との模擬戦", (850, 172), 19, TEXT, True)
            draw_wrapped(screen, "imports/simulation の個体と戦います。模擬戦では双方のAIを更新しません。", pygame.Rect(850, 205, 290, 52), 14, MUTED)
            draw_wrapped(screen, "個体データは monster.json と ai.json を含む1体1フォルダ形式です。所有数に上限はありません。", pygame.Rect(500, 390, 650, 80), 17, WARN)
            for button in tool_buttons:
                button.draw(screen, pygame.mouse.get_pos())

        warning = any(word in manager.status for word in ("できません", "ありません", "空です", "不正"))
        draw_status_bar(screen, manager.status, pygame.Rect(20, 720, 1195, 45), warning=warning)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()


