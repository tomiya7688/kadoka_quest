# {
#   責務: [test_ai_tendency_ui: test・AI・tendency・uiの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from copy import deepcopy
from unittest.mock import Mock

import pygame
import pytest

from kadoka_quest.apps import manage, ranch_manager
from kadoka_quest.core.ai import default_ai, learn_from_action
from kadoka_quest.core.ai_tendencies import summarize_tendencies
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.state import StateStore
from kadoka_quest.ui import ai_tendency_panel as panel
from kadoka_quest.ui.common import ACCENT, BG, PANEL_ALT, font


# {
#   責務: [manager_app: test・AI・tendency・uiのmanager・appを求める]
#   処理: [1: test・AI・tendency・uiのmanager・appを求める]
#   引数: [
#     request: 要求
#     monkeypatch: monkeypatch
#     tmp_path: tmp・パス
#   ]
#   戻り値: [result: test・AI・tendency・uiのmanager・appを求めるための結果（型注釈なし）]
# }
@pytest.fixture(params=[ranch_manager, manage], ids=["ranch", "developer"])
def manager_app(request, monkeypatch, tmp_path):
    app = request.param
    store = MonsterStore(tmp_path / "monsters")
    store.create("slime", monster_id="a_attack", name="攻撃スライム")
    store.create("slime", monster_id="b_healer", name="回復スライム")
    monkeypatch.setattr(app, "MonsterStore", lambda **kwargs: store)
    monkeypatch.setattr(app, "StateStore", lambda: StateStore(tmp_path / "state.json"))
    monkeypatch.setattr(app, "PartyStore", lambda: PartyStore(tmp_path / "parties"))
    cls = app.RanchManager if app is ranch_manager else app.Manager
    return app, cls(), store


# {
#   責務: [teach: test・AI・tendency・uiのteachを求める]
#   処理: [1: test・AI・tendency・uiのteachを求める]
#   引数: [
#     record: 個体レコード
#     skill_id: スキル・識別子
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def teach(record, skill_id):
    for _ in range(70):
        learn_from_action(record.ai, skill_id, 1, ("mp:low", "self:critical", "threat:stronger"))


# {
#   責務: [test_selected_individual_live_learning_and_reset: 検証: selected individual live learning and reset]
#   処理: [1: 検証: selected individual live learning and reset]
#   引数: [manager_app: manager・app]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_selected_individual_live_learning_and_reset(manager_app):
    _, manager, store = manager_app
    original = deepcopy(manager.selected_record.ai)
    assert all(row["state"] == "unlearned" for row in manager.selected_tendencies)
    assert manager.selected_record.ai == original
    teach(manager.selected_record, "attack")
    assert manager.selected_tendencies[0]["value"] > 50
    store.save(manager.selected_record)
    healer = store.get("b_healer")
    teach(healer, "small_heal")
    store.save(healer)
    manager.refresh()
    manager.selected = next(i for i, record in enumerate(manager.records) if record.monster_id == "b_healer")
    assert manager.selected_tendencies[0]["value"] < 50
    assert manager.selected_tendencies[1]["value"] > 50
    manager.reset_ai()
    assert manager.selected_record.monster_id == "b_healer"
    assert all(row["state"] == "unlearned" for row in manager.selected_tendencies)
    manager.records = []
    assert manager.selected_tendencies == []


