from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import pytest

from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.apps.field_command_app import FieldCommandApplication


def test_direct_simulation_start_command_is_no_longer_supported() -> None:
    start_simulation = mock.Mock()
    session = SimpleNamespace(start_simulation=start_simulation)
    application = FieldCommandApplication(session)

    with pytest.raises(ValueError, match="simulation.start"):
        application.handle(AppCommand("field", "simulation.start"))

    start_simulation.assert_not_called()
