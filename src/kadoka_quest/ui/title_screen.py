# {
#   責務: [title_screen: タイトルとセーブ選択の表示・入力状態を所有し、保存や起動の要求だけを呼出元へ返します]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Callable

import pygame

from kadoka_quest.ui.game_ui import (
    ACCENT, BG, MUTED, TEXT, Button, TextField, draw_cursor, draw_frame, navigation_event,
    draw_text, draw_text_clipped, draw_wrapped, font,
)


# {
#   責務: [TitleScreen: 黒地のタイトル、名前付きセーブ一覧、新規作成・複製フォームを表示します]
#   フィールド: [
#     names: 表示するセーブ名の独立一覧
#     selected: 一覧で選択中の位置
#     mode: home・profiles・new・copyの表示画面
#     focus: 現在画面のキーボード選択位置
#     offset: セーブ一覧の先頭行
#     name_field: 新規作成・複製先の名前入力
#     status: 保存・起動の結果を表示する説明
#     active_name: 次回起動に使われる保存済み選択名
#     buttons: 操作IDごとのゲーム専用ボタン
#     _action: 呼出元へ一度返す保存・起動要求
#   ]
# }
class TitleScreen:
    SIZE = (1040, 720)
    PAGE_ROWS = 7
    PROFILE_RECT = pygame.Rect(220, 192, 600, 308)
    GROUPS = {
        "home": ("play", "profiles", "new", "quit"),
        "profiles": ("load", "copy", "back"),
        "new": ("create", "form_back"),
        "copy": ("save_copy", "form_back"),
    }

    # {
    #   責務: [__init__: タイトルの操作部品と、保存先を参照しない表示状態を作ります]
    #   処理: [
    #     1: 名前一覧と選択状態を初期化します
    #     2: 各画面の固定ボタンを一度だけ作ります
    #   ]
    #   引数: [
    #     self: タイトル表示の所有者
    #     button_factory: 表示部品の生成関数。検査時も同じ操作経路を使います
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, button_factory: Callable = Button) -> None:
        self.names: list[str] = []
        self.selected = 0
        self.mode = "home"
        self.focus = 0
        self.offset = 0
        self.name_field = TextField(pygame.Rect(252, 300, 536, 52), "")
        self.status = ""
        self.active_name = ""
        self._action: str | None = None
        definitions = (
            ("play", "ゲームを開始", (330, 292, 380, 52)),
            ("profiles", "セーブデータを選ぶ", (330, 358, 380, 52)),
            ("new", "新規作成", (330, 424, 380, 52)),
            ("quit", "終了", (330, 490, 380, 52)),
            ("load", "選択データを読み込む", (220, 528, 288, 48)),
            ("copy", "別名保存", (524, 528, 136, 48)),
            ("back", "戻る", (676, 528, 144, 48)),
            ("create", "新規作成", (252, 398, 252, 48)),
            ("save_copy", "別名保存", (252, 398, 252, 48)),
            ("form_back", "戻る", (536, 398, 252, 48)),
        )
        # ボタンはUI要求だけを設定し、ファイル操作やプロセス起動を実行しません。
        self.buttons = {
            key: button_factory(pygame.Rect(rect), label, lambda key=key: self._activate(key))
            for key, label, rect in definitions
        }

    # {
    #   責務: [set_profiles: 呼出元が読み込んだセーブ名と現在の選択を表示へ反映します]
    #   処理: [
    #     1: 一覧を独立コピーします
    #     2: 選択名を復元して見える行へスクロールします
    #   ]
    #   引数: [
    #     self: タイトル表示の所有者
    #     names: 保存機能から渡されたセーブ名一覧
    #     active_name: 次回起動に使われる保存済み選択名
    #     select_name: 一覧で選択する名前。省略時は現在の選択を維持します
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def set_profiles(self, names: list[str], active_name: str, select_name: str | None = None) -> None:
        # 保存処理が一覧を置き換えても、現在見ている名前を可能な限り維持します。
        previous = select_name or self.selected_name()
        self.names = list(names)
        self.active_name = active_name
        self.selected = self.names.index(previous) if previous in self.names else 0
        self._reveal_selection()

    # {
    #   責務: [selected_name: 現在選択中のセーブ名を返します]
    #   処理: [1: 一覧が空なら空文字列を返し、存在する選択だけを読み取ります]
    #   引数: [self: タイトル表示の所有者]
    #   戻り値: [name: 選択中のセーブ名。未選択なら空文字列（str）]
    # }
    def selected_name(self) -> str:
        return self.names[self.selected] if self.names else ""

    # {
    #   責務: [show_home: 操作結果を保ったままタイトルのゲーム開始項目へ戻します]
    #   処理: [1: 名前入力を終了し、ホーム画面の先頭へフォーカスを戻します]
    #   引数: [self: タイトル表示の所有者]
    #   戻り値: [result: なし（None）]
    # }
    def show_home(self) -> None:
        self.mode, self.focus = "home", 0
        self.name_field.active = False

    # {
    #   責務: [_activate: 選択項目を画面遷移または保存・起動要求へ変換します]
    #   処理: [
    #     1: 画面を開く操作は表示状態を更新します
    #     2: 実処理が必要な操作は要求IDだけを保持します
    #   ]
    #   引数: [
    #     self: タイトル表示の所有者
    #     action: 現在画面のボタンから渡される操作ID
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def _activate(self, action: str) -> None:
        # 保存機能をUI内で呼ばず、画面を開く操作と外部への要求を分けます。
        if action == "profiles":
            self.mode, self.focus = "profiles", -1
            self._reveal_selection()
        elif action in {"new", "copy"}:
            self.mode, self.focus = action, -1
            self.name_field.value = ""
            self.name_field.active = True
        elif action in {"back", "form_back"}:
            self.show_home()
        else:
            self._action = action

    # {
    #   責務: [_reveal_selection: 選択行が七行の表示領域に収まるよう一覧の先頭を調整します]
    #   処理: [
    #     1: 空一覧と選択の上限を補正します
    #     2: 選択行を可視範囲へ入れます
    #   ]
    #   引数: [self: タイトル表示の所有者]
    #   戻り値: [result: なし（None）]
    # }
    def _reveal_selection(self) -> None:
        # セーブ一覧が縮んだ場合も、存在しない行を選択したままにしません。
        self.selected = max(0, min(self.selected, len(self.names) - 1))
        self.offset = min(self.offset, self.selected)
        self.offset = max(self.offset, self.selected - self.PAGE_ROWS + 1, 0)

    # {
    #   責務: [_profile_key: 一覧の選択・ページ送りと、選択したセーブの読込要求を処理します]
    #   処理: [
    #     1: 矢印・Home・End・Pageキーで選択を動かします
    #     2: 決定時だけ読込要求を返します
    #   ]
    #   引数: [
    #     self: タイトル表示の所有者
    #     key: 一覧へ入力されたpygameキーコード
    #   ]
    #   戻り値: [handled: 一覧が入力を処理した場合はtrue（bool）]
    # }
    def _profile_key(self, key: int) -> bool:
        # ページ送りの幅は描画する行数と共用し、空一覧では読込要求を出しません。
        movement = {pygame.K_UP: -1, pygame.K_DOWN: 1, pygame.K_PAGEUP: -self.PAGE_ROWS, pygame.K_PAGEDOWN: self.PAGE_ROWS}
        if key in movement:
            self.selected += movement[key]
        elif key == pygame.K_HOME:
            self.selected = 0
        elif key == pygame.K_END:
            self.selected = len(self.names) - 1
        elif key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_z, pygame.K_SPACE}:
            if self.names:
                self._action = "load"
        else:
            return False
        self._reveal_selection()
        return True

    # {
    #   責務: [handle: マウスとキーボードを現在のタイトル画面だけへ渡します]
    #   処理: [
    #     1: 閉じる・戻るを判定し、決定操作のキーリピートを拒否します
    #     2: 入力欄と一覧とボタンへ順に入力を渡します
    #     3: 実処理の要求を一度返します
    #   ]
    #   引数: [
    #     self: タイトル表示の所有者
    #     event: pygameから受け取った入力イベント
    #   ]
    #   戻り値: [action: 保存・起動・終了の操作ID。表示だけの操作ならNone（str | None）]
    # }
    def handle(self, event: pygame.event.Event) -> str | None:
        self._action = None
        event = navigation_event(event)
        if event.type == pygame.QUIT:
            return "quit"
        group = self.GROUPS[self.mode]
        form = self.mode in {"new", "copy"}
        if event.type == pygame.KEYDOWN:
            # 決定キーの長押しで、作成直後にゲームを起動したりプロセスを増やしたりしません。
            if getattr(event, "repeat", False):
                if event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE}:
                    return None
                if not (form and self.name_field.active) and event.key in {pygame.K_z, pygame.K_SPACE, pygame.K_x}:
                    return None
            if event.key == pygame.K_ESCAPE or (event.key == pygame.K_x and not (form and self.name_field.active)):
                self.show_home() if self.mode != "home" else self._activate("quit")
            elif event.key == pygame.K_TAB:
                # 入力欄・一覧を-1として、ボタンとの往復を一つの巡回順にします。
                first = -1 if self.mode != "home" else 0
                delta = -1 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 1
                self.focus = (self.focus - first + delta) % (len(group) - first) + first
                self.name_field.active = form and self.focus == -1
            elif form and self.name_field.active:
                if event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                    self._action = "create" if self.mode == "new" else "save_copy"
                else:
                    self.name_field.handle(event)
            elif self.mode == "profiles" and self.focus == -1 and self._profile_key(event.key):
                pass
            elif event.key in {pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT}:
                self.focus = (self.focus + (1 if event.key in {pygame.K_DOWN, pygame.K_RIGHT} else -1)) % len(group)
            elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_z, pygame.K_SPACE}:
                action = group[max(0, self.focus)]
                if action not in {"play", "load", "copy"} or self.names:
                    self._activate(action)
            return self._action
        if self.mode == "profiles" and event.type == pygame.MOUSEWHEEL:
            self.selected -= event.y
            self.focus = -1
            self._reveal_selection()
        if form:
            self.name_field.handle(event)
            if self.name_field.active:
                self.focus = -1
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.mode == "profiles":
            if self.PROFILE_RECT.collidepoint(event.pos):
                row = (event.pos[1] - self.PROFILE_RECT.y) // 44
                if self.offset + row < len(self.names):
                    self.selected, self.focus = self.offset + row, -1
        for index, key in enumerate(group):
            button = self.buttons[key]
            button.enabled = key not in {"play", "load", "copy"} or bool(self.names)
            if event.type == pygame.MOUSEBUTTONDOWN and button.rect.collidepoint(event.pos):
                self.focus = index
            if button.handle(event):
                break
        return self._action

    # {
    #   責務: [draw: 現在のタイトル画面を黒地・白枠・限定色で描画します]
    #   処理: [
    #     1: 画面別の内容を描きます
    #     2: フォーカス付きボタンと結果説明を描きます
    #   ]
    #   引数: [
    #     self: タイトル表示の所有者
    #     screen: 1040×720の描画先
    #     mouse: 現在のマウス座標
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def draw(self, screen: pygame.Surface, mouse: tuple[int, int]) -> None:
        screen.fill(BG)
        if self.mode == "home":
            self._draw_home(screen)
        elif self.mode == "profiles":
            self._draw_profiles(screen)
        else:
            self._draw_form(screen)
        for index, key in enumerate(self.GROUPS[self.mode]):
            button = self.buttons[key]
            button.enabled = key not in {"play", "load", "copy"} or bool(self.names)
            button.focused = self.focus == index
            button.draw(screen, mouse)
        # 長い検査・保存エラーは枠内で折り返し、操作領域を押し出しません。
        draw_wrapped(screen, self.status, pygame.Rect(160, 608, 720, 56), 16, MUTED, 6)
        hint = "↑↓ 選択   Enter / Z 決定   Esc / X 戻る"
        if self.mode in {"new", "copy"}:
            hint = "名前を入力   Enter 決定   Tab 項目移動   Esc 戻る"
        elif self.mode == "profiles":
            hint = "↑↓ 選択   Enter 読込   Tab 操作へ   Esc 戻る"
        draw_text(screen, hint, (200, 680), 16, MUTED)

    # {
    #   責務: [_draw_home: ゲーム開始を中心に、作品名と選択済みの記録を表示します]
    #   処理: [
    #     1: ドット文字の作品名と短い案内を描きます
    #     2: 現在選択中のセーブ名を表示します
    #   ]
    #   引数: [
    #     self: タイトル表示の所有者
    #     screen: タイトルの描画先
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def _draw_home(self, screen: pygame.Surface) -> None:
        # 装飾は小さな矩形だけに抑え、ゲーム開始項目の周囲に余白を残します。
        title = "KADOKA QUEST"
        width = font(48).size(title)[0]
        draw_text(screen, title, ((self.SIZE[0] - width) // 2, 96), 48, TEXT)
        pygame.draw.line(screen, TEXT, (330, 170), (710, 170), 2)
        draw_text(screen, "小さな仲間と、まだ知らない世界へ。", (264, 200), 16, MUTED)
        draw_text_clipped(screen, "記録  " + (self.selected_name() or "なし"),
                          pygame.Rect(330, 248, 380, 28), 16, ACCENT)

    # {
    #   責務: [_draw_profiles: 七行のセーブ名と選択位置、表示範囲を描画します]
    #   処理: [
    #     1: 現在のページだけを描きます
    #     2: 選択と使用中の記録を別の印で示します
    #   ]
    #   引数: [
    #     self: タイトル表示の所有者
    #     screen: セーブ選択の描画先
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def _draw_profiles(self, screen: pygame.Surface) -> None:
        draw_text(screen, "冒険の記録", (220, 100), 32)
        draw_text(screen, "つづける記録を選んでください。", (220, 148), 16, MUTED)
        draw_frame(screen, self.PROFILE_RECT.inflate(8, 8))
        for row, name in enumerate(self.names[self.offset:self.offset + self.PAGE_ROWS]):
            index = self.offset + row
            rect = pygame.Rect(220, 192 + row * 44, 600, 44)
            selected = index == self.selected
            if selected:
                draw_cursor(screen, (232, rect.y + 16), ACCENT if self.focus == -1 else TEXT)
            label = name + ("  * 使用中" if name == self.active_name else "")
            draw_text_clipped(screen, label, pygame.Rect(264, rect.y + 10, 536, 28),
                              16, ACCENT if selected else TEXT)
        if not self.names:
            draw_text(screen, "記録がありません。新規作成してください。", (248, 220), 16, MUTED)
        position = f"{self.selected + 1} / {len(self.names)}" if self.names else "0 / 0"
        draw_text(screen, position, (724, 152), 16, MUTED)

    # {
    #   責務: [_draw_form: 新規作成または別名保存に必要な名前入力だけを表示します]
    #   処理: [
    #     1: 操作目的と複製元を示します
    #     2: 入力欄を同じ白枠の中へ配置します
    #   ]
    #   引数: [
    #     self: タイトル表示の所有者
    #     screen: 名前入力の描画先
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def _draw_form(self, screen: pygame.Surface) -> None:
        draw_frame(screen, pygame.Rect(220, 192, 600, 300))
        title = "新しい冒険" if self.mode == "new" else "冒険の記録を複製"
        draw_text(screen, title, (252, 214), 32)
        description = "セーブデータ名を入力してください。"
        if self.mode == "copy":
            description = "複製元  " + self.selected_name()
        draw_text_clipped(screen, description, pygame.Rect(252, 266, 536, 24), 16, MUTED)
        self.name_field.draw(screen)
