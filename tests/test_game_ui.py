# {
#   責務: [test_game_ui: Player専用の文字描画、選択操作、一覧境界、牧場の画面接続を検証する]
#   フィールド: []
# }
from __future__ import annotations

from copy import deepcopy
from unittest.mock import Mock

import pygame
import pytest

from kadoka_quest.ui import common, game_ui
from kadoka_quest.ui.game_ai_tendency_panel import draw_ai_tendencies


# {
#   責務: [pixel_window: テスト専用の小さなPlayerウィンドウを用意して終了時に閉じる]
#   処理: [1: Playerの初期化経路でウィンドウを作り、検証後にpygameを終了する]
#   引数: []
#   戻り値: [result: テスト用の描画Surfaceを一度返す生成器]
# }
@pytest.fixture
def pixel_window():
    # テスト実行側のdummy SDL設定を使用し、実セーブには触れない。
    surface = game_ui.init_pygame("pixel-ui-test", (320, 240))
    yield surface
    pygame.quit()


# {
#   責務: [test_native_pixel_font_scales_exactly_and_returns_independent_images: 整数拡大とキャッシュ画像の独立性を検証する]
#   処理: [1: 日本語字形の2倍画像を比較し、取得画像の変更が次の描画へ漏れないことを確かめる]
#   引数: [pixel_window: 初期化済みのテストウィンドウ]
#   戻り値: [result: なし（None）]
# }
def test_native_pixel_font_scales_exactly_and_returns_independent_images(pixel_window):
    # 同じ16px範囲の指定は同じフォントを共有し、エディターの配色は変更しない。
    assert game_ui.font(14) is game_ui.font(22)
    assert common.BG != game_ui.BG and common.ACCENT != game_ui.ACCENT
    small = game_ui.font(16).render("牧場の仲間", True, game_ui.TEXT)
    large = game_ui.font(32).render("牧場の仲間", True, game_ui.TEXT)
    expected = pygame.transform.scale(small, (small.get_width() * 2, small.get_height() * 2))
    assert pygame.image.tobytes(large, "RGBA") == pygame.image.tobytes(expected, "RGBA")
    before = pygame.image.tobytes(small, "RGBA")
    small.fill((200, 0, 0))
    assert pygame.image.tobytes(game_ui.font(16).render("牧場の仲間", False, game_ui.TEXT), "RGBA") == before


# {
#   責務: [test_reopening_player_window_reloads_font_resources: pygame終了後の再起動で古いフォントを再利用しないことを検証する]
#   処理: [1: 終了前後のフォントが別のインスタンスで、再起動後も日本語を描けることを確かめる]
#   引数: [pixel_window: 初期化済みのテストウィンドウ]
#   戻り値: [result: なし（None）]
# }
def test_reopening_player_window_reloads_font_resources(pixel_window):
    # 牧場からゲームへ戻り再び牧場を開く経路と同じ初期化を実行する。
    first = game_ui.font(16)
    pygame.quit()
    game_ui.init_pygame("reopened", (320, 240))
    assert game_ui.font(16) is not first
    assert game_ui.font(16).render("再開", False, game_ui.TEXT).get_width() > 0


# {
#   責務: [test_direct_pygame_restart_recovers_existing_font_for_measurement_and_rendering: pygameを直接再起動しても保持済みフォントが計測と描画を再開できることを検証する]
#   処理: [1: フォント参照を保持したままpygameを再起動し、未描画文字の計測と描画を確認する]
#   引数: [pixel_window: 初期化済みのテストウィンドウ]
#   戻り値: [result: なし（None）]
# }
def test_direct_pygame_restart_recovers_existing_font_for_measurement_and_rendering(pixel_window):
    # ゲーム起動元やE2Eドライバーが専用の初期化関数を通らない経路を再現する。
    existing = game_ui.font(16)
    expected = existing.size("再起動後の日本語")
    pygame.quit()
    pygame.init()
    assert existing.size("再起動後の日本語") == expected
    assert existing.get_height() > 0 and existing.get_linesize() > 0
    pygame.quit()
    pygame.init()
    image = existing.render("再起動後に初めて描く文字", False, game_ui.TEXT)
    assert image.get_width() > 0
    game_ui.draw_text(pygame.Surface((320, 240)), "再起動後の直接描画", (0, 0), 16)


