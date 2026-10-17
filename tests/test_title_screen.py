# {
#   責務: [test_title_screen: タイトルの選択・文字入力・描画境界と、実ランチャーループの保存失敗時の起動抑止を検証します。]
#   フィールド: []
# }
from __future__ import annotations

from unittest.mock import Mock

import pygame
import pytest

from kadoka_quest.apps import launcher
from kadoka_quest.ui import game_ui
from kadoka_quest.ui.title_screen import TitleScreen


# {
#   責務: [title_window: 実セーブを使わないタイトル用のdummy SDL画面を用意します。]
#   処理: [1: 共通Player初期化で画面を作り、検査後にpygameを終了します。]
#   引数: [monkeypatch: テスト中だけ環境変数を差し替えるpytest機能]
#   戻り値: [result: タイトルの描画先Surfaceを返す生成器]
# }
@pytest.fixture
def title_window(monkeypatch):
    # OSの実ウィンドウ操作とは区別し、入力と描画契約だけを検査します。
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    surface = game_ui.init_pygame("title-ui-test", TitleScreen.SIZE)
    yield surface
    pygame.quit()


# {
#   責務: [key: タイトルの公開入力入口へ渡すpygameキーイベントを作ります。]
#   処理: [1: キー・文字列・修飾・リピート状態を持つイベントを返します。]
#   引数: [
#     code: pygameキーコード
#     text: 確定した文字列。操作キーでは空文字列
#     mod: Shiftなどの修飾状態
#     repeat: 長押しによる繰返し入力か
#   ]
#   戻り値: [result: KEYDOWNイベント]
# }
def key(code, text="", mod=0, repeat=False):
    return pygame.event.Event(pygame.KEYDOWN, key=code, unicode=text, mod=mod, repeat=repeat)


# {
#   責務: [open_profiles: タイトルの通常キーボード操作でセーブ一覧を開きます。]
#   処理: [1: ホームの選択を1段下げて決定します。]
#   引数: [view: ホームを表示しているTitleScreen]
#   戻り値: [result: なし]
# }
def open_profiles(view):
    view.handle(key(pygame.K_DOWN))
    view.handle(key(pygame.K_RETURN))
    assert view.mode == "profiles" and view.focus == -1


# {
#   責務: [test_empty_profiles_disable_load_copy_and_start: 空一覧から起動・読込・複製の要求が発生しないことを検証します。]
#   処理: [1: ホームと一覧の決定操作を実行し、操作要求とボタンの無効表示を確認します。]
#   引数: [title_window: タイトルのdummy描画先]
#   戻り値: [result: なし]
# }
def test_empty_profiles_disable_load_copy_and_start(title_window):
    view = TitleScreen()
    view.set_profiles([], "")
    assert view.handle(key(pygame.K_RETURN)) is None
    view.draw(title_window, (-1, -1))
    assert not view.buttons["play"].enabled
    open_profiles(view)
    for code in (pygame.K_END, pygame.K_PAGEDOWN, pygame.K_RETURN):
        assert view.handle(key(code)) is None
    assert view.selected_name() == "" and view.offset == 0
    view.draw(title_window, (-1, -1))
    assert not view.buttons["load"].enabled and not view.buttons["copy"].enabled
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=view.buttons["copy"].rect.center)
    assert view.handle(click) is None and view.mode == "profiles"


