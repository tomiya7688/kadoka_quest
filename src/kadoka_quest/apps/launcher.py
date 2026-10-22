# {
#   責務: [launcher: ゲーム専用タイトルの要求を、セーブ管理とゲーム起動へ接続します]
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
from kadoka_quest.ui.game_ui import Button, init_pygame, smoke_frames
from kadoka_quest.ui.title_screen import TitleScreen


# {
#   責務: [_perform_save_action: セーブ操作の成功パスまたは利用者向けエラーを返します]
#   処理: [1: 保存機能を呼び、名前不正とファイル操作失敗を画面へ返せる結果に変換します]
#   引数: [
#     action: 保存先Pathを返す既存セーブ操作
#     fallback: 例外に説明がない場合に表示する日本語の案内
#   ]
#   戻り値: [result: 成功時はPathとNone、失敗時はNoneと説明（tuple[Path | None, str | None]）]
# }
def _perform_save_action(action: Callable[[], Path], fallback: str) -> tuple[Path | None, str | None]:
    try:
        return action(), None
    except (ValueError, OSError) as exc:
        return None, str(exc) if str(exc) else fallback


# {
#   責務: [main: タイトル画面から名前付きセーブの作成・選択・複製とゲーム起動を提供します]
#   処理: [
#     1: 保存先とデータ検証結果を用意し、ゲーム専用タイトルを作ります
#     2: タイトルの要求を既存SaveDataManagerとゲーム起動へ渡します
#     3: タイトルを描画し、終了時にpygameを閉じます
#   ]
#   引数: []
#   戻り値: [result: なし（None）]
# }
def main() -> None:
    ensure_runtime_directories()
    saves = SaveDataManager()
    if not is_frozen():
        saves.import_legacy(PROJECT_ROOT / "saves" / "default")
    if not saves.list_names():
        saves.ensure_profile("default")
    validation_issues = DataValidator(DATA_ROOT).validate()
    screen = init_pygame("kadoka quest", TitleScreen.SIZE)
    view = TitleScreen(button_factory=Button)
    view.set_profiles(saves.list_names(), saves.active_name(), saves.active_name())
    view.status = (
        f"ゲームデータに{len(validation_issues)}件の問題があります。内容を確認してください。"
        if validation_issues else ""
    )
    clock = pygame.time.Clock()
    running = True

    # {
    #   責務: [refresh_saved_profile: セーブ操作の結果をタイトルへ反映します]
    #   処理: [
    #     1: 失敗時は入力画面と入力した名前を残します
    #     2: 成功時は保存済みの一覧を読み直し、新しい選択を表示します
    #   ]
    #   引数: [
    #     path: 成功したセーブ操作の対象フォルダ。失敗時はNone
    #     error: 失敗理由。成功時はNone
    #     message: 成功した操作を説明する文
    #   ]
    #   戻り値: [success: 保存操作が成功した場合はtrue（bool）]
    # }
    def refresh_saved_profile(path: Path | None, error: str | None, message: str) -> bool:
        if path is None:
            view.status = error or "セーブデータを更新できませんでした。"
            return False
        view.set_profiles(saves.list_names(), saves.active_name(), path.name)
        view.status = message
        view.show_home()
        return True

    # {
    #   責務: [new_save: タイトルに入力した名前で新規セーブを作ります]
    #   処理: [1: 新規作成を保存機能へ依頼し、成功または失敗を表示します]
    #   引数: []
    #   戻り値: [result: なし（None）]
    # }
    def new_save() -> None:
        name = view.name_field.value
        path, error = _perform_save_action(lambda: saves.create(name), "セーブデータを新規作成できませんでした。")
        refresh_saved_profile(path, error, f"{name} を新規作成しました。ゲームを開始できます。")

    # {
    #   責務: [save_as: 選択した冒険の記録を入力名へ複製します]
    #   処理: [1: 元データを保持する複製を保存機能へ依頼し、結果を表示します]
    #   引数: []
    #   戻り値: [result: なし（None）]
    # }
    def save_as() -> None:
        name = view.name_field.value
        path, error = _perform_save_action(
            lambda: saves.copy_profile(view.selected_name(), name), "別名保存できませんでした。",
        )
        refresh_saved_profile(path, error, f"{name} に別名保存しました。元の記録も残っています。")

    # {
    #   責務: [load_selected: 一覧で選択した記録を次回起動用のセーブへ設定します]
    #   処理: [1: 選択の保存結果を表示し、成功時だけタイトルへ戻ります]
    #   引数: []
    #   戻り値: [success: 選択を保存できた場合はtrue（bool）]
    # }
    def load_selected() -> bool:
        name = view.selected_name()
        path, error = _perform_save_action(lambda: saves.set_active(name), "セーブデータを読み込めませんでした。")
        return refresh_saved_profile(path, error, f"{name} を選択しました。ゲームを開始できます。")

    # {
    #   責務: [launch: 選択の保存に成功した記録でゲームプロセスを起動します]
    #   処理: [
    #     1: 次回起動用の選択を保存し、失敗時は起動を中止します
    #     2: セーブ先を子プロセスへ渡し、起動結果をタイトルに表示します
    #   ]
    #   引数: []
    #   戻り値: [result: なし（None）]
    # }
    def launch() -> None:
        if not load_selected():
            return
        environment = os.environ.copy()
        environment["KADOKA_SAVE_DIR"] = str(saves.profile_root(view.selected_name()))
        script = PLAYER_LAUNCH_TARGETS[0][1]
        command = [sys.executable, "--play"] if is_frozen() else [sys.executable, str(PROJECT_ROOT / script)]
        try:
            subprocess.Popen(command, cwd=PROJECT_ROOT, env=environment)
        except OSError as exc:
            view.status = f"ゲームを起動できませんでした: {exc}"
            return
        view.status = f"{view.selected_name()} でゲームを起動しました。"

    # 画面は要求IDだけを返し、保存先やゲーム起動の詳細を知りません。
    actions = {"play": launch, "create": new_save, "save_copy": save_as, "load": load_selected}
    smoke = smoke_frames()
    frames = 0
    while running:
        for event in pygame.event.get():
            action = view.handle(event)
            if action == "quit":
                running = False
                # 終了後の同じイベント束に決定キーが残っていてもゲームを起動しません。
                break
            elif action in actions:
                actions[action]()
        view.draw(screen, pygame.mouse.get_pos())
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()
