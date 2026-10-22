# {
#   責務: [battle_renderer: 戦闘Sessionを敵の舞台・味方の状態・会話枠・コマンド列へ描き、戦闘状態を変更しません]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any

import pygame

from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.ui.character_image_provider import CharacterImageProvider
from kadoka_quest.ui.game_ui import (
    ACCENT, BG, MUTED, TEXT, Button, draw_cursor, draw_frame,
    draw_text, draw_text_clipped, draw_wrapped, font,
)

ENEMY_STAGE = pygame.Rect(24, 72, 1072, 280)
ALLY_STRIP = pygame.Rect(24, 364, 1072, 104)
MESSAGE_RECT = pygame.Rect(24, 488, 1072, 132)
COMMAND_RECTS = tuple(pygame.Rect(24 + index * 272, 644, 256, 56) for index in range(4))
OUTCOME_LABELS = {
    "victory": "勝利した！",
    "defeat": "パーティは戦闘不能になった。",
    "escaped": "戦闘から離れた。",
    "fled": "戦闘から離れた。",
    "enemies_fled": "相手は全員逃げ去った。",
    "scouted": "スカウトに成功した！",
}
STATUS_LABELS = {"bleeding": "出血", "poison": "毒", "sleep": "眠り", "paralysis": "まひ"}


