from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pygame

from kadoka_quest.apps.launcher_config import DEVELOPER_LAUNCH_TARGETS
from kadoka_quest.data.savedata import SaveDataManager
from kadoka_quest.developer.workflow import DeveloperWorkflowService, WorkflowResult
from kadoka_quest.paths import PROJECT_ROOT, ensure_runtime_directories, is_frozen
from kadoka_quest.ui.common import ACCENT, BG, GOOD, MUTED, PANEL, PANEL_ALT, TEXT, WARN, Button, draw_text, draw_wrapped, init_pygame, smoke_frames


def main() -> None:
    ensure_runtime_directories()
    saves = SaveDataManager()
    if not is_frozen():
        saves.import_legacy(PROJECT_ROOT / "saves" / "default")
    if not saves.list_names():
        saves.ensure_profile("default")

    workflow = DeveloperWorkflowService(PROJECT_ROOT)
    screen = init_pygame("kadoka quest - developer", (1080, 760))
    clock = pygame.time.Clock()
    running = True
    active_save = saves.active_name() or "default"
    status = f"Developer environment ready. Active save: {active_save}"
    status_ok = True

    def set_result(result: WorkflowResult) -> None:
        nonlocal status, status_ok
        status = result.message
        status_ok = result.ok

    def launch(script: str) -> None:
        environment = os.environ.copy()
        environment["KADOKA_DEVELOPER_TOOLS"] = "1"
        active = saves.active_name() or active_save
        if active in saves.list_names():
            environment["KADOKA_SAVE_DIR"] = str(saves.profile_root(active))
        if is_frozen():
            command = [sys.executable, "--dev-tool", Path(script).stem]
        else:
            command = [sys.executable, str(PROJECT_ROOT / script)]
        try:
            subprocess.Popen(command, cwd=PROJECT_ROOT, env=environment)
        except OSError as exc:
            set_result(WorkflowResult(False, f"Failed to launch {script}: {exc}"))
            return
        set_result(WorkflowResult(True, f"Started {script}."))

    def stop() -> None:
        nonlocal running
        running = False

    def launch_callback(script: str):
        return lambda: launch(script)

    editor_buttons: list[Button] = []
    for index, (label, script) in enumerate(DEVELOPER_LAUNCH_TARGETS):
        editor_buttons.append(
            Button(
                pygame.Rect(55, 155 + index * 72, 430, 52),
                label,
                launch_callback(script),
            )
        )

    workflow_buttons = [
        Button(pygame.Rect(575, 155, 430, 52), "1. Playerデータを検証", lambda: set_result(workflow.validate_project())),
        Button(pygame.Rect(575, 227, 430, 52), "2. Player Preview / Test Run", lambda: set_result(workflow.preview_player())),
        Button(pygame.Rect(575, 299, 430, 52), "3. Player配布ビルド", lambda: set_result(workflow.start_player_build())),
        Button(pygame.Rect(575, 371, 430, 52), "4. Player配布物スモーク", lambda: set_result(workflow.start_player_smoke())),
    ]
    buttons = editor_buttons + workflow_buttons + [Button(pygame.Rect(575, 455, 430, 52), "終了", stop)]

    smoke = smoke_frames()
    frames = 0

    while running:
        completed = workflow.poll()
        if completed is not None:
            set_result(completed)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            for button in buttons:
                button.handle(event)

        screen.fill(BG)
        draw_text(screen, "kadoka quest developer", (45, 26), 42, ACCENT, True)
        draw_text(screen, "Playerアプリ制作環境", (48, 78), 18, MUTED, True)

        pygame.draw.rect(screen, PANEL, pygame.Rect(35, 125, 470, 430), border_radius=12)
        draw_text(screen, "Content Editors", (55, 133), 20, ACCENT, True)
        pygame.draw.rect(screen, PANEL, pygame.Rect(555, 125, 470, 430), border_radius=12)
        draw_text(screen, "Player Workflow", (575, 133), 20, ACCENT, True)

        mouse = pygame.mouse.get_pos()
        for button in buttons:
            button.draw(screen, mouse)

        task = workflow.running_task
        if task is not None and task.process.poll() is None:
            draw_text(screen, f"実行中: {task.label}", (575, 525), 15, WARN, True)

        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(35, 580, 990, 135), border_radius=8)
        draw_text(screen, "Status", (55, 594), 17, ACCENT, True)
        draw_wrapped(screen, status, pygame.Rect(55, 622, 950, 48), 15, GOOD if status_ok else WARN)
        draw_wrapped(
            screen,
            "EditorsはPlayerが直接読むdata/assetsへ保存します。Validate → Preview → Build → Smokeの順で同じPlayer成果物を確認できます。",
            pygame.Rect(55, 680, 950, 28),
            13,
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