# {
#   責務: [test_hundred_profiles_support_end_page_home_and_mouse_selection: 100件の一覧をキーボードとマウスで最後まで選べることを検証します。]
#   処理: [1: 末尾・ページ・先頭へ移動し、表示行と選択名の一致を確認します。]
#   引数: [title_window: pygameを初期化したdummy描画先]
#   戻り値: [result: なし]
# }
def test_hundred_profiles_support_end_page_home_and_mouse_selection(title_window):
    view = TitleScreen()
    names = [f"冒険{index:03d}" for index in range(100)]
    view.set_profiles(names, names[0])
    open_profiles(view)
    view.handle(key(pygame.K_END))
    assert view.selected_name() == names[-1] and view.offset == 93
    view.handle(key(pygame.K_PAGEUP))
    assert view.selected == 92 and view.offset <= 92 < view.offset + view.PAGE_ROWS
    view.handle(key(pygame.K_PAGEDOWN))
    assert view.selected == 99
    assert view.handle(key(pygame.K_RETURN)) == "load"
    view.handle(key(pygame.K_HOME))
    view.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=-3))
    assert view.selected == 3
    view.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(300, 192 + 5 * 44 + 8)))
    assert view.selected == 5
    names.clear()
    assert len(view.names) == 100
    view.set_profiles(["最後の記録"], "最後の記録")
    assert view.selected == 0 and view.offset == 0


# {
#   責務: [test_tab_focus_cycles_between_list_and_actions: 台帳一覧と操作ボタンのTab巡回および逆順巡回を検証します。]
#   処理: [1: 画面内のフォーカス位置を一周させ、描画される選択も確認します。]
#   引数: [title_window: タイトルのdummy描画先]
#   戻り値: [result: なし]
# }
def test_tab_focus_cycles_between_list_and_actions(title_window):
    view = TitleScreen()
    view.set_profiles(["記録"], "記録")
    open_profiles(view)
    for expected in (0, 1, 2, -1):
        view.handle(key(pygame.K_TAB))
        assert view.focus == expected
    view.handle(key(pygame.K_TAB, mod=pygame.KMOD_SHIFT))
    view.draw(title_window, (-1, -1))
    assert view.focus == 2 and view.buttons["back"].focused
    assert not view.buttons["load"].focused
    view.handle(key(pygame.K_ESCAPE))
    assert view.mode == "home" and view.focus == 0


# {
#   責務: [test_name_input_preserves_characters_and_escape_cancels_without_action: 名前入力でXや空白を操作にせず、Escだけが入力画面を閉じることを検証します。]
#   処理: [1: 新規作成を開き文字入力・削除・Tab巡回を行い、取消の結果を確認します。]
#   引数: [title_window: pygameを初期化したdummy描画先]
#   戻り値: [result: なし]
# }
def test_name_input_preserves_characters_and_escape_cancels_without_action(title_window):
    view = TitleScreen()
    view.handle(key(pygame.K_DOWN))
    view.handle(key(pygame.K_DOWN))
    view.handle(key(pygame.K_RETURN))
    assert view.mode == "new" and view.name_field.active
    view.handle(key(pygame.K_UNKNOWN, "長い冒険"))
    view.handle(key(pygame.K_x, "x"))
    view.handle(key(pygame.K_SPACE, " ", repeat=True))
    assert view.name_field.value == "長い冒険x "
    view.handle(key(pygame.K_BACKSPACE))
    assert view.name_field.value == "長い冒険x"
    for expected in (0, 1, -1):
        view.handle(key(pygame.K_TAB))
        assert view.focus == expected
    assert view.name_field.active
    assert view.handle(key(pygame.K_ESCAPE)) is None
    assert view.mode == "home" and not view.name_field.active


# {
#   責務: [test_confirmation_repeat_does_not_reissue_actions: 決定キーの長押しが保存・起動要求を再発行しないことを検証します。]
#   処理: [1: ホーム・一覧・新規入力で通常の決定とリピートを比較します。]
#   引数: [
#     title_window: pygameを初期化したdummy描画先
#     mode: 検査するタイトル画面
#     expected: 通常押下で返る要求ID
#   ]
#   戻り値: [result: なし]
# }
@pytest.mark.parametrize(("mode", "expected"), [("home", "play"), ("profiles", "load"), ("new", "create")])
def test_confirmation_repeat_does_not_reissue_actions(title_window, mode, expected):
    view = TitleScreen()
    view.set_profiles(["記録"], "記録")
    view.mode = mode
    view.focus = 0 if mode == "home" else -1
    view.name_field.active = mode == "new"
    assert view.handle(key(pygame.K_RETURN)) == expected
    assert view.handle(key(pygame.K_RETURN, repeat=True)) is None
    assert view.mode == mode


