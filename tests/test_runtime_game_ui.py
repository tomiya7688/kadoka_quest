# {
#   責務: [test_runtime_game_ui: ゲーム用レイアウトの入力位置と会話ページ、メニューの意味コマンドを検証します]
#   フィールド: []
# }
from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import pygame
import pytest

import kadoka_quest.apps.game as game_app
from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.ui.battle_renderer import COMMAND_RECTS, BattleRenderer
from kadoka_quest.ui.field_overlay import FieldOverlay, MENU_BUTTON, MENU_ITEMS, MENU_RECTS, PARTY_RECTS
from kadoka_quest.ui.game_ui import BG, TEXT, Button, draw_text, draw_wrapped
from kadoka_quest.ui.runtime_input_adapter import RuntimeInputAdapter
from kadoka_quest.ui.runtime_mouse_adapter import RuntimeMouseAdapter


# {
#   責務: [screen: 実ウィンドウを開かずゲームUIの描画先を用意します]
#   処理: [1: pygameの文字機能とメモリ上の描画面を用意します]
#   引数: []
#   戻り値: [result: 1120x740の検証用Surface]
# }
@pytest.fixture
def screen():
    pygame.font.init()
    return pygame.Surface((1120, 740))


# {
#   責務: [key: メニューの検証で押下キーをpygameイベントとして作ります]
#   処理: [1: 指定キーの一回押下イベントを作ります]
#   引数: [value: pygameのキー定数]
#   戻り値: [result: KEYDOWNイベント]
# }
def key(value):
    return pygame.event.Event(pygame.KEYDOWN, key=value, repeat=False)


# {
#   責務: [test_field_menu_stops_held_movement_and_dispatches_existing_actions: メニューを開いた時の移動解除と既存管理画面への遷移要求を検証します]
#   処理: [1: 開閉・移動・決定を順に入力し、意味要求とUI状態を比較します]
#   引数: []
#   戻り値: [result: なし。ゲームSessionや実セーブは使用しません]
# }
def test_field_menu_stops_held_movement_and_dispatches_existing_actions():
    overlay = FieldOverlay()
    requests = overlay.handle_event(key(pygame.K_ESCAPE))
    assert overlay.opened
    assert {request["payload"]["direction"] for request in requests} == {"left", "right", "back", "front"}
    assert all(request["action"] == "move.stop" for request in requests)
    assert overlay.handle_event(key(pygame.K_DOWN)) == []
    assert overlay.handle_event(key(pygame.K_RETURN)) == [{"kind": "command", "target": "manager", "action": "open", "payload": {}}]
    assert not overlay.opened


# {
#   責務: [test_field_menu_help_returns_to_same_selection_and_party_click_selects: 操作説明から戻る選択保持と個体の表示枠クリックを検証します]
#   処理: [1: 説明を開閉し、パーティ枠のクリックが対応する個体番号を返すか確認します]
#   引数: []
#   戻り値: [result: なし]
# }
def test_field_menu_help_returns_to_same_selection_and_party_click_selects():
    overlay = FieldOverlay()
    overlay.handle_event(key(pygame.K_ESCAPE))
    help_index = next(index for index, item in enumerate(MENU_ITEMS) if item[1] == "help")
    overlay.selection = help_index
    assert overlay.handle_event(key(pygame.K_RETURN)) == []
    assert overlay.help_open
    assert overlay.handle_event(key(pygame.K_ESCAPE)) == []
    assert overlay.opened and not overlay.help_open
    assert overlay.selection == help_index
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=PARTY_RECTS[2].center)
    assert overlay.handle_event(event) == [{"kind": "command", "target": "field", "action": "party.select", "payload": {"index": 2}}]
    assert overlay.opened


# {
#   責務: [test_field_menu_mouse_buttons_use_the_same_actions_as_keyboard: メニューの表示枠中央が対応する既存コマンドを返すか検証します]
#   処理: [1: 開くボタンと対象項目の中央を押し、宛先と操作名を比較します]
#   引数: [index: 検証するゲーム操作のメニュー項目番号]
#   戻り値: [result: なし]
# }
@pytest.mark.parametrize("index", [1, 2, 3, 4, 5, 7])
def test_field_menu_mouse_buttons_use_the_same_actions_as_keyboard(index):
    overlay = FieldOverlay()
    overlay.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=MENU_BUTTON.center))
    requests = overlay.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=MENU_RECTS[index].center))
    assert requests[0]["target"] == MENU_ITEMS[index][1]
    assert requests[0]["action"] == MENU_ITEMS[index][2]
    assert not overlay.opened


