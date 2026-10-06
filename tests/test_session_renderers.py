# {
#   責務: [test_session_renderers: test・セッション・renderersの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import random
from types import SimpleNamespace
from unittest import mock

import pygame
import pytest

from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.fixed_mob_controller import FixedMobController
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController
from kadoka_engine.player_field_controller import PlayerFieldController
from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.apps.field_session import FieldSession
from kadoka_quest.apps.game import KANA_KEYS, PASSWORD, draw_password
from kadoka_quest.apps.password_session import PasswordSession
from kadoka_quest.ui.battle_renderer import BattleRenderer
from kadoka_quest.ui.character_image_provider import CharacterImageProvider
from kadoka_quest.ui.common import Button
from kadoka_quest.ui.field_renderer import FIELD_RECT, draw_field


# {
#   責務: [screen: test・セッション・renderersの描画先を求める]
#   処理: [1: test・セッション・renderersの描画先を求める]
#   引数: [monkeypatch: monkeypatch]
#   戻り値: [result: 描画面（型注釈なし）]
# }
@pytest.fixture
def screen(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    surface = pygame.display.set_mode((1120, 740))
    yield surface
    pygame.display.quit()


# {
#   責務: [test_battle_renderer_uses_session_and_visual_provider_only: 検証: battle renderer uses session and visual provider only]
#   処理: [1: 検証: battle renderer uses session and visual provider only]
#   引数: [
#     screen: 描画先
#     with_image: with・画像
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("with_image", [False, True])
def test_battle_renderer_uses_session_and_visual_provider_only(screen, with_image):
    images = mock.Mock(spec=CharacterImageProvider)
    images.get.return_value = pygame.Surface((20, 20)) if with_image else None
    images.appearance.return_value = {"value": "#abcdef", "symbol": "S"}
    member = SimpleNamespace(
        record=SimpleNamespace(monster_id="slime1", species_id="slime", level=3),
        name="スライム", hp=5, mp=2, stats={"hp": 10, "mp": 5},
    )
    battle = SimpleNamespace(allies=[member], enemies=[member], outcome=None, log=["見える", "まだ見えない"], round_number=2)
    session = BattleSession()
    session.begin(battle, 0, simulation=True)
    session.focus_id = "slime1"
    session.visible_log_count = 1
    session.action_line = "攻撃中"
    session.playback = True
    before = dict(vars(session))
    buttons = [Button(pygame.Rect(355, 650, 95, 48), "戦う", lambda: None)]
    renderer = BattleRenderer(images)
    with mock.patch("kadoka_quest.ui.battle_renderer.draw_text") as text, \
         mock.patch("kadoka_quest.ui.battle_renderer.draw_wrapped") as wrapped:
        renderer.draw(screen, session, buttons)
    assert any(call.args[1] == "模擬戦（AI更新なし）" for call in text.call_args_list)
    assert [call.args[1] for call in wrapped.call_args_list] == ["攻撃中", "見える"]
    assert not buttons[0].enabled
    assert vars(session) == before
    images.get.assert_called_with("slime", "portrait", (82, 82))
    session.playback = False
    session.auto = True
    renderer.draw(screen, session, buttons)
    assert buttons[0].enabled
    battle.outcome = "victory"
    renderer.draw(screen, session, buttons)
    assert not buttons[0].enabled
    session.clear()
    renderer.draw(screen, session, buttons)


# {
#   責務: [test_field_renderer_reads_live_session_and_supplied_party: 検証: field renderer reads live session and supplied party]
#   処理: [1: 検証: field renderer reads live session and supplied party]
#   引数: [screen: 描画先]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_field_renderer_reads_live_session_and_supplied_party(screen):
    field = FieldEngine(
        {"id": "small", "display_name": "テスト", "width": 3, "height": 3, "tiles": [["floor"] * 3 for _ in range(3)]},
        {"floor": {"appearance": {"type": "color", "value": "#123456"}}},
    )
    player = PlayerFieldController(0, 0)
    fixed = FixedMobController(field, random.Random(1))
    fixed.npcs = [{"species_id": "maru", "x": 1, "y": 1, "direction": "left"}]
    session = FieldSession(field, player, fixed, HiddenEnemyController(field, random.Random(2)))
    images = mock.Mock(spec=CharacterImageProvider)
    images.get.return_value = None
    images.appearance.return_value = {"value": "#abcdef"}
    party = [SimpleNamespace(species_id="slime", name="スライム", level=2, ai={})]
    clip = screen.get_clip()
    draw_field(screen, session, images, party, 0, now=0)
    assert screen.get_clip() == clip
    assert screen.get_at((FIELD_RECT.x + 80, FIELD_RECT.y + 80))[:3] == (0x12, 0x34, 0x56)
    images.get.assert_any_call("maru", "field_left", (48, 48))
    images.get.assert_any_call("hero", "field_front", (48, 48))
    images.appearance.assert_called_once_with("slime")
    session.player.direction = "right"
    session.map_data["display_name"] = "更新後"
    with mock.patch("kadoka_quest.ui.field_renderer.draw_text") as text:
        draw_field(screen, session, images, [], 3, now=0)
    assert any(call.args[1] == "更新後" for call in text.call_args_list)
    images.get.assert_any_call("hero", "field_right", (48, 48))


# {
#   責務: [test_password_renderer_needs_only_password_session: 検証: password renderer needs only password session]
#   処理: [1: 検証: password renderer needs only password session]
#   引数: [screen: 描画先]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_password_renderer_needs_only_password_session(screen):
    session = PasswordSession(PASSWORD, KANA_KEYS)
    session.open()
    session.append("へ")
    session.message = "あいことばが違います。"
    before = dict(vars(session))
    with mock.patch("kadoka_quest.apps.game.draw_text") as text:
        draw_password(screen, session)
    assert any(call.args[1] == "へ" for call in text.call_args_list)
    assert any(call.args[1] == session.message for call in text.call_args_list)
    assert vars(session) == before