# {
#   責務: [test_long_profile_name_is_clipped_to_its_row: 長い日本語名の画素がセーブ一覧の隣へ漏れないことを検証します。]
#   処理: [1: 長名と空名の描画を比較し、文字用矩形の外が同じ画素であることを確認します。]
#   引数: [title_window: タイトルのdummy描画先]
#   戻り値: [result: なし]
# }
def test_long_profile_name_is_clipped_to_its_row(title_window):
    view = TitleScreen()
    view.set_profiles(["長い日本語の冒険の記録" * 80], "")
    open_profiles(view)
    view.draw(title_window, (-1, -1))
    long_name = title_window.copy()
    view.set_profiles([""], "使用中ではない名前")
    view.draw(title_window, (-1, -1))
    baseline = title_window.copy()
    # 文字領域だけを同じ色で消すと、それ以外の画素は完全に一致します。
    name_rect = pygame.Rect(264, 202, 536, 28)
    long_name.fill(game_ui.BG, name_rect)
    baseline.fill(game_ui.BG, name_rect)
    assert pygame.image.tobytes(long_name, "RGB") == pygame.image.tobytes(baseline, "RGB")
    assert title_window.get_clip() == title_window.get_rect()


# {
#   責務: [launcher_dependencies: 実ランチャーの保存とプロセス境界だけをテスト用に差し替えます。]
#   処理: [1: 保存操作と起動をMockにし、本物のTitleScreenをランチャーへ渡します。]
#   引数: [
#     monkeypatch: テスト中だけ依存を差し替えるpytest機能
#     title_window: 実TitleScreenが描くdummy画面
#     tmp_path: テストだけのプロフィールルート
#   ]
#   戻り値: [result: 保存Mock・タイトル・プロセス起動Mockの組]
# }
def launcher_dependencies(monkeypatch, title_window, tmp_path):
    # ファイルI/Oと外部プロセスを遮断し、mainの要求振分けと描画は実行します。
    saves = Mock()
    saves.list_names.return_value = ["記録"]
    saves.active_name.return_value = "記録"
    saves.profile_root.return_value = tmp_path / "記録"
    saves.set_active.return_value = tmp_path / "記録"
    view = TitleScreen()
    monkeypatch.setattr(launcher, "SaveDataManager", Mock(return_value=saves))
    monkeypatch.setattr(launcher, "ensure_runtime_directories", Mock())
    monkeypatch.setattr(launcher, "DataValidator", Mock(return_value=Mock(validate=Mock(return_value=[]))))
    monkeypatch.setattr(launcher, "is_frozen", lambda: False)
    monkeypatch.setattr(launcher, "init_pygame", lambda title, size: title_window)
    monkeypatch.setattr(launcher, "TitleScreen", Mock(SIZE=TitleScreen.SIZE, return_value=view))
    monkeypatch.setattr(launcher, "smoke_frames", lambda: 1)
    monkeypatch.setattr(launcher.pygame.time, "Clock", Mock(return_value=Mock()))
    popen = Mock()
    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    return saves, view, popen


