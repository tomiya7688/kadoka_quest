# {
#   責務: [battle_renderer: 戦闘・描画処理の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any

import pygame

from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.ui.character_image_provider import CharacterImageProvider
from kadoka_quest.ui.common import (
    ACCENT,
    BAD,
    BG,
    GOOD,
    MUTED,
    PANEL,
    PANEL_ALT,
    SELECTED,
    TEXT,
    WARN,
    Button,
    draw_text,
    draw_wrapped,
)


# {
#   責務: [BattleRenderer: Draws battle state without executing commands or calculations.]
#   フィールド: [images: 画像一覧]
# }
class BattleRenderer:
    """Draws battle state without executing commands or calculations."""

    # {
    #   責務: [__init__: 戦闘・描画処理が利用する初期状態と依存を設定する]
    #   処理: [1: 戦闘・描画処理が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     images: 画像一覧（CharacterImageProvider）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, images: CharacterImageProvider) -> None:
        self.images = images

    # {
    #   責務: [_hex_color: 戦闘・描画処理のhex・色を求める]
    #   処理: [1: 戦闘・描画処理のhex・色を求める]
    #   引数: [value: 値（str）]
    #   戻り値: [result: 戦闘・描画処理のhex・色を求めるための結果（tuple[int, int, int]）]
    # }
    @staticmethod
    def _hex_color(value: str) -> tuple[int, int, int]:
        try:
            clean = value.lstrip("#")
            return tuple(int(clean[index:index + 2], 16) for index in (0, 2, 4))
        except (TypeError, ValueError):
            return 130, 130, 130

    # {
    #   責務: [_draw_combatant: 戦闘個体を描画する]
    #   処理: [1: 戦闘個体を描画する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     screen: 描画先（pygame.Surface）
    #     session: セッション（BattleSession）
    #     member: 個体（Any）
    #     rect: 表示矩形（pygame.Rect）
    #     ally: 味方（bool）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _draw_combatant(
        self,
        screen: pygame.Surface,
        session: BattleSession,
        member: Any,
        rect: pygame.Rect,
        ally: bool,
    ) -> None:
        pygame.draw.rect(screen, PANEL_ALT, rect, border_radius=10)
        focused = session.focus_id == member.record.monster_id
        if focused:
            pygame.draw.rect(screen, WARN if not ally else GOOD, rect, 4, border_radius=10)
        if getattr(member, "fled", False):
            draw_text(screen, f"{member.name}：逃走済み", (rect.x + 12, rect.y + 40), 18, MUTED)
            return
        appearance = self.images.appearance(member.record.species_id)
        color = self._hex_color(appearance.get("value", "#888888"))
        center = (rect.x + 47 if ally else rect.right - 47, rect.y + 55)
        portrait = self.images.get(member.record.species_id, "portrait", (82, 82))
        if portrait:
            screen.blit(portrait, portrait.get_rect(center=center))
        else:
            pygame.draw.circle(screen, color, center, 35)
            symbol = appearance.get("symbol", "?")
            symbol_image = pygame.font.SysFont(["Meiryo", "Arial"], 24, bold=True).render(str(symbol), True, BG)
            screen.blit(symbol_image, symbol_image.get_rect(center=center))
        text_x = rect.x + 95 if ally else rect.x + 12
        draw_text(screen, f"{member.name} Lv{member.record.level}", (text_x, rect.y + 13), 18, TEXT, True)
        hp_color = GOOD if member.hp / member.stats["hp"] > 0.35 else BAD
        draw_text(screen, f"HP {member.hp}/{member.stats['hp']}", (text_x, rect.y + 46), 15, hp_color)
        draw_text(screen, f"MP {member.mp}/{member.stats['mp']}", (text_x, rect.y + 69), 15, ACCENT)
        if focused:
            draw_text(screen, "行動中", (rect.right - 65, rect.y + 75), 13, WARN if not ally else GOOD, True)

    # {
    #   責務: [draw: 戦闘・描画処理を描画する]
    #   処理: [1: 戦闘・描画処理を描画する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     screen: 描画先（pygame.Surface）
    #     session: セッション（BattleSession）
    #     buttons: buttons（list[Button]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def draw(self, screen: pygame.Surface, session: BattleSession, buttons: list[Button]) -> None:
        battle = session.battle
        if not battle:
            return
        draw_text(screen, "模擬戦（AI更新なし）" if session.simulation else "コマンドバトル", (25, 20), 32, ACCENT, True)
        draw_text(screen, "←→で選択 / Enterで決定 / 1〜4で直接実行 / Aでオート", (360, 27), 16, MUTED)
        mode_label = "行動演出中" if session.playback else ("オート戦闘中" if session.auto else "手動戦闘")
        draw_text(screen, mode_label, (360, 50), 15, WARN if session.playback else (GOOD if session.auto else ACCENT), True)
        draw_text(screen, "味方", (25, 70), 20, GOOD, True)
        draw_text(screen, "相手", (790, 70), 20, WARN, True)
        for index, member in enumerate(battle.allies):
            self._draw_combatant(screen, session, member, pygame.Rect(25, 100 + index * 115, 310, 100), True)
        for index, member in enumerate(battle.enemies):
            self._draw_combatant(screen, session, member, pygame.Rect(785, 100 + index * 115, 310, 100), False)
        pygame.draw.rect(screen, PANEL, pygame.Rect(355, 90, 410, 490), border_radius=10)
        draw_text(screen, f"戦闘ログ / {battle.round_number}ターン", (372, 108), 18, MUTED, True)
        pygame.draw.rect(screen, SELECTED, pygame.Rect(370, 138, 380, 68), border_radius=8)
        draw_text(screen, "いまの行動", (383, 145), 14, WARN if session.playback else MUTED, True)
        current_action = session.action_line or "コマンドを選んでください。"
        draw_wrapped(screen, current_action, pygame.Rect(383, 168, 354, 34), 16, TEXT)
        draw_text(screen, "履歴", (372, 218), 14, MUTED, True)
        visible_logs = battle.log[:session.visible_log_count]
        for index, line in enumerate(visible_logs[-13:]):
            draw_wrapped(screen, line, pygame.Rect(372, 240 + index * 25, 375, 24), 14, TEXT)
        if battle.outcome and not session.playback:
            pygame.draw.rect(screen, (55, 94, 122), pygame.Rect(355, 590, 410, 42), border_radius=8)
            draw_text(screen, f"結果: {battle.outcome}　Enterでフィールドへ", (375, 600), 17, GOOD, True)
        mouse = pygame.mouse.get_pos()
        for index, button in enumerate(buttons):
            button.enabled = battle.outcome is None and not session.playback
            button.draw(screen, mouse)
            if index == session.selection and not battle.outcome and not session.playback:
                pygame.draw.rect(screen, ACCENT, button.rect.inflate(6, 6), 3, border_radius=9)
