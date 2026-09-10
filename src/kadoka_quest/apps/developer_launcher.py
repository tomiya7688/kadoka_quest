from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pygame

from kadoka_quest.apps.launcher_config import DEVELOPER_LAUNCH_TARGETS
from kadoka_quest.data.savedata import SaveDataManager
from kadoka_quest.paths import PROJECT_ROOT, ensure_runtime_directories, is_frozen
from kadoka_quest.ui.common import ACCENT, BG, GOOD, MUTED, PANEL, PANEL_ALT, TEXT, Button, draw_text, draw_wrapped, init_pygame, smoke_frames


def main() -> None:
    ensure_runtime_directories()
    saves = SaveDataManager()
    if not is_frozen():
        saves.import_legacy(PROJECT_ROOT / "saves" / "default")
    if not saves.list_names():
        saves.create("default")

    screen = init_pygame("kadoka quest - developer tools", (900, 640))
    clock = pygame.time.Clock()
    running = True
    active_save = saves.active_name() or "default"
    status = f"開発者ツール。現在のセーブ: {active_save}"

    def launch(script: str) -> None:
        nonlocal status
        environment = os.environ.copy()
        active = saves.active_name() or active_save
        if active in saves.list_names():
            environment["KADOKA_SAVE_DIR"] = str(saves.profile_root(active))
        if is_frozen():
            command = [sys.executable, "--dev-tool", Path(script).stem]
        else:
            command = [sys.executable, str(PROJECT_ROOT / script)]
        subprocess.Popen(command, cwd=PROJECT_ROOT, env=environment)
        status = f"{script} を起動しました。"

    def stop() -> None:
        nonlocal running
        running = False

    def launch_callback(script: str):
        return lambda: launch(script)

    buttons: list[Button] = []
    for index, (label, script) in enumerate(DEVELOPER_LAUNCH_TARGETS):
        column = index % 2
        row = index // 2
        buttons.append(
            Button(
                pygame.Rect(55 + column * 405, 155 + row * 82, 365, 58),
                label,
                launch_callback(script),
            )
        )
    buttons.append(Button(pygame.Rect(55, 425, 770, 58), "終了", stop))

    smoke = smoke_frames()
    frames = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            for button in buttons:
                button.handle(event)

        screen.fill(BG)
        draw_text(screen, "kadoka quest developer", (45, 28), 42, ACCENT, True)
        draw_text(screen, "開発者ツール", (55, 105), 24, ACCENT, True)
        pygame.draw.rect(screen, PANEL, pygame.Rect(35, 135, 830, 375), border_radius=12)
        mouse = pygame.mouse.get_pos()
        for button in buttons:
            button.draw(screen, mouse)

        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(35, 530, 830, 75), border_radius=8)
        draw_wrapped(screen, status, pygame.Rect(55, 543, 790, 26), 16, TEXT)
        draw_wrapped(
            screen,
            "通常プレイヤー向けの run_game.bat / launcher.py には、ここにある開発機能を表示しません。",
            pygame.Rect(55, 570, 790, 28),
            14,
            MUTED,
        )
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
