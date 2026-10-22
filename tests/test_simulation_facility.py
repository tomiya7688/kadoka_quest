# {
#   責務: [test_simulation_facility: test・simulation・facilityの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
import random
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import pygame

from kadoka_quest.apps.field_event_app import FieldEventApplication
from kadoka_quest.apps.manager_process_service import ManagerProcessService
from kadoka_quest.apps.simulation_facility_hooks import (
    install_simulation_facility_hooks,
    open_simulation_manager,
    refresh_simulation_if_closed,
)
from kadoka_quest.apps.simulation_roster_service import SimulationRosterService
from kadoka_quest.data.field_data import FieldDataLoader
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.ui.runtime_input_adapter import RuntimeInputAdapter


# {
#   責務: [SimulationRosterTests: simulation・所有個体台帳・testsの状態と振る舞いを担当する]
#   フィールド: [
#     temporary: temporary
#     root: 基準ディレクトリ
#     repository: データ取得先
#     roster: 所有個体台帳
#   ]
# }
class SimulationRosterTests(unittest.TestCase):
    # {
    #   責務: [setUp: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = GameRepository()
        self.roster = SimulationRosterService(
            self.root / "simulation",
            self.repository,
            self.root / "imports" / "simulation",
        )

    # {
    #   責務: [tearDown: 検証用fixtureと一時的な変更を後始末する]
    #   処理: [1: 検証用fixtureと一時的な変更を後始末する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def tearDown(self) -> None:
        self.temporary.cleanup()

    # {
    #   責務: [test_simulation_monsters_do_not_enter_owned_store: 検証: simulation monsters do not enter owned store]
    #   処理: [1: 検証: simulation monsters do not enter owned store]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_simulation_monsters_do_not_enter_owned_store(self) -> None:
        owned = MonsterStore(self.root / "owned", self.repository)
        record = self.roster.create("slime", level=12)

        self.assertEqual(record.level, 12)
        self.assertIsNone(owned.get(record.monster_id))
        self.assertIsNotNone(self.roster.store.get(record.monster_id))

    # {
    #   責務: [test_external_simulation_import_stays_in_simulation_roster: 検証: external simulation import stays in simulation roster]
    #   処理: [1: 検証: external simulation import stays in simulation roster]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_external_simulation_import_stays_in_simulation_roster(self) -> None:
        external = MonsterStore(self.root / "imports" / "simulation", self.repository)
        source = external.create("ghost", level=7, monster_id="external_ghost")
        owned = MonsterStore(self.root / "owned", self.repository)

        added, skipped = self.roster.import_external()

        self.assertEqual((added, skipped), (1, 0))
        self.assertEqual(self.roster.store.get(source.monster_id).level, 7)
        self.assertIsNone(owned.get(source.monster_id))

    # {
    #   責務: [test_battle_request_is_one_shot_and_limited_to_four: 検証: battle request is one shot and limited to four]
    #   処理: [1: 検証: battle request is one shot and limited to four]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_battle_request_is_one_shot_and_limited_to_four(self) -> None:
        records = [self.roster.create("slime", monster_id=f"sim_{index}") for index in range(5)]
        self.roster.request_battle(record.monster_id for record in records)

        loaded = self.roster.consume_battle_request()

        self.assertEqual([record.monster_id for record in loaded], [f"sim_{index}" for index in range(4)])
        self.assertEqual(self.roster.consume_battle_request(), [])