# {
#   責務: [test_dialogue_keeps_all_pages_and_does_not_dispatch_interaction_until_last: 長いNPC会話を失わず、途中のページ送りがゲーム操作を再実行しないことを検証します]
#   処理: [1: 四行の会話を表示して次ページへ送り、末尾では既存入力へ戻すことを確認します]
#   引数: [screen: メモリ上の描画面]
#   戻り値: [result: なし]
# }
def test_dialogue_keeps_all_pages_and_does_not_dispatch_interaction_until_last(screen):
    overlay = FieldOverlay()
    overlay.observe_message("まる『一行目\n二行目\n三行目\n四行目』", 100)
    assert overlay.speaker == "まる"
    assert overlay.lines == ("一行目", "二行目", "三行目", "四行目")
    assert overlay.handle_event(key(pygame.K_SPACE)) == []
    assert overlay.page == 1
    with mock.patch("kadoka_quest.ui.field_overlay.draw_text") as text:
        overlay.draw(screen, [], 0, 10000)
    assert "四行目" in [call.args[1] for call in text.call_args_list]
    assert overlay.handle_event(key(pygame.K_SPACE)) is None
    overlay.handle_event(key(pygame.K_RIGHT))
    assert overlay.dismissed
    overlay.handle_event(key(pygame.K_SPACE))
    assert not overlay.dismissed


# {
#   責務: [test_plain_field_notice_expires_but_npc_dialogue_remains: 通常通知の表示寿命と会話の継続表示を区別して検証します]
#   処理: [1: 通知と会話をそれぞれ期限後に描き、会話本文だけが残ることを確認します]
#   引数: [screen: メモリ上の描画面]
#   戻り値: [result: なし]
# }
def test_plain_field_notice_expires_but_npc_dialogue_remains(screen):
    overlay = FieldOverlay()
    overlay.observe_message("街へ入りました。", 100)
    with mock.patch("kadoka_quest.ui.field_overlay.draw_text") as text:
        overlay.draw(screen, [], 0, 7000)
    assert "街へ入りました。" not in [call.args[1] for call in text.call_args_list]
    overlay.observe_message("かどか『こんにちは。』", 100)
    with mock.patch("kadoka_quest.ui.field_overlay.draw_text") as text:
        overlay.draw(screen, [], 0, 7000)
    assert "こんにちは。" in [call.args[1] for call in text.call_args_list]


# {
#   責務: [test_battle_command_hitboxes_dispatch_and_disable_during_playback: 戦闘の新しい下段コマンド枠が正しい要求を返し、演出中は入力しないことを検証します]
#   処理: [1: 四つの枠内と枠間をクリックし、実行要求と無効状態を確認します]
#   引数: []
#   戻り値: [result: なし]
# }
def test_battle_command_hitboxes_dispatch_and_disable_during_playback():
    commands = ("fight", "scout", "item", "run")
    adapter = RuntimeMouseAdapter([], {}, zip(commands, COMMAND_RECTS))
    bounds = pygame.Rect(0, 0, 1120, 740)
    for command, rect in zip(commands, COMMAND_RECTS):
        assert bounds.contains(rect)
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        requests = adapter.translate(event, "battle", now=123)
        assert requests[0]["payload"] == {"index": commands.index(command)}
        assert requests[1]["payload"] == {"command": command, "now": 123}
        assert adapter.translate(event, "battle", battle_enabled=False) == []
    gap = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(288, 670))
    assert adapter.translate(gap, "battle") == []


# {
#   責務: [test_battle_status_display_does_not_modify_effects: 個体の状態表示が状態異常の辞書を変更しないことを検証します]
#   処理: [1: 既知状態とMOD状態の表示を求め、元の効果を比較します]
#   引数: []
#   戻り値: [result: なし]
# }
def test_battle_status_display_does_not_modify_effects():
    member = SimpleNamespace(hp=5, fled=False, status_effects=[{"id": "bleeding", "remaining": 2}, "mod_status"])
    assert BattleRenderer._status_text(member) == "出血 / mod_status"
    assert member.status_effects == [{"id": "bleeding", "remaining": 2}, "mod_status"]
    member.hp = 0
    assert BattleRenderer._status_text(member) == "戦闘不能"
    member.fled = True
    assert BattleRenderer._status_text(member) == "逃走済み"


