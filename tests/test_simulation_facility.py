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


class SimulationRosterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = GameRepository()
        self.roster = SimulationRosterService(
            self.root / "simulation",
            self.repository,
            self.root / "imports" / "simulation",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_simulation_monsters_do_not_enter_owned_store(self) -> None:
        owned = MonsterStore(self.root / "owned", self.repository)
        record = self.roster.create("slime", level=12)

        self.assertEqual(record.level, 12)
        self.assertIsNone(owned.get(record.monster_id))
        self.assertIsNotNone(self.roster.store.get(record.monster_id))

    def test_external_simulation_import_stays_in_simulation_roster(self) -> None:
        external = MonsterStore(self.root / "imports" / "simulation", self.repository)
        source = external.create("ghost", level=7, monster_id="external_ghost")
        owned = MonsterStore(self.root / "owned", self.repository)

        added, skipped = self.roster.import_external()

        self.assertEqual((added, skipped), (1, 0))
        self.assertEqual(self.roster.store.get(source.monster_id).level, 7)
        self.assertIsNone(owned.get(source.monster_id))

    def test_battle_request_is_one_shot_and_limited_to_four(self) -> None:
        records = [self.roster.create("slime", monster_id=f"sim_{index}") for index in range(5)]
        self.roster.request_battle(record.monster_id for record in records)

        loaded = self.roster.consume_battle_request()

        self.assertEqual([record.monster_id for record in loaded], [f"sim_{index}" for index in range(4)])
        self.assertEqual(self.roster.consume_battle_request(), [])


class SimulationFacilityIntegrationTests(unittest.TestCase):
    def test_starting_town_contains_separate_simulation_hall_events(self) -> None:
        repository = GameRepository()
        map_data = FieldDataLoader(repository).load_map("starting_town")["map"]
        events = {event["id"]: event for event in map_data["events"]}

        self.assertEqual(events["simulation_hall_terminal"]["type"], "open_simulation_manager")
        self.assertNotEqual(events["simulation_hall_terminal"]["x"], events["to_starting_ranch"]["x"])

    def test_field_event_routes_simulation_terminal(self) -> None:
        effect = FieldEventApplication().resolve_interaction(
            None,
            {"id": "terminal", "type": "open_simulation_manager", "text": "open"},
            "front",
        )
        self.assertEqual(effect["kind"], "open_simulation_manager")

    def test_f6_no_longer_starts_simulation_directly(self) -> None:
        adapter = RuntimeInputAdapter({})
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F6, unicode="", repeat=False)
        self.assertEqual(adapter.translate(event, "field", 0), [])

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

    def test_install_hooks_does_not_replace_battle_command_handler(self) -> None:
        class FakeGame:
            def handle_battle_command(self, command: str) -> str:
                return command

        original = FakeGame.handle_battle_command
        install_simulation_facility_hooks(FakeGame)

        self.assertIs(FakeGame.handle_battle_command, original)
        self.assertIs(FakeGame.open_simulation_manager, open_simulation_manager)
        self.assertIs(FakeGame.refresh_simulation_if_closed, refresh_simulation_if_closed)


if __name__ == "__main__":
    unittest.main()