# {
#   責務: [SimulationFacilityIntegrationTests: simulation・facility・integration・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class SimulationFacilityIntegrationTests(unittest.TestCase):
    # {
    #   責務: [test_starting_town_contains_separate_simulation_hall_events: 検証: starting town contains separate simulation hall events]
    #   処理: [1: 検証: starting town contains separate simulation hall events]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_starting_town_contains_separate_simulation_hall_events(self) -> None:
        repository = GameRepository()
        map_data = FieldDataLoader(repository).load_map("starting_town")["map"]
        events = {event["id"]: event for event in map_data["events"]}

        self.assertEqual(events["simulation_hall_terminal"]["type"], "open_simulation_manager")
        self.assertNotEqual(events["simulation_hall_terminal"]["x"], events["to_starting_ranch"]["x"])

    # {
    #   責務: [test_field_event_routes_simulation_terminal: 検証: field event routes simulation terminal]
    #   処理: [1: 検証: field event routes simulation terminal]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_field_event_routes_simulation_terminal(self) -> None:
        effect = FieldEventApplication().resolve_interaction(
            None,
            {"id": "terminal", "type": "open_simulation_manager", "text": "open"},
            "front",
        )
        self.assertEqual(effect["kind"], "open_simulation_manager")

    # {
    #   責務: [test_f6_no_longer_starts_simulation_directly: 検証: f6 no longer starts simulation directly]
    #   処理: [1: 検証: f6 no longer starts simulation directly]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_f6_no_longer_starts_simulation_directly(self) -> None:
        adapter = RuntimeInputAdapter({})
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F6, unicode="", repeat=False)
        self.assertEqual(adapter.translate(event, "field", 0), [])

    # {
    #   責務: [test_process_service_uses_simulation_flag_when_frozen: 検証: process service uses simulation flag when frozen]
    #   処理: [1: 検証: process service uses simulation flag when frozen]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_process_service_uses_simulation_flag_when_frozen(self) -> None:
        launcher = mock.Mock(return_value=mock.Mock(poll=mock.Mock(return_value=None)))
        service = ManagerProcessService(
            Path("simulation_manager.py"),
            python_executable="KadokaQuest.exe",
            launcher=launcher,
            frozen=True,
            frozen_argument="--simulation-manager",
        )
        self.assertEqual(service.open(), "started")
        launcher.assert_called_once_with(
            ["KadokaQuest.exe", "--simulation-manager"],
            cwd=Path("."),
        )

    # {
    #   責務: [test_closed_facility_request_starts_non_learning_battle: 検証: closed facility request starts non learning battle]
    #   処理: [1: 検証: closed facility request starts non learning battle]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_closed_facility_request_starts_non_learning_battle(self) -> None:
        process = mock.Mock()
        process.consume_closed.return_value = True
        opponent = mock.Mock()
        roster = mock.Mock()
        roster.consume_battle_request.return_value = [opponent]
        battle = mock.Mock(learning_enabled=False)
        session = SimpleNamespace(
            repository=mock.Mock(),
            rng=random.Random(1),
            battle_session=mock.Mock(),
            mode="field",
            status="",
            party=lambda: [mock.Mock()],
        )
        with mock.patch("kadoka_quest.apps.simulation_facility_hooks._components", return_value=(process, roster)), mock.patch(
            "kadoka_quest.apps.simulation_facility_hooks.BattleEngine", return_value=battle
        ):
            refresh_simulation_if_closed(session)

        session.battle_session.begin.assert_called_once()
        self.assertTrue(session.battle_session.begin.call_args.kwargs["simulation"])
        self.assertEqual(session.mode, "battle")

    # {
    #   責務: [test_install_hooks_does_not_replace_battle_command_handler: 検証: install hooks does not replace battle command handler]
    #   処理: [1: 検証: install hooks does not replace battle command handler]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_install_hooks_does_not_replace_battle_command_handler(self) -> None:
        # {
        #   責務: [FakeGame: fake・ゲームの状態と振る舞いを担当する]
        #   フィールド: []
        # }
        class FakeGame:
            # {
            #   責務: [handle_battle_command: 戦闘・コマンドを入力を処理する]
            #   処理: [1: 戦闘・コマンドを入力を処理する]
            #   引数: [
            #     self: 処理対象インスタンス
            #     command: コマンド（str）
            #   ]
            #   戻り値: [result: コマンド（str）]
            # }
            def handle_battle_command(self, command: str) -> str:
                return command

        original = FakeGame.handle_battle_command
        install_simulation_facility_hooks(FakeGame)

        self.assertIs(FakeGame.handle_battle_command, original)
        self.assertIs(FakeGame.open_simulation_manager, open_simulation_manager)
        self.assertIs(FakeGame.refresh_simulation_if_closed, refresh_simulation_if_closed)


if __name__ == "__main__":
    unittest.main()
