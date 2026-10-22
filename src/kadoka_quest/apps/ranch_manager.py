# {
#   責務: [ranch_manager: Playerの牧場で所有個体、AI学習傾向、パーティとプリセットを操作する]
#   フィールド: []
# }
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pygame

from kadoka_quest.apps.ai_inspector import AiInspector
from kadoka_quest.core.ai import TACTICS
from kadoka_quest.core.monster import calculate_stats
from kadoka_quest.data.jsonio import read_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore
from kadoka_quest.paths import ASSET_ROOT
from kadoka_quest.ui.game_ai_tendency_panel import draw_ai_tendencies
from kadoka_quest.ui.game_labels import TACTIC_LABELS
from kadoka_quest.ui.game_ui import (
    ACCENT,
    BG,
    MUTED,
    PANEL_ALT,
    SELECTED,
    TEXT,
    Button,
    ScrollBar,
    draw_text,
    draw_text_clipped,
    draw_frame,
    draw_cursor,
    draw_wrapped,
    init_pygame,
    move_list_selection,
    navigation_event,
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


# {
#   責務: [RanchManager: Player-facing ownership and party management used by the in-world ranch.]
#   フィールド: [
#     repository: データ取得先
#     monsters: モンスター一覧
#     states: 現在パーティを含む状態を保存するStore
#     state: 読み込み済みのゲーム状態
#     parties: パーティプリセットを読み書きするStore
#     records: 個体レコード一覧
#     selected: 選択中
#     offset: 表示位置
#     tab: 個体情報またはパーティ編成を示すタブ識別子
#     presets: プリセット一覧
#     selected_preset: 選択中・プリセット
#     preset_offset: プリセット・表示位置
#     preset_names: 再読み込み時に取得したプリセットの表示名
#     status: 画面下部へ表示する直前の操作結果
#     skills: スキル一覧
#   ]
# }
class RanchManager:
    """Player-facing ownership and party management used by the in-world ranch."""

    # {
    #   責務: [__init__: 所有個体と現在パーティを読み込み、牧場の初期選択を用意する]
    #   処理: [1: 各Storeから状態を取得し、画面の選択位置と一覧を初期化する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self) -> None:
        # 保存形式を変えず、初期状態と個体の取得を各Storeへ委譲する。
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

    # {
    #   責務: [refresh: 所有個体とプリセットを再取得し、可能なら選択中の個体を維持する]
    #   処理: [1: 個体識別子から選択を復元し、プリセット表示名と各一覧の位置を更新する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def refresh(self) -> None:
        # 外部の学習更新を読み込み、同じ個体の表示を継続できるようにする。
        self.skills = self.repository.get_skills()
        current_id = self.records[self.selected].monster_id if self.records and self.selected < len(self.records) else None
        self.records = self.monsters.list_records()
        if current_id:
            self.selected = next((index for index, record in enumerate(self.records) if record.monster_id == current_id), 0)
        self.selected = max(0, min(self.selected, max(0, len(self.records) - 1)))
        self.offset = max(0, min(self.offset, max(0, len(self.records) - 9)))
        self.presets = self.parties.list_presets()
        self.preset_names = {path: str(read_json(path).get("name", path.stem)) for path in self.presets}
        self.selected_preset = max(0, min(self.selected_preset, max(0, len(self.presets) - 1)))
        self.preset_offset = max(0, min(self.preset_offset, max(0, len(self.presets) - 8)))

    # {
    #   責務: [selected_record: 所有一覧で選択している個体を返す]
    #   処理: [1: 所有一覧が空でなければ選択位置の個体を返す]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 選択中の個体レコード。所有一覧が空の場合はNone]
    # }
    @property
    def selected_record(self):
        # 空一覧では操作対象がないことを呼び出し元へ明示する。
        return self.records[self.selected] if self.records else None

    # {
    #   責務: [selected_tendencies: 選択中の個体から表示用のAI学習傾向を取得する]
    #   処理: [1: 選択中のAIとスキル定義をAiInspectorの要約処理へ渡す]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 学習傾向の一覧。個体がない場合は空一覧]
    # }
    @property
    def selected_tendencies(self) -> list[dict]:
        # 画面で学習計算を重複実装せず、既存の要約機能を使用する。
        record = self.selected_record
        return AiInspector.summarize_tendencies(record.ai, self.skills) if record else []

    # {
    #   責務: [add_party: 選択中の個体を現在パーティへ追加して状態を保存する]
    #   処理: [1: 個体の存在、重複、4枠上限を確認し、追加できる場合だけ保存する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def add_party(self) -> None:
        # 重複や満員の場合は編成を変更せず、操作結果だけを表示する。
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

    # {
    #   責務: [remove_party: 所有個体を残したまま選択中の個体を現在パーティから外す]
    #   処理: [1: 選択中の識別子を編成から除き、現在パーティの状態を保存する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def remove_party(self) -> None:
        # 個体やAIの保存データを削除せず、現在パーティだけを変更する。
        record = self.selected_record
        if not record:
            return
        self.state["current_party"] = [item for item in self.state.get("current_party", []) if item != record.monster_id]
        self.states.save(self.state)
        self.status = f"{record.name} をパーティから外しました。個体は牧場に残ります。"

    # {
    #   責務: [reset_ai: 選択中の個体のAIを初期化し、学習傾向の表示を更新する]
    #   処理: [1: MonsterStoreへAI初期化を依頼し、個体を再取得する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def reset_ai(self) -> None:
        # AI初期化の対象を選択中の個体だけに限定する。
        record = self.selected_record
        if not record:
            return
        self.monsters.reset_ai(record.monster_id)
        self.status = f"{record.name} のAIだけ初期化しました。"
        self.refresh()

    # {
    #   責務: [cycle_tactic: 選択中の個体の行動指針を定義済みの次の指針へ切り替える]
    #   処理: [1: 次の指針をStoreへ保存し、個体の表示を再取得する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def cycle_tactic(self) -> None:
        # 行動指針の保存形式はStoreへ任せ、画面には操作結果を返す。
        record = self.selected_record
        if not record:
            return
        current = str(record.ai.get("tactic", "balanced"))
        index = TACTICS.index(current) if current in TACTICS else 0
        next_tactic = TACTICS[(index + 1) % len(TACTICS)]
        self.monsters.set_tactic(record.monster_id, next_tactic)
        self.status = f"{record.name} の行動指針を {TACTIC_LABELS.get(next_tactic, next_tactic)} に変更しました。"
        self.refresh()

    # {
    #   責務: [save_preset: 現在パーティを日時付きプリセットへ保存して一覧で選択する]
    #   処理: [1: 編成を保存して一覧を再取得し、保存した項目が見える位置へ移動する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_preset(self) -> None:
        # 現在パーティの識別子を既存のプリセット形式で保存する。
        name = "編成_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.parties.save(name, list(self.state.get("current_party", [])))
        self.status = f"{path.name} を保存しました。"
        self.refresh()
        self.selected_preset = self.presets.index(path)
        self.preset_offset = max(0, self.selected_preset - 7)

    # {
    #   責務: [update_preset: 選択中のプリセットを現在パーティで更新する]
    #   処理: [1: プリセットがなければ新規保存し、存在する場合は選択ファイルを更新する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def update_preset(self) -> None:
        # 選択中のファイルだけへ現在の編成を書き込む。
        if not self.presets:
            self.save_preset()
            return
        path = self.presets[self.selected_preset]
        name = str(read_json(path).get("name", path.stem))
        self.parties.update(path, name, list(self.state.get("current_party", [])))
        self.status = f"{path.name} を現在編成で更新しました。"

    # {
    #   責務: [load_preset: 選択プリセットに含まれる所有個体を現在パーティへ反映して保存する]
    #   処理: [1: 存在する個体だけを編成へ保存し、欠損による空き枠の数を表示する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def load_preset(self) -> None:
        # 保存済み個体が見つからない枠を除き、読込結果の空き数を表示する。
        if not self.presets:
            self.status = "保存済みプリセットがありません。"
            return
        path = self.presets[self.selected_preset]
        loaded = self.parties.load(path, self.monsters)
        self.state["current_party"] = [record.monster_id for record in loaded if record]
        self.states.save(self.state)
        missing = sum(1 for record in loaded if record is None)
        self.status = f"{path.name} を読み込みました（空き{missing}）。"


# {
#   責務: [main: Playerの牧場ウィンドウで一覧選択と操作を受け付け、現在の管理状態を表示する]
#   処理: [
#     1: 個体とプリセットの管理アプリ、操作ボタン、スクロール状態を用意する
#     2: キーとマウスの入力を選択移動または管理アプリの操作へ渡す
#     3: 現在の個体、パーティ、学習傾向、操作結果を白黒の画面へ描く
#   ]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def main() -> None:
    screen = init_pygame("kadoka quest - 牧場", (1160, 740))
    clock = pygame.time.Clock()
    manager = RanchManager()
    running = True
    smoke = smoke_frames()
    frames = 0
    keyboard_focus = 0
    portrait_cache: dict[tuple[str, int], pygame.Surface | None] = {}

    # {
    #   責務: [portrait: モンスター画像を指定サイズで取得し、読込失敗を含めて画面終了まで保持する]
    #   処理: [1: 未読込の画像だけ最近傍法で拡大し、同じ指定の画像を再利用する]
    #   引数: [
    #     species_id: 画像定義を取得するモンスター種族の識別子
    #     size: 画像の一辺の画素数
    #   ]
    #   戻り値: [result: 指定サイズの画像。画像を読み込めない場合はNone]
    # }
    def portrait(species_id: str, size: int) -> pygame.Surface | None:
        # 欠落画像を含めて結果を保持し、毎フレームのファイルアクセスを避ける。
        key = (species_id, size)
        if key in portrait_cache:
            return portrait_cache[key]
        try:
            bundle = manager.repository.get_species(species_id)
            source = pygame.image.load(str(ASSET_ROOT / str(bundle.definition.get("portrait_path", "")))).convert_alpha()
            portrait_cache[key] = pygame.transform.scale(source, (size, size))
            return portrait_cache[key]
        except (OSError, pygame.error, KeyError):
            portrait_cache[key] = None
            return None

    tab_buttons = [
        Button(pygame.Rect(455, 25, 180, 42), "個体情報", lambda: setattr(manager, "tab", "individual")),
        Button(pygame.Rect(645, 25, 190, 42), "パーティ編成", lambda: setattr(manager, "tab", "party")),
    ]
    individual_buttons = [
        Button(pygame.Rect(455, 315, 155, 42), "パーティ追加", manager.add_party),
        Button(pygame.Rect(620, 315, 155, 42), "パーティ解除", manager.remove_party),
        Button(pygame.Rect(785, 315, 155, 42), "行動指針切替", manager.cycle_tactic),
        Button(pygame.Rect(950, 315, 155, 42), "AI初期化", manager.reset_ai),
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
            event = navigation_event(event)
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.WINDOWFOCUSGAINED or (event.type == pygame.KEYDOWN and event.key == pygame.K_F5):
                manager.refresh()

            owned_scroll.configure(len(manager.records), 9)
            preset_scroll.configure(len(manager.presets), 8)
            owned_scroll.value = manager.offset
            preset_scroll.value = manager.preset_offset
            active_buttons = individual_buttons if manager.tab == "individual" else party_buttons
            visible_buttons = tab_buttons + active_buttons
            list_count = 2 if manager.tab == "party" else 1
            keyboard_focus = min(keyboard_focus, list_count + len(visible_buttons) - 1)
            # Tabは一覧と操作ボタンを巡回し、方向キーは選択行を表示範囲へ追従させる。
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    step = -1 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 1
                    keyboard_focus = (keyboard_focus + step) % (list_count + len(visible_buttons))
                elif keyboard_focus == 0:
                    manager.selected, manager.offset = move_list_selection(
                        manager.selected, manager.offset, len(manager.records), 9, event.key,
                    )
                elif keyboard_focus == 1 and list_count == 2:
                    manager.selected_preset, manager.preset_offset = move_list_selection(
                        manager.selected_preset, manager.preset_offset, len(manager.presets), 8, event.key,
                    )
                elif event.key in {pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT}:
                    step = -1 if event.key in {pygame.K_UP, pygame.K_LEFT} else 1
                    keyboard_focus = list_count + (keyboard_focus - list_count + step) % len(visible_buttons)
            for index, button in enumerate(visible_buttons):
                button.focused = keyboard_focus == list_count + index
            owned_scroll.value = manager.offset
            preset_scroll.value = manager.preset_offset
            handled = owned_scroll.handle(event)
            if manager.tab == "party":
                handled = preset_scroll.handle(event) or handled
            manager.offset = owned_scroll.value
            manager.preset_offset = preset_scroll.value
            for index, button in enumerate(visible_buttons):
                if button.handle(event):
                    handled = True
                    keyboard_focus = list_count + index
                    break

            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if 25 <= event.pos[0] < 405 and 120 <= event.pos[1] < 606:
                    row = (event.pos[1] - 120) // 54
                    index = manager.offset + row
                    if 0 <= index < len(manager.records):
                        manager.selected = index
                        keyboard_focus = 0
                elif manager.tab == "party" and 805 <= event.pos[0] < 1105 and 150 <= event.pos[1] < 526:
                    row = (event.pos[1] - 150) // 47
                    index = manager.preset_offset + row
                    if 0 <= index < len(manager.presets):
                        manager.selected_preset = index
                        keyboard_focus = 1

            if event.type == pygame.MOUSEWHEEL:
                mouse_x, _ = pygame.mouse.get_pos()
                if mouse_x < 435:
                    manager.offset = max(0, min(owned_scroll.maximum, manager.offset - event.y))
                elif manager.tab == "party":
                    manager.preset_offset = max(0, min(preset_scroll.maximum, manager.preset_offset - event.y))

        screen.fill(BG)
        draw_text(screen, "モンスター牧場", (24, 24), 32, TEXT)
        draw_text(screen, f"所有 {len(manager.records)}体", (25, 66), 16, MUTED)
        for button, tab in zip(tab_buttons, ("individual", "party")):
            button.selected = manager.tab == tab
            button.draw(screen, pygame.mouse.get_pos())

        # 所有一覧と詳細は固定の矩形へ分け、個体数にかかわらず画面外へ伸ばさない。
        draw_frame(screen, pygame.Rect(15, 90, 415, 565), ACCENT if keyboard_focus == 0 else TEXT)
        draw_text(screen, "所有個体", (30, 98), 17, MUTED, True)
        if not manager.records:
            draw_wrapped(screen, "所有個体がありません。", pygame.Rect(35, 150, 350, 80), 16, MUTED)
        party_ids = set(manager.state.get("current_party", []))
        for row, record in enumerate(manager.records[manager.offset:manager.offset + 9]):
            index = manager.offset + row
            rect = pygame.Rect(25, 120 + row * 54, 378, 47)
            draw_frame(screen, rect, ACCENT if index == manager.selected else PANEL_ALT, 2, SELECTED if index == manager.selected else BG)
            if index == manager.selected:
                draw_cursor(screen, (rect.x + 6, rect.centery - 5))
            image = portrait(record.species_id, 32)
            if image:
                screen.blit(image, (rect.x + 22, rect.y + 7))
            marker = "★ " if record.monster_id in party_ids else ""
            draw_text_clipped(screen, marker + record.name, pygame.Rect(rect.x + 62, rect.y + 3, rect.width - 72, 21), 16)
            draw_text_clipped(screen, f"Lv{record.level}  {record.species_id}", pygame.Rect(rect.x + 62, rect.y + 25, rect.width - 72, 21), 16, MUTED)
        owned_scroll.configure(len(manager.records), 9)
        owned_scroll.value = manager.offset
        if owned_scroll.maximum:
            owned_scroll.draw(screen, pygame.mouse.get_pos())

        draw_frame(screen, pygame.Rect(445, 90, 700, 565))
        record = manager.selected_record
        if manager.tab == "individual":
            draw_text(screen, "個体情報", (455, 108), 16, TEXT)
            if record:
                image = portrait(record.species_id, 120)
                if image:
                    screen.blit(image, (455, 145))
                draw_text_clipped(screen, record.name, pygame.Rect(595, 145, 245, 26), 16, TEXT)
                draw_text_clipped(screen, f"{record.species_id} / Lv{record.level} / +{len(record.plus_choices)}", pygame.Rect(595, 182, 245, 24), 16, MUTED)
                draw_text_clipped(screen, f"装備: {record.equipment_id or 'なし'}", pygame.Rect(595, 210, 245, 24), 16, MUTED)
                tactic = str(record.ai.get("tactic", "balanced"))
                draw_text_clipped(screen, f"行動指針: {TACTIC_LABELS.get(tactic, tactic)}", pygame.Rect(595, 238, 245, 24), 16, MUTED)
                stats = calculate_stats(manager.repository, record)
                for index, key in enumerate(("hp", "mp", "attack", "defense", "speed", "magic")):
                    x = 860 + (index % 2) * 125
                    y = 142 + (index // 2) * 43
                    draw_frame(screen, pygame.Rect(x, y, 115, 35), MUTED, 2)
                    draw_text(screen, f"{STAT_LABELS[key]} {stats[key]}", (x + 8, y + 8), 14)
            for button in individual_buttons:
                button.enabled = record is not None
                button.draw(screen, pygame.mouse.get_pos())
            draw_ai_tendencies(screen, manager.selected_tendencies, pygame.Rect(455, 380, 650, 240))
        else:
            draw_text(screen, "現在パーティ（4枠）", (455, 108), 16, TEXT)
            party = StateStore.party_records(manager.state, manager.monsters)
            for index in range(4):
                rect = pygame.Rect(455, 150 + index * 90, 325, 76)
                draw_frame(screen, rect, MUTED, 2)
                if index < len(party):
                    member = party[index]
                    image = portrait(member.species_id, 58)
                    if image:
                        screen.blit(image, (rect.x + 8, rect.y + 9))
                    draw_text_clipped(screen, f"{index + 1}. {member.name}", pygame.Rect(rect.x + 78, rect.y + 10, rect.width - 86, 24), 16, TEXT)
                    draw_text_clipped(screen, f"Lv{member.level} {member.species_id}", pygame.Rect(rect.x + 78, rect.y + 40, rect.width - 86, 24), 16, MUTED)
                else:
                    draw_text(screen, f"{index + 1}. 空き", (rect.x + 20, rect.y + 25), 17, MUTED)
            draw_text(screen, f"保存パーティ {len(manager.presets)}件", (805, 108), 16, ACCENT if keyboard_focus == 1 else TEXT)
            if not manager.presets:
                draw_wrapped(screen, "保存パーティはありません。新規保存で現在の編成を残せます。", pygame.Rect(815, 165, 280, 120), 16, MUTED)
            for row, path in enumerate(manager.presets[manager.preset_offset:manager.preset_offset + 8]):
                index = manager.preset_offset + row
                rect = pygame.Rect(805, 150 + row * 47, 300, 40)
                draw_frame(screen, rect, ACCENT if index == manager.selected_preset else PANEL_ALT, 2, SELECTED if index == manager.selected_preset else BG)
                if index == manager.selected_preset:
                    draw_cursor(screen, (rect.x + 7, rect.centery - 5))
                draw_text_clipped(screen, manager.preset_names.get(path, path.stem), pygame.Rect(rect.x + 25, rect.y + 8, rect.width - 33, 24), 16)
            preset_scroll.configure(len(manager.presets), 8)
            preset_scroll.value = manager.preset_offset
            if preset_scroll.maximum:
                preset_scroll.draw(screen, pygame.mouse.get_pos())
            for button in party_buttons:
                button.draw(screen, pygame.mouse.get_pos())

        draw_frame(screen, pygame.Rect(15, 666, 1130, 62), TEXT, 2)
        draw_text_clipped(screen, manager.status, pygame.Rect(30, 674, 1100, 24), 16)
        draw_text(screen, "Tab: 操作先  ↑↓: 選択  Enter: 決定  PgUp/PgDn: 一覧移動  F5: 再読込  Esc: 戻る", (30, 700), 16, MUTED)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