# {
#   責務: [test_japanese_wrapping_preserves_content_and_explicit_blank_lines: 長い日本語と明示空行の内容を折り返しで失わないことを検証する]
#   処理: [1: 全文字、空行、各行の幅、空領域の戻り値を比較する]
#   引数: [pixel_window: 初期化済みのテストウィンドウ]
#   戻り値: [result: なし（None）]
# }
def test_japanese_wrapping_preserves_content_and_explicit_blank_lines(pixel_window):
    # ページ送り用の行列から、改行以外の全ての入力文字を復元できる。
    message = "長い日本語の説明が途中で消えません。" * 30 + "\n\n次の話です。"
    lines = game_ui.wrap_lines(message, 96)
    assert "".join(lines) == message.replace("\n", "")
    assert "" in lines
    assert all(game_ui.font(16).size(line)[0] <= 96 for line in lines)
    assert game_ui.wrap_lines(message, 0) == ()
    assert game_ui.wrap_lines("", 96) == ()


# {
#   責務: [test_clipped_text_and_wrapping_restore_clip_without_painting_neighbors: 長い日本語表示が隣のパネルや外側の描画範囲を変更しないことを検証する]
#   処理: [1: 制限した矩形へ文字を描き、外側の画素とクリップ状態を比較する]
#   引数: [pixel_window: 初期化済みのテストウィンドウ]
#   戻り値: [result: なし（None）]
# }
def test_clipped_text_and_wrapping_restore_clip_without_painting_neighbors(pixel_window):
    # 既存のクリップが指定矩形より狭い場合も、外側の制限を維持する。
    marker = (19, 41, 63)
    pixel_window.fill(marker)
    original = pixel_window.copy()
    area = pygame.Rect(40, 40, 96, 58)
    clip = pygame.Rect(45, 35, 82, 75)
    pixel_window.set_clip(clip)
    game_ui.draw_text_clipped(pixel_window, "非常に長い個体名" * 100, area)
    game_ui.draw_wrapped(pixel_window, "日本語の説明\n次の行" * 100, area)
    assert pixel_window.get_clip() == clip
    pixel_window.set_clip(None)
    pixel_window.fill(marker, area.clip(clip))
    assert pygame.image.tobytes(pixel_window, "RGB") == pygame.image.tobytes(original, "RGB")
    assert area == pygame.Rect(40, 40, 96, 58)


# {
#   責務: [test_button_focus_disabled_and_repeat_execute_only_one_action: フォーカス中の有効な決定だけがボタン操作を一度実行することを検証する]
#   処理: [1: フォーカス、キーリピート、無効状態を切り替えて操作回数を確認する]
#   引数: [pixel_window: 初期化済みのテストウィンドウ]
#   戻り値: [result: なし（None）]
# }
def test_button_focus_disabled_and_repeat_execute_only_one_action(pixel_window):
    action = Mock()
    rect = pygame.Rect(20, 20, 90, 40)
    button = game_ui.Button(rect, "とても長い操作ラベル", action)
    button.rect.x += 1
    assert rect.x == 20
    key = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert not button.handle(key)
    button.focused = True
    assert button.handle(key)
    assert not button.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=True))
    button.enabled = False
    assert not button.handle(key)
    action.assert_called_once_with()
    # 無効ボタンも描画でき、長いラベルの処理でクリップ状態を残さない。
    button.draw(pixel_window, (-1, -1))
    assert pixel_window.get_clip() == pixel_window.get_rect()


# {
#   責務: [test_text_field_preserves_full_value_and_does_not_paint_outside: 長い入力値が表示の切り抜きで失われないことを検証する]
#   処理: [1: 入力欄を描き、値、呼び出し元矩形、外側の画素を比較する]
#   引数: [pixel_window: 初期化済みのテストウィンドウ]
#   戻り値: [result: なし（None）]
# }
def test_text_field_preserves_full_value_and_does_not_paint_outside(pixel_window):
    marker = (19, 41, 63)
    pixel_window.fill(marker)
    original = pixel_window.copy()
    rect = pygame.Rect(40, 60, 80, 36)
    value = "長いセーブ名" * 80
    field = game_ui.TextField(rect, value)
    field.active = True
    field.draw(pixel_window)
    assert field.value == value and field.rect is not rect
    pixel_window.fill(marker, rect)
    assert pygame.image.tobytes(pixel_window, "RGB") == pygame.image.tobytes(original, "RGB")