# {
#   責務: [test_panel_shows_unknown_states_and_confines_drawing: 検証: panel shows unknown states and confines drawing]
#   処理: [1: 検証: panel shows unknown states and confines drawing]
#   引数: [
#     monkeypatch: monkeypatch
#     columns: columns
#     size: 大きさ
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("columns,size", [(2, (650, 240)), (3, (705, 180))])
def test_panel_shows_unknown_states_and_confines_drawing(monkeypatch, columns, size):
    pygame.font.init()
    surface = pygame.Surface((900, 500))
    surface.fill(BG)
    rect = pygame.Rect(40, 40, *size)
    original_clip = surface.get_clip()
    skills = {"attack": {"kind": "physical"}, "heal": {"kind": "heal", "mp_cost": 6}}
    rows = summarize_tendencies(default_ai(), skills)
    rows[1].update(state="insufficient", reason="few_observations")
    before = deepcopy(rows)
    draw_text = Mock(wraps=panel.draw_text)
    monkeypatch.setattr(panel, "draw_text", draw_text)
    panel.draw_ai_tendencies(surface, rows, rect, columns)
    text = [call.args[1] for call in draw_text.call_args_list]
    assert "未学習" in text and "データ不足" in text
    assert all(label in text for label in panel.LABELS.values())
    assert surface.get_at((rect.x + 10, rect.y + 63))[:3] == PANEL_ALT
    assert surface.get_at((rect.right + 1, rect.y))[:3] == BG
    for call in draw_text.call_args_list:
        position, font_size = call.args[2:4]
        assert rect.contains(pygame.Rect(position, font(font_size).size(str(call.args[1]))))
    assert rows == before and surface.get_clip() == original_clip
    rows[0].update(state="ready", value=75, stage="high", reason=None)
    panel.draw_ai_tendencies(surface, rows, rect, columns)
    assert surface.get_at((rect.x + 10, rect.y + 63))[:3] == ACCENT
    assert "高い" in [call.args[1] for call in draw_text.call_args_list]
    panel.draw_ai_tendencies(surface, [], rect, columns)
    assert surface.get_clip() == original_clip


# {
#   責務: [test_actual_management_screen_updates_on_f5_focus_selection_and_reset: 検証: actual management screen updates on f5 focus selection and reset]
#   処理: [1: 検証: actual management screen updates on f5 focus selection and reset]
#   引数: [
#     manager_app: manager・app
#     monkeypatch: monkeypatch
#     tmp_path: tmp・パス
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_actual_management_screen_updates_on_f5_focus_selection_and_reset(manager_app, monkeypatch, tmp_path):
    app, manager, store = manager_app
    cls_name = "RanchManager" if app is ranch_manager else "Manager"
    monkeypatch.setattr(app, cls_name, lambda: manager)
    monkeypatch.setattr(app, "smoke_frames", lambda: 5)
    captured = []
    real_draw = panel.draw_ai_tendencies
    frame = 0

    # {
    #   責務: [events: test・AI・tendency・uiのイベント一覧を求める]
    #   処理: [1: test・AI・tendency・uiのイベント一覧を求める]
    #   引数: []
    #   戻り値: [result: test・AI・tendency・uiのイベント一覧を求めるための結果（型注釈なし）]
    # }
    def events():
        nonlocal frame
        frame += 1
        if frame == 2:
            record = store.get("a_attack")
            teach(record, "attack")
            store.save(record)
            return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F5)]
        if frame == 3:
            record = store.get("b_healer")
            teach(record, "small_heal")
            store.save(record)
            return [pygame.event.Event(pygame.WINDOWFOCUSGAINED),
                    pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(80, 180))]
        if frame == 4:
            position = (1000, 335) if app is ranch_manager else (1050, 320)
            return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=position)]
        return []

    # {
    #   責務: [draw: test・AI・tendency・uiを描画する]
    #   処理: [1: test・AI・tendency・uiを描画する]
    #   引数: [
    #     surface: 描画面
    #     rows: rows
    #     rect: 表示矩形
    #     kwargs: kwargs
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def draw(surface, rows, rect, **kwargs):
        captured.append(deepcopy(rows))
        real_draw(surface, rows, rect, **kwargs)

    real_flip = pygame.display.flip

    # {
    #   責務: [flip: test・AI・tendency・uiのflipを求める]
    #   処理: [1: test・AI・tendency・uiのflipを求める]
    #   引数: []
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def flip():
        if len(captured) in (1, 2):
            name = "initial_screen.png" if len(captured) == 1 else "learned_screen.png"
            pygame.image.save(pygame.display.get_surface(), str(tmp_path / name))
        real_flip()

    monkeypatch.setattr(pygame.event, "get", events)
    monkeypatch.setattr(app, "draw_ai_tendencies", draw)
    monkeypatch.setattr(pygame.display, "flip", flip)
    app.main()
    assert len(captured) == 5
    assert all(row["state"] == "unlearned" for row in captured[0])
    assert captured[1][0]["value"] > 50
    assert captured[2][0]["value"] < 50 and captured[2][1]["value"] > 50
    assert all(row["state"] == "unlearned" for row in captured[3])
    assert all(row["state"] == "unlearned" for row in captured[4])
    assert store.get("b_healer").ai["actions"] == 0
    print(f"UI screenshot: {tmp_path / 'learned_screen.png'}")