# {
#   責務: [test_enter_confirm_uses_existing_field_interact_command: ゲームパッドからも使うEnter決定が既存の調べる操作へ変換されることを検証します]
#   処理: [1: EnterとSpaceの出力要求を比較します]
#   引数: []
#   戻り値: [result: なし]
# }
def test_enter_confirm_uses_existing_field_interact_command():
    adapter = RuntimeInputAdapter({})
    assert adapter.translate(key(pygame.K_RETURN), "field", 0) == adapter.translate(key(pygame.K_SPACE), "field", 0)


# {
#   責務: [test_field_dpad_neutral_releases_movement_without_starting_another_step: 十字キーを離す入力が移動を止め、別の移動を開始しないことを検証します]
#   処理: [1: 右方向と中立を変換し、開始時刻と停止要求を比較します]
#   引数: []
#   戻り値: [result: なし]
# }
def test_field_dpad_neutral_releases_movement_without_starting_another_step():
    adapter = RuntimeInputAdapter({})
    pressed = pygame.event.Event(pygame.JOYHATMOTION, value=(1, 0), hat=0)
    neutral = pygame.event.Event(pygame.JOYHATMOTION, value=(0, 0), hat=0)
    requests = adapter.translate(pressed, "field", 123)
    assert requests[-1]["action"] == "move.start"
    assert requests[-1]["payload"] == {"direction": "right", "now": 123}
    released = adapter.translate(neutral, "field", 200)
    assert len(released) == 4
    assert all(request["action"] == "move.stop" for request in released)


# {
#   責務: [test_menu_and_dialogue_ignore_repeated_confirm_keys: Escと決定キーの長押しが開閉や会話ページを繰り返さないことを検証します]
#   処理: [1: 通常押下の直後にrepeat付き入力を送り、表示状態と要求が変わらないことを確認します]
#   引数: []
#   戻り値: [result: なし]
# }
def test_menu_and_dialogue_ignore_repeated_confirm_keys():
    overlay = FieldOverlay()
    overlay.handle_event(key(pygame.K_ESCAPE))
    assert overlay.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=True)) == []
    assert overlay.opened
    overlay.handle_event(key(pygame.K_ESCAPE))
    overlay.observe_message("まる『一\n二\n三\n四\n五\n六\n七』", 0)
    overlay.handle_event(key(pygame.K_SPACE))
    assert overlay.page == 1
    assert overlay.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, repeat=True)) == []
    assert overlay.page == 1


# {
#   責務: [test_menu_uses_japanese_tactic_labels_and_keeps_unknown_mod_names: 既知の行動指針は日本語で表示し、MOD独自名は保持することを検証します]
#   処理: [1: 既知指針と未知指針の個体を描き、表示文字列を比較します]
#   引数: [screen: メモリ上の描画面]
#   戻り値: [result: なし]
# }
def test_menu_uses_japanese_tactic_labels_and_keeps_unknown_mod_names(screen):
    overlay = FieldOverlay()
    overlay.opened = True
    party = [SimpleNamespace(name="まる", level=1, ai={"tactic": tactic}) for tactic in ("balanced", "mod_tactic")]
    with mock.patch("kadoka_quest.ui.field_overlay.draw_text_clipped") as text:
        overlay.draw(screen, party, 0, 0)
    values = [call.args[1] for call in text.call_args_list]
    assert "行動指針: バランス" in values
    assert "行動指針: mod_tactic" in values


# {
#   責務: [test_runtime_quit_discards_later_events_and_skips_the_tick: 終了イベントの後に届いた決定入力や同フレームの更新を実行しないことを検証します]
#   処理: [1: 保存を持たないゲームの代役へ終了と決定を送り、runtimeが呼ばれないことを確認します]
#   引数: [screen: メモリ上の描画面]
#   戻り値: [result: なし。実セーブ・実ウィンドウ・外部プロセスは使用しません]
# }
def test_runtime_quit_discards_later_events_and_skips_the_tick(screen):
    runtime = mock.Mock()
    game = SimpleNamespace(character_images=object(), battle_session=SimpleNamespace(battle=None, playback=False), mode="field", runtime=runtime)
    events = [pygame.event.Event(pygame.QUIT), key(pygame.K_SPACE)]
    with mock.patch.object(game_app, "KadokaQuest", return_value=game), \
         mock.patch.object(game_app, "init_pygame", return_value=screen), \
         mock.patch.object(game_app, "smoke_frames", return_value=1), \
         mock.patch("pygame.event.get", return_value=events), \
         mock.patch("pygame.quit"):
        game_app.main()
    runtime.dispatch.assert_not_called()


