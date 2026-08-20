from __future__ import annotations

import os
import subprocess
import sys

import pygame

from kadoka_quest.data.savedata import SaveDataManager
from kadoka_quest.paths import PROJECT_ROOT, ensure_runtime_directories
from kadoka_quest.ui.common import ACCENT, BG, GOOD, MUTED, PANEL, PANEL_ALT, TEXT, Button, TextField, draw_text, draw_wrapped, init_pygame, smoke_frames


def main() -> None:
    ensure_runtime_directories()
    saves = SaveDataManager()
    saves.import_legacy(PROJECT_ROOT / "saves" / "default")
    if not saves.list_names():
        saves.create("default")
    names = saves.list_names()
    selected = names.index(saves.active_name()) if saves.active_name() in names else 0
    name_field = TextField(pygame.Rect(55, 185, 285, 42), "新しいセーブ")
    screen = init_pygame("kadoka quest - launcher", (1040, 720))
    clock = pygame.time.Clock()
    running = True
    status = "使用するセーブデータを選んでゲームを開始してください。"

    def refresh(select_name: str | None = None) -> None:
        nonlocal names, selected
        names = saves.list_names()
        if select_name in names:
            selected = names.index(str(select_name))
        selected = max(0, min(selected, max(0, len(names) - 1)))

    def selected_name() -> str:
        return names[selected] if names else "default"

    def new_save() -> None:
        nonlocal status
        try:
            path = saves.create(name_field.value)
            refresh(path.name)
            status = f"{path.name} を新規作成して選択しました。"
        except (ValueError, FileExistsError) as exc:
            status = str(exc) if str(exc) else "同じ名前のセーブデータがあります。"

    def save_as() -> None:
        nonlocal status
        try:
            path = saves.copy_profile(selected_name(), name_field.value)
            refresh(path.name)
            status = f"現在の状態を {path.name} として保存しました。"
        except (ValueError, FileExistsError, FileNotFoundError) as exc:
            status = str(exc) if str(exc) else "別名保存できませんでした。"

    def load_selected() -> None:
        nonlocal status
        try:
            saves.set_active(selected_name())
            status = f"{selected_name()} を読み込むセーブデータに設定しました。"
        except (ValueError, FileNotFoundError) as exc:
            status = str(exc)

    def launch(script: str) -> None:
        nonlocal status
        load_selected()
        environment = os.environ.copy()
        environment["KADOKA_SAVE_DIR"] = str(saves.profile_root(selected_name()))
        subprocess.Popen([sys.executable, str(PROJECT_ROOT / script)], cwd=PROJECT_ROOT, env=environment)
        status = f"{selected_name()} で {script} を起動しました。"

    def stop() -> None:
        nonlocal running
        running = False

    buttons = [
        Button(pygame.Rect(55, 245, 135, 44), "新規作成", new_save),
        Button(pygame.Rect(205, 245, 135, 44), "別名保存", save_as),
        Button(pygame.Rect(55, 300, 285, 44), "選択データを読み込む", load_selected),
        Button(pygame.Rect(410, 145, 260, 58), "ゲームを開始", lambda: launch("game.py")),
        Button(pygame.Rect(705, 145, 260, 58), "個体・パーティ管理", lambda: launch("manage.py")),
        Button(pygame.Rect(410, 235, 260, 58), "ブロックエディタ", lambda: launch("block_editor.py")),
        Button(pygame.Rect(705, 235, 260, 58), "マップエディタ", lambda: launch("map_editor.py")),
        Button(pygame.Rect(410, 325, 260, 58), "モンスターエディタ", lambda: launch("monster_editor.py")),
        Button(pygame.Rect(705, 325, 260, 58), "終了", stop),
    ]
    smoke = smoke_frames()
    frames = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            handled = name_field.handle(event)
            for button in buttons:
                handled = button.handle(event) or handled
            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, _ in enumerate(names[:7]):
                    if pygame.Rect(55, 390 + index * 40, 285, 34).collidepoint(event.pos):
                        selected = index

        screen.fill(BG)
        draw_text(screen, "kadoka quest", (45, 25), 48, ACCENT, True)
        draw_text(screen, "セーブデータ", (55, 115), 24, ACCENT, True)
        name_field.draw(screen, "セーブデータ名")
        pygame.draw.rect(screen, PANEL, pygame.Rect(40, 365, 315, 315), border_radius=10)
        active = saves.active_name()
        for index, name in enumerate(names[:7]):
            rect = pygame.Rect(55, 390 + index * 40, 285, 34)
            pygame.draw.rect(screen, (55, 94, 122) if index == selected else PANEL_ALT, rect, border_radius=5)
            draw_text(screen, ("● " if name == active else "  ") + name, (66, rect.y + 8), 15, GOOD if name == active else TEXT, name == active)
        draw_text(screen, "● は現在読み込むデータ", (58, 650), 14, MUTED)

        pygame.draw.rect(screen, PANEL, pygame.Rect(385, 115, 605, 300), border_radius=12)
        draw_text(screen, f"選択中: {selected_name()}", (410, 425), 20, GOOD, True)
        mouse = pygame.mouse.get_pos()
        for button in buttons:
            button.draw(screen, mouse)
        pygame.draw.rect(screen, PANEL, pygame.Rect(385, 465, 605, 130), border_radius=10)
        draw_wrapped(screen, "各セーブは savedata/セーブ名/ の中に state.json、monsters、items、parties を持ちます。JSONは直接編集できます。", pygame.Rect(410, 485, 555, 90), 17, MUTED)
        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(385, 620, 605, 60), border_radius=8)
        draw_wrapped(screen, status, pygame.Rect(405, 632, 565, 40), 16)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()

