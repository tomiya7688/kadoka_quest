# {
#   責務: [launcher: launcherの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import subprocess
import sys

import pygame

from kadoka_quest.apps.launcher_config import PLAYER_LAUNCH_TARGETS
from kadoka_quest.data.savedata import SaveDataManager
from kadoka_engine.data_validator import DataValidator
from kadoka_quest.paths import DATA_ROOT, PROJECT_ROOT, ensure_runtime_directories, is_frozen
from kadoka_quest.ui.common import ACCENT, BG, GOOD, MUTED, PANEL, PANEL_ALT, TEXT, Button, TextField, draw_text, draw_wrapped, init_pygame, smoke_frames


# {
#   責務: [_perform_save_action: launcherのperform・保存・actionを求める]
#   処理: [1: launcherのperform・保存・actionを求める]
#   引数: [
#     action: action（Callable[[], Path]）
#     fallback: fallback（str）
#   ]
#   戻り値: [result: launcherのperform・保存・actionを求めるための結果（tuple[Path | None, str | None]）]
# }
def _perform_save_action(action: Callable[[], Path], fallback: str) -> tuple[Path | None, str | None]:
    try:
        return action(), None
    except (ValueError, OSError) as exc:
        return None, str(exc) if str(exc) else fallback


# {
#   責務: [main: launcherのエントリ処理を実行する]
#   処理: [1: launcherのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def main() -> None:
    ensure_runtime_directories()
    saves = SaveDataManager()
    if not is_frozen():
        saves.import_legacy(PROJECT_ROOT / "saves" / "default")
    if not saves.list_names():
        saves.ensure_profile("default")
    names = saves.list_names()
    validation_issues = DataValidator(DATA_ROOT).validate()
    selected = names.index(saves.active_name()) if saves.active_name() in names else 0
    name_field = TextField(pygame.Rect(55, 185, 285, 42), "新しいセーブ")
    screen = init_pygame("kadoka quest", (1040, 720))
    clock = pygame.time.Clock()
    running = True
    status = (
        f"データ検証で{len(validation_issues)}件の問題を検出しました。確認後もゲームは起動できます。"
        if validation_issues else "データ検証済みです。使用するセーブデータを選んでください。"
    )

    # {
    #   責務: [refresh: launcherを更新内容を読み直す]
    #   処理: [1: launcherを更新内容を読み直す]
    #   引数: [select_name: select・名前（str | None）]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def refresh(select_name: str | None = None) -> None:
        nonlocal names, selected
        names = saves.list_names()
        if select_name in names:
            selected = names.index(str(select_name))
        selected = max(0, min(selected, max(0, len(names) - 1)))

    # {
    #   責務: [selected_name: launcherの選択中・名前を求める]
    #   処理: [1: launcherの選択中・名前を求める]
    #   引数: []
    #   戻り値: [result: launcherの選択中・名前を求めるための結果（str）]
    # }
    def selected_name() -> str:
        return names[selected] if names else "default"

    # {
    #   責務: [new_save: 保存を新規作成する]
    #   処理: [1: 保存を新規作成する]
    #   引数: []
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def new_save() -> None:
        nonlocal status
        path, error = _perform_save_action(
            lambda: saves.create(name_field.value),
            "セーブデータを新規作成できませんでした。",
        )
        if path is None:
            status = error or "セーブデータを新規作成できませんでした。"
            return
        refresh(path.name)
        status = f"{path.name} を新規作成して選択しました。"

    # {
    #   責務: [save_as: asを保存する]
    #   処理: [1: asを保存する]
    #   引数: []
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_as() -> None:
        nonlocal status
        path, error = _perform_save_action(
            lambda: saves.copy_profile(selected_name(), name_field.value),
            "別名保存できませんでした。",
        )
        if path is None:
            status = error or "別名保存できませんでした。"
            return
        refresh(path.name)
        status = f"現在の状態を {path.name} として保存しました。"

    # {
    #   責務: [load_selected: 選択中を読み込む]
    #   処理: [1: 選択中を読み込む]
    #   引数: []
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def load_selected() -> None:
        nonlocal status
        path, error = _perform_save_action(
            lambda: saves.set_active(selected_name()),
            "セーブデータを読み込めませんでした。",
        )
        if path is None:
            status = error or "セーブデータを読み込めませんでした。"
            return
        status = f"{selected_name()} を読み込むセーブデータに設定しました。"

    # {
    #   責務: [launch: launcherを起動する]
    #   処理: [1: launcherを起動する]
    #   引数: [script: script（str）]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def launch(script: str) -> None:
        nonlocal status
        load_selected()
        environment = os.environ.copy()
        environment["KADOKA_SAVE_DIR"] = str(saves.profile_root(selected_name()))
        command = [sys.executable, "--play"] if is_frozen() else [sys.executable, str(PROJECT_ROOT / script)]
        subprocess.Popen(command, cwd=PROJECT_ROOT, env=environment)
        status = f"{selected_name()} でゲームを起動しました。"

    # {
    #   責務: [stop: launcherを停止する]
    #   処理: [1: launcherを停止する]
    #   引数: []
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def stop() -> None:
        nonlocal running
        running = False

    # {
    #   責務: [launch_callback: コールバックを起動する]
    #   処理: [1: コールバックを起動する]
    #   引数: [script: script（str）]
    #   戻り値: [result: コールバックを起動するための結果（型注釈なし）]
    # }
    def launch_callback(script: str):
        return lambda: launch(script)

    buttons = [
        Button(pygame.Rect(55, 245, 135, 44), "新規作成", new_save),
        Button(pygame.Rect(205, 245, 135, 44), "別名保存", save_as),
        Button(pygame.Rect(55, 300, 285, 44), "選択データを読み込む", load_selected),
    ]
    for label, script in PLAYER_LAUNCH_TARGETS:
        buttons.append(Button(pygame.Rect(410, 145, 555, 58), label, launch_callback(script)))
    buttons.append(Button(pygame.Rect(410, 225, 555, 58), "終了", stop))

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

        pygame.draw.rect(screen, PANEL, pygame.Rect(385, 115, 605, 220), border_radius=12)
        draw_text(screen, f"選択中: {selected_name()}", (410, 305), 20, GOOD, True)
        mouse = pygame.mouse.get_pos()
        for button in buttons:
            button.draw(screen, mouse)

        pygame.draw.rect(screen, PANEL, pygame.Rect(385, 365, 605, 95), border_radius=10)
        draw_wrapped(
            screen,
            "ここはプレイヤー向けランチャーです。個体・パーティ管理はゲーム内の牧場から行います。",
            pygame.Rect(410, 382, 555, 60),
            16,
            MUTED,
        )
        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(385, 485, 605, 80), border_radius=8)
        draw_wrapped(screen, status, pygame.Rect(405, 500, 565, 50), 16)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
