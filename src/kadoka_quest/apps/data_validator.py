# {
#   責務: [data_validator: データ・検証処理の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import pygame

from kadoka_engine.data_validator import DataValidator
from kadoka_quest.paths import DATA_ROOT
from kadoka_quest.ui.common import ACCENT, BG, GOOD, MUTED, PANEL, PANEL_ALT, TEXT, WARN, Button, ScrollBar, draw_text, draw_wrapped, init_pygame, smoke_frames


ROWS = 8


# {
#   責務: [main: データ・検証処理のエントリ処理を実行する]
#   処理: [1: データ・検証処理のエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def main() -> None:
    screen = init_pygame("kadoka quest - data validation", (1100, 720))
    clock = pygame.time.Clock()
    validator = DataValidator(DATA_ROOT)
    issues = validator.validate()
    scroll = ScrollBar(pygame.Rect(1055, 145, 12, 450), total=len(issues), page=ROWS)
    running = True

    # {
    #   責務: [refresh: データ・検証処理を更新内容を読み直す]
    #   処理: [1: データ・検証処理を更新内容を読み直す]
    #   引数: []
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def refresh() -> None:
        nonlocal issues
        issues = validator.validate()
        scroll.configure(len(issues), ROWS)
        scroll.value = min(scroll.value, scroll.maximum)

    # {
    #   責務: [stop: データ・検証処理を停止する]
    #   処理: [1: データ・検証処理を停止する]
    #   引数: []
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def stop() -> None:
        nonlocal running
        running = False

    buttons = [
        Button(pygame.Rect(760, 35, 140, 45), "再検査", refresh),
        Button(pygame.Rect(920, 35, 140, 45), "閉じる", stop),
    ]
    smoke = smoke_frames()
    frames = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                refresh()
            if event.type == pygame.MOUSEWHEEL:
                scroll.value = max(0, min(scroll.maximum, scroll.value - event.y))
            scroll.handle(event)
            for button in buttons:
                button.handle(event)

        screen.fill(BG)
        draw_text(screen, "MODデータ検証", (32, 25), 38, ACCENT, True)
        summary = "問題は見つかりませんでした。" if not issues else f"{len(issues)}件の問題があります。起動は停止しません。"
        draw_text(screen, summary, (35, 95), 21, GOOD if not issues else WARN, True)
        pygame.draw.rect(screen, PANEL, pygame.Rect(25, 130, 1050, 485), border_radius=10)
        if not issues:
            draw_wrapped(screen, "ブロック、マップ、種族、Lv別能力、スキル、＋分岐、装備、耐性の参照は正常です。", pygame.Rect(55, 175, 970, 80), 20, GOOD)
        for row, issue in enumerate(issues[scroll.value:scroll.value + ROWS]):
            rect = pygame.Rect(40, 145 + row * 56, 995, 48)
            pygame.draw.rect(screen, PANEL_ALT, rect, border_radius=6)
            draw_text(screen, f"[{issue['code']}] {issue['path']}", (rect.x + 12, rect.y + 5), 15, WARN, True)
            draw_wrapped(screen, issue["message"], pygame.Rect(rect.x + 12, rect.y + 25, rect.width - 24, 20), 14, TEXT)
        scroll.draw(screen, pygame.mouse.get_pos())
        draw_text(screen, "F5: 再検査 / Esc: 閉じる", (35, 650), 17, MUTED)
        for button in buttons:
            button.draw(screen, pygame.mouse.get_pos())
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()