# {
#   責務: [test_battle_outcomes_render_japanese_results_only_after_playback: 実際の五種類の戦闘結果を日本語で描き、再生中は結果を先出ししないことを検証します]
#   処理: [
#     1: 結果確定済みの戦闘Sessionを再生中または再生後の状態にします
#     2: 本物の描画関数で描き、結果本文の画素・進行表示・操作無効化を比較します
#     3: 未公開ログとSessionの状態が描画によって変わらないことを確認します
#   ]
#   引数: [
#     screen: 実ウィンドウを持たない描画先Surface
#     outcome: BattleEngineが生成する戦闘終了の識別子
#     label: 終了識別子に対応する期待する日本語の結果
#     playback: 最終行動のログを再生しているか
#   ]
#   戻り値: [result: なし。実セーブ・戦闘計算・外部プロセスは使用しません]
# }
@pytest.mark.parametrize("outcome,label", [
    ("victory", "勝利した！"),
    ("defeat", "パーティは戦闘不能になった。"),
    ("escaped", "戦闘から離れた。"),
    ("enemies_fled", "相手は全員逃げ去った。"),
    ("scouted", "スカウトに成功した！"),
])
@pytest.mark.parametrize("playback", [False, True])
def test_battle_outcomes_render_japanese_results_only_after_playback(screen, outcome, label, playback):
    member = SimpleNamespace(
        record=SimpleNamespace(monster_id="fixture", species_id="slime", level=3),
        name="スライム", hp=5, mp=2, stats={"hp": 10, "mp": 5}, status_effects=[], fled=False,
    )
    battle = SimpleNamespace(
        allies=[member], enemies=[member], outcome=outcome,
        log=["公開済みの行動", "まだ公開していない結果"], round_number=2,
    )
    session = BattleSession()
    session.begin(battle, 0)
    session.playback = playback
    session.auto = True
    session.visible_log_count = 1
    session.action_line = "現在の行動です。"
    before = dict(vars(session))
    images = mock.Mock()
    images.get.return_value = pygame.Surface((20, 20))
    buttons = [Button(rect.copy(), name, lambda: None) for rect, name in zip(COMMAND_RECTS, ("たたかう", "スカウト", "どうぐ", "にげる"))]
    screen.fill(BG)
    # 呼び出しを記録しながら実際の文字を描き、空のMock描画だけで合格にしません。
    with mock.patch("kadoka_quest.ui.battle_renderer.draw_text", wraps=draw_text) as text, \
         mock.patch("kadoka_quest.ui.battle_renderer.draw_wrapped", wraps=draw_wrapped) as wrapped, \
         mock.patch("pygame.mouse.get_pos", return_value=(-1, -1)):
        BattleRenderer(images).draw(screen, session, buttons)
    expected_action = "現在の行動です。" if playback else f"{label}  Enterでフィールドへ"
    expected_mode = "行動演出中" if playback else "戦闘終了"
    assert [call.args[1] for call in wrapped.call_args_list] == [expected_action, "公開済みの行動"]
    assert f"2ターン  /  {expected_mode}" in [call.args[1] for call in text.call_args_list]
    assert all(not button.enabled and not button.focused for button in buttons)
    assert vars(session) == before
    assert battle.log == ["公開済みの行動", "まだ公開していない結果"]
    # 結果本文の画素を独立した期待Surfaceと比較し、再生中の結果先出しも検出します。
    action_rect = pygame.Rect(76, 504, 996, 52)
    expected = pygame.Surface(screen.get_size())
    expected.fill(BG)
    draw_wrapped(expected, expected_action, action_rect, 16, TEXT)
    assert pygame.image.tobytes(screen.subsurface(action_rect), "RGB") == pygame.image.tobytes(expected.subsurface(action_rect), "RGB")