# {
#   責務: [test_scrollbar_tiny_track_large_list_and_empty_refresh: 小さいバーと大量項目でもつまみが外へ出ず、空一覧で状態が戻ることを検証する]
#   処理: [1: 大量項目の末尾、短いバー、空一覧への更新を確認する]
#   引数: [pixel_window: 初期化済みのテストウィンドウ]
#   戻り値: [result: なし（None）]
# }
def test_scrollbar_tiny_track_large_list_and_empty_refresh(pixel_window):
    # 小さい表示領域でもつまみ全体がバー内に収まり、元の矩形を共有しない。
    rect = pygame.Rect(10, 10, 8, 6)
    scroll = game_ui.ScrollBar(rect, total=1_000_000, page=9)
    scroll.value = scroll.maximum
    assert rect.contains(scroll.thumb_rect()) and scroll.rect is not rect
    scroll.dragging = True
    scroll.configure(0, 9)
    assert scroll.value == 0 and not scroll.dragging
    assert scroll.thumb_rect() == rect
    scroll.draw(pixel_window, (12, 12))
    assert not scroll.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(12, 12)))


# {
#   責務: [test_list_navigation_keeps_selection_visible_at_all_boundaries: 空一覧と大量項目で選択と表示範囲の境界が保たれることを検証する]
#   処理: [1: 末尾・ページ戻り・先頭・空一覧への移動結果を確認する]
#   引数: []
#   戻り値: [result: なし（None）]
# }
def test_list_navigation_keeps_selection_visible_at_all_boundaries():
    selected, offset = game_ui.move_list_selection(0, 0, 1_000_000, 9, pygame.K_END)
    assert (selected, offset) == (999_999, 999_991)
    selected, offset = game_ui.move_list_selection(selected, offset, 1_000_000, 9, pygame.K_PAGEUP)
    assert offset <= selected < offset + 9
    assert game_ui.move_list_selection(selected, offset, 1_000_000, 9, pygame.K_HOME) == (0, 0)
    assert game_ui.move_list_selection(12, 4, 0, 9, pygame.K_DOWN) == (0, 0)


# {
#   責務: [test_gamepad_navigation_does_not_modify_original_events: デジタルゲームパッドの変換が元イベントを変更しないことを検証する]
#   処理: [1: 方向と決定をキーへ変換し、未対応イベントをそのまま返すことを確認する]
#   引数: []
#   戻り値: [result: なし（None）]
# }
def test_gamepad_navigation_does_not_modify_original_events():
    event = pygame.event.Event(pygame.JOYHATMOTION, value=(0, -1))
    assert game_ui.navigation_event(event).key == pygame.K_DOWN
    assert event.type == pygame.JOYHATMOTION
    assert game_ui.navigation_event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=0)).key == pygame.K_RETURN
    untouched = pygame.event.Event(pygame.JOYAXISMOTION, axis=0, value=0.6)
    assert game_ui.navigation_event(untouched) is untouched


# {
#   責務: [test_gamepad_devices_are_retained_and_removed_by_instance: ゲームパッド接続を保持し、切断した機器だけを解放することを検証する]
#   処理: [1: 模擬デバイスの接続を初期化し、切断通知後の保持表と解放回数を確認する]
#   引数: [monkeypatch: pygameの機器列挙を模擬デバイスへ差し替えるpytest機能]
#   戻り値: [result: なし（None）]
# }
def test_gamepad_devices_are_retained_and_removed_by_instance(monkeypatch):
    from kadoka_quest.ui.game_navigation import GamepadDevices

    # 実機の接続状態を変更せず、参照保持と切断の契約を検証する。
    device = Mock()
    device.get_instance_id.return_value = 17
    monkeypatch.setattr(pygame.joystick, "init", Mock())
    monkeypatch.setattr(pygame.joystick, "get_count", lambda: 1)
    monkeypatch.setattr(pygame.joystick, "Joystick", lambda index: device)
    devices = GamepadDevices()
    devices.open()
    assert devices.devices[17] is device
    device.init.assert_called_once_with()
    devices.remove(17)
    devices.remove(17)
    assert devices.devices == {}
    device.quit.assert_called_once_with()