# {
#   責務: [test_main_load_failure_keeps_title_open_and_never_starts_process: 選択保存が失敗した場合に本物のmainがゲームを起動しないことを検証します。]
#   処理: [1: 保存例外を注入してEnterを渡し、起動回数と画面の失敗説明を確認します。]
#   引数: [
#     monkeypatch: テスト用依存差し替え
#     title_window: タイトルのdummy描画先
#     tmp_path: テスト専用パス
#   ]
#   戻り値: [result: なし]
# }
def test_main_load_failure_keeps_title_open_and_never_starts_process(monkeypatch, title_window, tmp_path):
    saves, view, popen = launcher_dependencies(monkeypatch, title_window, tmp_path)
    saves.set_active.side_effect = OSError("テスト用の選択保存失敗")
    monkeypatch.setattr(pygame.event, "get", Mock(return_value=[key(pygame.K_RETURN)]))
    launcher.main()
    saves.set_active.assert_called_once_with("記録")
    popen.assert_not_called()
    assert "選択保存失敗" in view.status and view.mode == "home"


# {
#   責務: [test_main_success_passes_only_selected_save_to_child_once: 選択保存に成功したmainが正しいセーブ先で一度だけ起動することを検証します。]
#   処理: [1: 通常決定とリピートを同時に渡し、子プロセスの引数と環境変数を確認します。]
#   引数: [
#     monkeypatch: テスト用依存差し替え
#     title_window: タイトルのdummy描画先
#     tmp_path: テスト専用パス
#   ]
#   戻り値: [result: なし]
# }
def test_main_success_passes_only_selected_save_to_child_once(monkeypatch, title_window, tmp_path):
    saves, view, popen = launcher_dependencies(monkeypatch, title_window, tmp_path)
    monkeypatch.setattr(pygame.event, "get", Mock(return_value=[key(pygame.K_RETURN), key(pygame.K_RETURN, repeat=True)]))
    launcher.main()
    saves.set_active.assert_called_once_with("記録")
    popen.assert_called_once()
    assert popen.call_args.kwargs["env"]["KADOKA_SAVE_DIR"] == str(tmp_path / "記録")
    assert popen.call_args.args[0][-1].endswith("game.py")
    assert "ゲームを起動しました" in view.status


# {
#   責務: [test_main_quit_discards_later_confirmation_in_same_event_batch: 終了イベント後の決定キーがゲームを起動しないことを検証します。]
#   処理: [1: QUITとEnterを同じイベント束に入れ、保存と起動が行われないことを確認します。]
#   引数: [
#     monkeypatch: テスト用依存差し替え
#     title_window: タイトルのdummy描画先
#     tmp_path: テスト専用パス
#   ]
#   戻り値: [result: なし]
# }
def test_main_quit_discards_later_confirmation_in_same_event_batch(monkeypatch, title_window, tmp_path):
    saves, _view, popen = launcher_dependencies(monkeypatch, title_window, tmp_path)
    monkeypatch.setattr(pygame.event, "get", Mock(return_value=[pygame.event.Event(pygame.QUIT), key(pygame.K_RETURN)]))
    launcher.main()
    saves.set_active.assert_not_called()
    popen.assert_not_called()


# {
#   責務: [test_main_create_failure_preserves_form_and_typed_name: 新規保存の失敗時にmainが名前と入力画面を保持することを検証します。]
#   処理: [1: キー操作で名前を入力し、保存失敗後の画面状態を確認します。]
#   引数: [
#     monkeypatch: テスト用依存差し替え
#     title_window: タイトルのdummy描画先
#     tmp_path: テスト専用パス
#   ]
#   戻り値: [result: なし]
# }
def test_main_create_failure_preserves_form_and_typed_name(monkeypatch, title_window, tmp_path):
    saves, view, popen = launcher_dependencies(monkeypatch, title_window, tmp_path)
    saves.create.side_effect = ValueError("同名の記録があります")
    events = [key(pygame.K_DOWN), key(pygame.K_DOWN), key(pygame.K_RETURN), key(pygame.K_UNKNOWN, "冒険の続き"), key(pygame.K_RETURN)]
    monkeypatch.setattr(pygame.event, "get", Mock(return_value=events))
    launcher.main()
    saves.create.assert_called_once_with("冒険の続き")
    assert view.mode == "new" and view.name_field.value == "冒険の続き"
    assert "同名" in view.status
    popen.assert_not_called()
