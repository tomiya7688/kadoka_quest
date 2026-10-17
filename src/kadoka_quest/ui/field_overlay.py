# {
#   責務: [field_overlay: フィールドの会話・一時通知・メニューを描き、メニュー操作を意味コマンドへ変換します]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Sequence

import pygame

from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.ui.game_labels import TACTIC_LABELS
from kadoka_quest.ui.game_ui import ACCENT, BG, MUTED, TEXT, draw_cursor, draw_frame, draw_text, draw_text_clipped, font
from kadoka_quest.ui.game_text import wrap_lines

MENU_BUTTON = pygame.Rect(912, 12, 184, 40)
MENU_PANEL = pygame.Rect(96, 80, 928, 632)
MENU_ITEMS = (
    ("冒険に戻る", "resume", ""),
    ("なかまを管理", "manager", "open"),
    ("行動指針を変える", "field", "tactic.cycle"),
    ("個体を読み込む", "field", "acquire.scan"),
    ("編成を保存", "field", "party.save_preset"),
    ("編成を読み込む", "field", "party.load_next_preset"),
    ("操作の説明", "help", ""),
    ("選んだ個体のAIをリセット", "field", "ai.reset"),
    ("ゲームを終了", "quit", ""),
)
MENU_RECTS = tuple(pygame.Rect(552, 160 + index * 52, 432, 44) for index in range(len(MENU_ITEMS)))
PARTY_RECTS = tuple(pygame.Rect(128, 190 + index * 96, 376, 80) for index in range(4))
HELP_LINES = (
    "フィールドでは矢印またはWASDキーで移動してください。",
    "Spaceキーで正面を調べ、Lキーで持ち物を拾ってください。",
    "1〜4キーで個体を選び、Tキーで行動指針を変えてください。",
    "Rキーで選んだ個体の学習済みAIをリセットできます。",
    "F5キーで取得対象の個体を読み込めます。",
    "F7キーで現在の編成を保存し、F8キーで編成を読み込めます。",
    "模擬戦は街の模擬戦会館から開始してください。",
    "戦闘では矢印で選び、Enterキーまたは1〜4キーで実行してください。",
    "戦闘ではAキーでオートを切り替えられます。",
    "Escキーでメニューを開閉できます。",
)