# {
#   責務: [BattleRenderer: 戦闘個体とログを読み取り、操作対象が分かるゲーム用戦闘画面へ描きます]
#   フィールド: [images: 読み込み済みキャラクター画像を提供するProvider]
# }
class BattleRenderer:
    # {
    #   責務: [__init__: 戦闘画面で使用する画像Providerを保持します]
    #   処理: [1: 画像取得の依存先を保持します]
    #   引数: [
    #     self: 戦闘画面の描画担当
    #     images: キャラクター画像を返すProvider
    #   ]
    #   戻り値: [result: なし]
    # }
    def __init__(self, images: CharacterImageProvider) -> None:
        self.images = images

    # {
    #   責務: [_draw_portrait: 個体の画像または代替記号を指定枠内へ描きます]
    #   処理: [1: 個体画像を取得し、画像がない場合は白い輪郭と種族の記号を描きます]
    #   引数: [
    #     self: 画像Providerを持つ描画担当
    #     screen: 描画先
    #     member: 種族情報を持つ戦闘個体
    #     rect: 画像の表示枠
    #   ]
    #   戻り値: [result: なし。個体や元画像を変更しません]
    # }
    def _draw_portrait(self, screen: pygame.Surface, member: Any, rect: pygame.Rect) -> None:
        # 色付きの既存キャラクター画像は、その作品の見た目を保って表示します。
        portrait = self.images.get(member.record.species_id, "portrait", rect.size)
        if portrait:
            screen.blit(portrait, portrait.get_rect(center=rect.center))
            return
        appearance = self.images.appearance(member.record.species_id)
        fallback = rect.inflate(-rect.width // 3, -rect.height // 3)
        draw_frame(screen, fallback)
        symbol = font(32 if rect.width >= 100 else 16).render(str(appearance.get("symbol", "?")), False, TEXT)
        screen.blit(symbol, symbol.get_rect(center=rect.center))

    # {
    #   責務: [_status_text: 戦闘個体の逃走・戦闘不能・状態異常を表示文字列へ変換します]
    #   処理: [1: 逃走とHPを確認し、生存個体の状態異常名を表示順に連結します]
    #   引数: [member: 現在のHPと状態異常を読む戦闘個体]
    #   戻り値: [result: 個体の状態表示。状態異常がなければ空文字]
    # }
    @staticmethod
    def _status_text(member: Any) -> str:
        if getattr(member, "fled", False):
            return "逃走済み"
        if member.hp <= 0:
            return "戦闘不能"
        # 未知のMOD状態はIDを残し、表示のためにゲーム側の状態を正規化しません。
        names = []
        for effect in getattr(member, "status_effects", []):
            identifier = str(effect.get("id", "")) if isinstance(effect, dict) else str(effect)
            display_name = effect.get("display_name") if isinstance(effect, dict) else None
            names.append(str(display_name or STATUS_LABELS.get(identifier, identifier)))
        return " / ".join(names)

    # {
    #   責務: [_draw_enemy: 上段の舞台に敵画像・名前・HPと現在の状態を描きます]
    #   処理: [1: 行動中の印を描き、敵の画像と状態を同じ列へ配置します]
    #   引数: [
    #     self: 画像Providerを持つ描画担当
    #     screen: 描画先
    #     session: 行動中の個体IDを読む戦闘Session
    #     member: 描画対象の敵
    #     rect: 敵一体に割り当てた舞台の列
    #   ]
    #   戻り値: [result: なし。戦闘状態を変更しません]
    # }
    def _draw_enemy(self, screen: pygame.Surface, session: BattleSession, member: Any, rect: pygame.Rect) -> None:
        focused = session.focus_id == member.record.monster_id
        if focused:
            draw_cursor(screen, (rect.centerx - 6, rect.y + 4))
        # 敵の画像にはカード背景を付けず、黒い余白の中央へ大きく置きます。
        portrait_rect = pygame.Rect(0, 0, 160, 160)
        portrait_rect.midtop = (rect.centerx, rect.y + 24)
        if not getattr(member, "fled", False):
            self._draw_portrait(screen, member, portrait_rect)
        color = ACCENT if focused else TEXT
        draw_text_clipped(screen, f"{member.name}  Lv{member.record.level}", pygame.Rect(rect.x + 12, rect.y + 192, rect.width - 24, 24), 16, color)
        draw_text_clipped(screen, f"HP {member.hp}/{member.stats['hp']}", pygame.Rect(rect.x + 12, rect.y + 220, rect.width - 24, 24), 16, MUTED)
        draw_text_clipped(screen, self._status_text(member), pygame.Rect(rect.x + 12, rect.y + 246, rect.width - 24, 24), 16, MUTED)

    # {
    #   責務: [_draw_ally: 味方一体の名前・HP・MP・状態を下段のコンパクトな帯へ描きます]
    #   処理: [1: 名前と資源を描き、行動中の印と状態異常を追記します]
    #   引数: [
    #     self: 戦闘画面の描画担当
    #     screen: 描画先
    #     session: 行動中の個体IDを読む戦闘Session
    #     member: 描画対象の味方
    #     rect: 味方一体の表示枠
    #   ]
    #   戻り値: [result: なし。HP・MP・状態異常を変更しません]
    # }
    def _draw_ally(self, screen: pygame.Surface, session: BattleSession, member: Any, rect: pygame.Rect) -> None:
        focused = session.focus_id == member.record.monster_id
        color = ACCENT if focused else TEXT
        if focused:
            draw_cursor(screen, (rect.x + 8, rect.y + 12))
        text_rect = pygame.Rect(rect.x + 28, rect.y + 8, rect.width - 40, 24)
        draw_text_clipped(screen, f"{member.name}  Lv{member.record.level}", text_rect, 16, color)
        draw_text(screen, f"HP {member.hp}/{member.stats['hp']}", (rect.x + 16, rect.y + 38), 16, TEXT)
        draw_text(screen, f"MP {member.mp}/{member.stats['mp']}", (rect.x + 16, rect.y + 62), 16, MUTED)
        state_rect = pygame.Rect(rect.x + 136, rect.y + 62, rect.width - 148, 24)
        draw_text_clipped(screen, self._status_text(member), state_rect, 16, MUTED)

    # {
    #   責務: [draw: 敵の舞台・味方の状態帯・最新ログ・操作コマンドを戦闘画面へ描きます]
    #   処理: [
    #     1: 戦闘の種類と進行状態を表示して敵と味方を配置します
    #     2: 現在の行動と公開済みログの末尾二件を会話枠へ表示します
    #     3: 演出と勝敗に応じてコマンドの有効状態と選択表示を更新します
    #   ]
    #   引数: [
    #     self: 戦闘画面の描画担当
    #     screen: 描画先
    #     session: 描画専用で読む戦闘Session
    #     buttons: 入力側と同じ矩形を持つ四つのコマンドボタン
    #     status: コマンド実行時の補足通知。省略時は通知を描きません
    #   ]
    #   戻り値: [result: なし。ボタンの表示状態だけを更新し、Sessionは変更しません]
    # }
    def draw(self, screen: pygame.Surface, session: BattleSession, buttons: list[Button], status: str = "") -> None:
        battle = session.battle
        if not battle:
            return
        draw_text(screen, "模擬戦（AI更新なし）" if session.simulation else "コマンドバトル", (24, 24), 16, TEXT)
        # 結果が確定済みでも再生中は演出表示を保ち、再生後は操作終了を明示します。
        if session.playback:
            mode_label = "行動演出中"
        elif battle.outcome:
            mode_label = "戦闘終了"
        else:
            mode_label = "オート戦闘中" if session.auto else "コマンドを選択"
        draw_text(screen, f"{battle.round_number}ターン  /  {mode_label}", (720, 24), 16, MUTED)
        # 四体までの通常編成を横一列へ描き、敵の画像を画面上部の主役にします。
        enemy_width = ENEMY_STAGE.width // max(1, len(battle.enemies))
        for index, member in enumerate(battle.enemies):
            self._draw_enemy(screen, session, member, pygame.Rect(ENEMY_STAGE.x + index * enemy_width, ENEMY_STAGE.y, enemy_width, ENEMY_STAGE.height))
        draw_frame(screen, ALLY_STRIP)
        ally_width = ALLY_STRIP.width // max(1, len(battle.allies))
        for index, member in enumerate(battle.allies):
            rect = pygame.Rect(ALLY_STRIP.x + index * ally_width, ALLY_STRIP.y, ally_width, ALLY_STRIP.height)
            if index:
                pygame.draw.line(screen, MUTED, rect.topleft, rect.bottomleft, 1)
            self._draw_ally(screen, session, member, rect)

        # 公開済みのログだけを読み、まだ再生していない行動は表示しません。
        draw_frame(screen, MESSAGE_RECT)
        current_action = session.action_line or "コマンドを選んでください。"
        if battle.outcome and not session.playback:
            current_action = f"{OUTCOME_LABELS.get(battle.outcome, battle.outcome)}  Enterでフィールドへ"
        draw_text(screen, "＊", (44, 504), 16, TEXT)
        draw_wrapped(screen, current_action, pygame.Rect(76, 504, 996, 52), 16, TEXT)
        visible_logs = battle.log[:session.visible_log_count]
        for index, line in enumerate(visible_logs[-2:]):
            draw_wrapped(screen, line, pygame.Rect(76, 558 + index * 28, 996, 24), 16, MUTED)

        mouse = pygame.mouse.get_pos()
        for index, button in enumerate(buttons):
            button.enabled = battle.outcome is None and not session.playback
            button.focused = button.enabled and index == session.selection
            button.draw(screen, mouse)
        footer = status or "←→ 選択    Enter 決定    1〜4 直接実行    A オート切替"
        draw_text_clipped(screen, footer, pygame.Rect(24, 712, 1072, 24), 16, MUTED)
