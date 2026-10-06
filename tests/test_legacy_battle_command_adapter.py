# {
#   責務: [test_legacy_battle_command_adapter: test・legacy・戦闘・コマンド・adapterの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.apps.battle_command_app import BattleCommandApplication
from kadoka_quest.apps.battle_session import BattleSession


# {
#   責務: [test_full_runtime_shape_uses_flow_without_creating_legacy_adapter: 検証: full runtime shape uses flow without creating legacy adapter]
#   処理: [1: 検証: full runtime shape uses flow without creating legacy adapter]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_full_runtime_shape_uses_flow_without_creating_legacy_adapter() -> None:
    session = SimpleNamespace(
        battle_session=BattleSession(),
        monsters=object(),
        states=object(),
        state={},
        status="",
        mode="battle",
    )
    application = BattleCommandApplication(session)

    assert application.handle(AppCommand("battle", "selection.move", {"amount": 1})) == 1
    assert application._flow is not None
    assert application._legacy is None


# {
#   責務: [test_minimal_legacy_session_isolated_behind_adapter: 検証: minimal legacy session isolated behind adapter]
#   処理: [1: 検証: minimal legacy session isolated behind adapter]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_minimal_legacy_session_isolated_behind_adapter() -> None:
    session = SimpleNamespace(
        status="",
        handle_battle_command=mock.Mock(),
        selected_battle_command=mock.Mock(return_value="scout"),
        move_battle_selection=mock.Mock(return_value=3),
        set_battle_selection=mock.Mock(return_value=0),
        toggle_auto_battle=mock.Mock(),
        stop_auto_battle=mock.Mock(),
        update_battle_playback=mock.Mock(return_value=True),
        update_auto_battle=mock.Mock(),
        return_to_field=mock.Mock(return_value="field"),
    )
    application = BattleCommandApplication(session)

    assert application.handle(AppCommand("battle", "selection.move", {"amount": -1})) == 3
    assert application._flow is None
    assert application._legacy is not None
    session.move_battle_selection.assert_called_once_with(-1)

    application.handle(AppCommand("battle", "execute.selected"))
    session.handle_battle_command.assert_called_once_with("scout")