# {
#   責務: [FieldOverlay: フィールドのメニュー選択と通知の表示寿命を所有し、ゲーム状態を直接変更しません]
#   フィールド: [
#     opened: メニューを表示しているか
#     help_open: メニュー内の操作説明を表示しているか
#     selection: メニューで選択した項目番号
#     message: 最後に受け取った表示文
#     speaker: 会話文に明示されていた話者名
#     lines: 折り返し済みの通知本文
#     page: 通知本文の表示ページ番号
#     shown_at: 通知を受け取ったミリ秒
#     dismissed: 移動操作で会話を閉じたか
#   ]
# }
class FieldOverlay:
    # {
    #   責務: [__init__: 閉じたメニューと空の通知表示を準備します]
    #   処理: [1: UIだけが所有する選択と通知状態を初期化します]
    #   引数: [self: フィールドの重ね描画担当]
    #   戻り値: [result: なし]
    # }
    def __init__(self) -> None:
        self.opened = False
        self.help_open = False
        self.selection = 0
        self.message = ""
        self.speaker = ""
        self.lines: tuple[str, ...] = ()
        self.page = 0
        self.shown_at = 0
        self.dismissed = False

    # {
    #   責務: [observe_message: 新しいフィールド通知を受け取った時だけ話者と本文を表示用に準備します]
    #   処理: [
    #     1: 前回と異なる通知の表示時刻とページを更新します
    #     2: 明示された話者名を取り出し、本文を表示幅で折り返します
    #   ]
    #   引数: [
    #     self: 通知表示を所有するUI
    #     message: ゲームが生成した通知または話者名『本文』形式の会話
    #     now: 通知の表示寿命に使うミリ秒
    #   ]
    #   戻り値: [result: なし。ゲームの通知文字列は変更しません]
    # }
    def observe_message(self, message: str, now: int) -> None:
        if message == self.message:
            return
        self.message = message
        self.shown_at = now
        self.page = 0
        self.dismissed = False
        self.speaker = ""
        body = message
        # ゲームのNPC会話形式だけを分け、通常通知へ架空の話者を付けません。
        if "『" in message and message.endswith("』"):
            self.speaker, body = message.split("『", 1)
            body = body[:-1]
        self.lines = tuple(wrap_lines(body, 992, 16))

    # {
    #   責務: [_activate: 選んだメニュー項目を既存の意味コマンドまたはUI遷移へ変換します]
    #   処理: [1: 説明画面と閉じる操作をUI内で処理し、ゲーム操作は要求だけを返します]
    #   引数: [self: 選択項目を保持するメニュー]
    #   戻り値: [result: 既存のruntimeへ渡す要求一覧。UI操作だけなら空一覧]
    # }
    def _activate(self) -> list[dict]:
        _, target, action = MENU_ITEMS[self.selection]
        if target == "help":
            self.help_open = True
            return []
        self.opened = False
        if target == "resume":
            return []
        if target == "quit":
            return [{"kind": "quit"}]
        # 保存やAIの更新は既存のアプリケーション経路へ委譲します。
        return [{"kind": "command", "target": target, "action": action, "payload": {}}]

    # {
    #   責務: [handle_event: フィールドのメニュー・会話ページ入力を受け取り、消費した入力の要求を返します]
    #   処理: [
    #     1: メニュー開閉時に移動長押しを解除する要求を返します
    #     2: メニュー内の選択・決定・パーティ選択を入力から求めます
    #     3: 会話の次ページだけをUI内で送り、それ以外は既存入力へ渡します
    #   ]
    #   引数: [
    #     self: フィールドのメニュー状態を所有するUI
    #     event: pygameの入力イベント
    #   ]
    #   戻り値: [result: 消費した入力の意味要求一覧。Noneは既存入力へ渡すことを示します]
    # }
    def handle_event(self, event: pygame.event.Event) -> list[dict] | None:
        if event.type == pygame.QUIT:
            return None
        key_down = event.type == pygame.KEYDOWN
        # 決定と開閉は一押しだけで受け付け、長押しで会話やメニューを読み飛ばしません。
        if key_down and getattr(event, "repeat", False) and event.key in {pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
            return []
        clicked = event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1
        toggle = (key_down and event.key == pygame.K_ESCAPE) or (clicked and MENU_BUTTON.collidepoint(event.pos))
        if toggle:
            if self.help_open:
                self.help_open = False
                return []
            self.opened = not self.opened
            # メニューを閉じた直後に主人公が歩き続けないよう、保持中の方向を解除します。
            return [{"kind": "command", "target": "field", "action": "move.stop", "payload": {"direction": direction}} for direction in ("left", "right", "back", "front")]
        if not self.opened:
            if event.type == pygame.JOYHATMOTION and event.value != (0, 0):
                self.dismissed = True
            if key_down and event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
                if not self.dismissed and (self.page + 1) * 3 < len(self.lines):
                    self.page += 1
                    return []
                # 同じ台詞を再び受け取る場合も、移動で閉じた会話を先頭から表示します。
                self.dismissed = False
                self.page = 0
            if key_down and event.key in {pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d}:
                self.dismissed = True
            return None
        if self.help_open:
            if (key_down and event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}) or clicked:
                self.help_open = False
            return []
        if key_down:
            if event.key in {pygame.K_UP, pygame.K_w}:
                self.selection = (self.selection - 1) % len(MENU_ITEMS)
            elif event.key in {pygame.K_DOWN, pygame.K_s, pygame.K_TAB}:
                self.selection = (self.selection + 1) % len(MENU_ITEMS)
            elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE} and not getattr(event, "repeat", False):
                return self._activate()
            elif pygame.K_1 <= event.key <= pygame.K_4:
                return [{"kind": "command", "target": "field", "action": "party.select", "payload": {"index": event.key - pygame.K_1}}]
        if event.type == pygame.MOUSEMOTION or clicked:
            for index, rect in enumerate(MENU_RECTS):
                if rect.collidepoint(event.pos):
                    self.selection = index
                    if clicked:
                        return self._activate()
            if clicked:
                for index, rect in enumerate(PARTY_RECTS):
                    if rect.collidepoint(event.pos):
                        return [{"kind": "command", "target": "field", "action": "party.select", "payload": {"index": index}}]
        return []

    # {
    #   責務: [_draw_message: 会話は話者付きの下段枠へ描き、通常通知は一定時間だけ表示します]
    #   処理: [1: 表示寿命を確認して本文の現在ページと必要なページ送り案内を描きます]
    #   引数: [
    #     self: 折り返し済み本文を保持するUI
    #     screen: 描画先
    #     now: 通知の寿命判定に使うミリ秒
    #   ]
    #   戻り値: [result: なし。描画によってページや時刻を更新しません]
    # }
    def _draw_message(self, screen: pygame.Surface, now: int) -> None:
        if not self.lines or self.dismissed:
            return
        if not self.speaker and len(self.lines) <= 3 and now - self.shown_at > 6000:
            return
        rect = pygame.Rect(24, 556, 1072, 160)
        draw_frame(screen, rect)
        if self.speaker:
            draw_text_clipped(screen, self.speaker, pygame.Rect(48, 568, 992, 28), 16, ACCENT)
        draw_text(screen, "＊", (48, 600), 16)
        line_height = max(26, font(16).get_height() + 4)
        for index, line in enumerate(self.lines[self.page * 3:self.page * 3 + 3]):
            draw_text(screen, line, (80, 600 + index * line_height), 16)
        if (self.page + 1) * 3 < len(self.lines):
            draw_text(screen, "Enter / Space 次へ", (880, 684), 16, ACCENT)

    # {
    #   責務: [draw: メニューを開く導線と、会話またはパーティ付きメニューを描きます]
    #   処理: [
    #     1: メニューボタンと必要な会話枠を描きます
    #     2: メニューが開いている場合はパーティと項目、または操作説明を描きます
    #   ]
    #   引数: [
    #     self: メニューと会話の表示状態を所有するUI
    #     screen: 描画先
    #     party: 現在パーティの個体一覧。参照だけに使います
    #     selected_index: 行動指針とAIリセットの対象として選んだ個体番号
    #     now: 通知の寿命判定に使うミリ秒
    #   ]
    #   戻り値: [result: なし。個体やゲーム進行を変更しません]
    # }
    def draw(self, screen: pygame.Surface, party: Sequence[MonsterRecord], selected_index: int, now: int) -> None:
        draw_frame(screen, MENU_BUTTON, ACCENT if self.opened else TEXT, 2)
        draw_text(screen, "Esc  メニュー", (MENU_BUTTON.x + 20, MENU_BUTTON.y + 8), 16)
        if not self.opened:
            self._draw_message(screen, now)
            return
        # メニューは不透明な黒い一枚の枠に置き、背後の地形との混線を防ぎます。
        draw_frame(screen, MENU_PANEL)
        draw_text(screen, "操作の説明" if self.help_open else "メニュー", (128, 104), 32)
        if self.help_open:
            for index, line in enumerate(HELP_LINES):
                draw_text(screen, line, (128, 172 + index * 42), 16, TEXT)
            draw_text(screen, "Enter / Esc  メニューに戻る", (128, 664), 16, MUTED)
            return
        draw_text(screen, "なかま  /  1〜4で選択", (128, 158), 16, MUTED)
        for index, rect in enumerate(PARTY_RECTS):
            draw_frame(screen, rect, ACCENT if index == selected_index else MUTED, 2)
            record = party[index] if index < len(party) else None
            if record is None:
                draw_text(screen, f"{index + 1}. 空き", (rect.x + 20, rect.y + 24), 16, MUTED)
                continue
            draw_text_clipped(screen, f"{index + 1}. {record.name}  Lv{record.level}", rect.inflate(-32, -12), 16)
            tactic = str(record.ai.get("tactic", "balanced"))
            draw_text_clipped(screen, f"行動指針: {TACTIC_LABELS.get(tactic, tactic)}", pygame.Rect(rect.x + 16, rect.y + 44, rect.width - 32, 28), 16, MUTED)
        for index, (label, _, _) in enumerate(MENU_ITEMS):
            rect = MENU_RECTS[index]
            selected = index == self.selection
            draw_frame(screen, rect, ACCENT if selected else BG, 2)
            if selected:
                draw_cursor(screen, (rect.x + 16, rect.y + 16))
            draw_text(screen, label, (rect.x + 42, rect.y + 10), 16, ACCENT if selected else TEXT)
        draw_text(screen, "↑↓ 選択    Enter 決定    Esc 戻る", (128, 664), 16, MUTED)
