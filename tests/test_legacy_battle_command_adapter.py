from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.apps.battle_command_app import BattleCommandApplication
from kadoka_quest.apps.battle_session import BattleSession


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
