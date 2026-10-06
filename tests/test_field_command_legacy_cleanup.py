# {
#   責務: [test_field_command_legacy_cleanup: test・フィールド・コマンド・legacy・cleanupの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest import mock

from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.apps.field_command_app import FieldCommandApplication


# {
#   責務: [FieldCommandLegacyCleanupTests: フィールド・コマンド・legacy・cleanup・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class FieldCommandLegacyCleanupTests(unittest.TestCase):
    # {
    #   責務: [test_direct_simulation_start_command_is_no_longer_supported: 検証: direct simulation start command is no longer supported]
    #   処理: [1: 検証: direct simulation start command is no longer supported]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_direct_simulation_start_command_is_no_longer_supported(self) -> None:
        start_simulation = mock.Mock()
        session = SimpleNamespace(start_simulation=start_simulation)
        application = FieldCommandApplication(session)

        with self.assertRaisesRegex(ValueError, "simulation.start"):
            application.handle(AppCommand("field", "simulation.start"))

        start_simulation.assert_not_called()