# {
#   責務: [test_game_learning_panel_preserves_rows_and_clip: Playerの学習ゲージが入力データと外側の描画範囲を変更しないことを検証する]
#   処理: [1: 学習済みと未学習の項目を狭い領域へ描き、入力とクリップを比較する]
#   引数: [pixel_window: 初期化済みのテストウィンドウ]
#   戻り値: [result: なし（None）]
# }
def test_game_learning_panel_preserves_rows_and_clip(pixel_window):
    rows = [{"id": "aggression", "state": "ready", "stage": "high", "value": 75},
            {"id": "healing", "state": "unlearned", "stage": None, "value": None}]
    original = deepcopy(rows)
    clip = pygame.Rect(20, 20, 220, 150)
    pixel_window.set_clip(clip)
    draw_ai_tendencies(pixel_window, rows, pygame.Rect(10, 10, 160, 140))
    assert rows == original and pixel_window.get_clip() == clip


# {
#   責務: [test_ranch_keyboard_reaches_last_owned_and_preset_without_saving: 牧場の実描画ループでキーボードから一覧末尾へ移動しても保存が発生しないことを検証する]
#   処理: [
#     1: 一時保存領域に大量個体とプリセットを準備する
#     2: キーイベントで所有一覧とプリセット一覧の末尾へ移動する
#     3: 表示位置と保存内容の不変を確認する
#   ]
#   引数: [
#     monkeypatch: アプリの保存先と入力をテスト用に差し替えるpytest機能
#     tmp_path: テスト専用の一時ディレクトリ
#   ]
#   戻り値: [result: なし（None）]
# }
def test_ranch_keyboard_reaches_last_owned_and_preset_without_saving(monkeypatch, tmp_path):
    from kadoka_quest.apps import ranch_manager
    from kadoka_quest.data.monsters import MonsterStore
    from kadoka_quest.data.parties import PartyStore
    from kadoka_quest.data.state import StateStore

    # 実データを使用せず、初期化とプリセット作成も一時ディレクトリだけへ保存する。
    store = MonsterStore(tmp_path / "monsters")
    for index in range(15):
        store.create("slime", monster_id=f"owned_{index:02}", name="長い日本語の仲間名" * 8)
    parties = PartyStore(tmp_path / "parties")
    for index in range(13):
        parties.save(f"編成{index:02}", ["owned_00"])
    states = StateStore(tmp_path / "state.json")
    monkeypatch.setattr(ranch_manager, "MonsterStore", lambda **kwargs: store)
    monkeypatch.setattr(ranch_manager, "PartyStore", lambda: parties)
    monkeypatch.setattr(ranch_manager, "StateStore", Mock(return_value=states, party_records=StateStore.party_records))
    manager = ranch_manager.RanchManager()
    monkeypatch.setattr(ranch_manager, "RanchManager", lambda: manager)
    monkeypatch.setattr(ranch_manager, "smoke_frames", lambda: 1)
    before = {path: path.read_bytes() for path in tmp_path.rglob("*.json")}
    events = [
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END),
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB),
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB),
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN),
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=pygame.KMOD_SHIFT),
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END),
    ]
    monkeypatch.setattr(pygame.event, "get", lambda: events)
    # UIの状態だけが変化し、選択移動とタブ切替では保存内容が変わらない。
    ranch_manager.main()
    assert manager.selected == len(manager.records) - 1
    assert manager.offset == len(manager.records) - 9
    assert manager.tab == "party"
    assert manager.selected_preset == len(manager.presets) - 1
    assert manager.preset_offset == len(manager.presets) - 8
    assert {path: path.read_bytes() for path in tmp_path.rglob("*.json")} == before
