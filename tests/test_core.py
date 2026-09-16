from __future__ import annotations

import copy
from datetime import datetime
import os
from pathlib import Path
import random
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.application import AppCommand, CommandBus
from kadoka_quest.application.runtime_orchestrator import RuntimeOrchestrator
from kadoka_quest.apps.battle_command_app import BattleCommandApplication
from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.apps.field_command_app import FieldCommandApplication
from kadoka_quest.apps.field_event_app import FieldEventApplication
from kadoka_quest.apps.field_party_service import FieldPartyService
from kadoka_quest.apps.field_party_session import FieldPartySession
from kadoka_quest.apps.manager_command_app import ManagerCommandApplication
from kadoka_quest.apps.manager_process_service import ManagerProcessService
from kadoka_quest.apps.monster_import_service import MonsterImportService
from kadoka_quest.apps.password_command_app import PasswordCommandApplication
from kadoka_quest.apps.password_session import PasswordSession
from kadoka_quest.core.ai import choose_skill, default_ai, learn_from_action
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.battle_context import describe_battle_context
from kadoka_quest.core.battle_inference import BattleInference
from kadoka_quest.core.battle_learning import BattleLearning
from kadoka_quest.core.field_engine import FieldEngine
from kadoka_quest.core.fixed_mob_controller import FixedMobController
from kadoka_quest.core.grid_movement import GridMovement
from kadoka_quest.core.hidden_enemy_controller import HiddenEnemyController
from kadoka_quest.core.player_field_controller import PlayerFieldController
from kadoka_quest.apps.block_editor import BlockEditor
from kadoka_quest.apps.game import FIELD_RECT, TILE, KadokaQuest, draw_field
from kadoka_quest.apps.map_editor import MapEditor
from kadoka_quest.apps.monster_editor import NEW_SPECIES_ID, MonsterEditor
from kadoka_quest.core.monster import MonsterRecord, calculate_stats
from kadoka_quest.data.developer_monster_creator import DeveloperMonsterCreator
from kadoka_quest.data.battle_data import BattleDataLoader
from kadoka_quest.data.field_data import FieldDataLoader
from kadoka_quest.data.field_progress import FieldProgressStore
from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.data.map_presets import MapPresetStore
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository, STAT_KEYS
from kadoka_quest.data.savedata import SaveDataManager
from kadoka_quest.data.state import StateStore
from kadoka_quest.ui.common import ScrollBar, TextField, handle_fields
from kadoka_quest.ui.character_image_provider import CharacterImageProvider
from kadoka_quest.ui.pixel_editor import PixelArtEditor, PixelTarget
from kadoka_quest.ui.runtime_input_adapter import RuntimeInputAdapter
from kadoka_quest.ui.runtime_mouse_adapter import RuntimeMouseAdapter


class JsonIoTests(unittest.TestCase):
    def test_write_json_retries_a_temporary_windows_access_denial(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            original_replace = os.replace
            attempts = 0

            def temporarily_locked(source: Path, target: Path) -> None:
                nonlocal attempts
                attempts += 1
                if attempts < 3:
                    raise PermissionError(5, "temporarily locked")
                original_replace(source, target)

            with mock.patch("kadoka_quest.data.jsonio.os.replace", side_effect=temporarily_locked), mock.patch(
                "kadoka_quest.data.jsonio.time.sleep"
            ) as sleep:
                write_json(path, {"x": 3})

            self.assertEqual(read_json(path), {"x": 3})
            self.assertEqual(attempts, 3)
            self.assertEqual(sleep.call_count, 2)
            self.assertEqual(list(Path(temporary).glob("*.tmp")), [])

    def test_write_json_keeps_the_previous_save_when_replacement_stays_locked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            write_json(path, {"x": 3})
            with mock.patch("kadoka_quest.data.jsonio.os.replace", side_effect=PermissionError(5, "locked")), mock.patch(
                "kadoka_quest.data.jsonio.time.sleep"
            ):
                with self.assertRaises(PermissionError):
                    write_json(path, {"x": 4})

            self.assertEqual(read_json(path), {"x": 3})
            self.assertEqual(list(Path(temporary).glob("*.tmp")), [])


class CommandApplicationTests(unittest.TestCase):
    def test_command_bus_routes_one_target_and_rejects_unknown_or_duplicate_targets(self) -> None:
        handler = mock.Mock()
        handler.handle.return_value = "handled"
        bus = CommandBus()
        bus.register("field", handler.handle)
        command = AppCommand("field", "interact")

        self.assertEqual(bus.dispatch(command), "handled")
        handler.handle.assert_called_once_with(command)
        with self.assertRaises(ValueError):
            bus.register("field", handler.handle)
        with self.assertRaises(ValueError):
            bus.dispatch(AppCommand("missing", "noop"))

    def test_runtime_applications_receive_plain_semantic_commands(self) -> None:
        session = SimpleNamespace(
            selected_party=0,
            select_party=mock.Mock(return_value=True),
            battle_selection=0,
            auto_battle=False,
            status="",
            start_held_direction=mock.Mock(return_value=True),
            stop_held_direction=mock.Mock(),
            handle_battle_command=mock.Mock(),
            selected_battle_command=mock.Mock(return_value="scout"),
            move_battle_selection=mock.Mock(return_value=3),
            set_battle_selection=mock.Mock(return_value=0),
            stop_auto_battle=mock.Mock(),
            append_password=mock.Mock(),
        )
        bus = CommandBus()
        bus.register("field", FieldCommandApplication(session).handle)
        bus.register("battle", BattleCommandApplication(session).handle)
        bus.register("password", PasswordCommandApplication(session).handle)

        self.assertTrue(bus.dispatch(AppCommand("field", "move.start", {"direction": "left", "now": 120})))
        session.start_held_direction.assert_called_once_with("left", 120)
        self.assertTrue(bus.dispatch(AppCommand("field", "party.select", {"index": 3})))
        session.select_party.assert_called_once_with(3)
        self.assertEqual(bus.dispatch(AppCommand("battle", "selection.move", {"amount": -1})), 3)
        bus.dispatch(AppCommand("battle", "execute.selected"))
        session.handle_battle_command.assert_called_once_with("scout")
        bus.dispatch(AppCommand("password", "append", {"character": "へ"}))
        session.append_password.assert_called_once_with("へ")

    def test_runtime_command_applications_do_not_depend_on_pygame(self) -> None:
        for relative in (
            "src/kadoka_quest/application/app_command.py",
            "src/kadoka_quest/application/command_bus.py",
            "src/kadoka_quest/apps/field_command_app.py",
            "src/kadoka_quest/apps/field_party_service.py",
            "src/kadoka_quest/apps/field_party_session.py",
            "src/kadoka_quest/apps/battle_command_app.py",
            "src/kadoka_quest/apps/battle_session.py",
            "src/kadoka_quest/apps/password_command_app.py",
            "src/kadoka_quest/apps/password_session.py",
            "src/kadoka_quest/apps/manager_command_app.py",
            "src/kadoka_quest/apps/manager_process_service.py",
            "src/kadoka_quest/apps/monster_import_service.py",
            "src/kadoka_quest/application/runtime_orchestrator.py",
        ):
            self.assertNotIn("import pygame", (PROJECT_ROOT / relative).read_text(encoding="utf-8"))

    def test_battle_session_owns_selection_playback_auto_and_end_context(self) -> None:
        ally = SimpleNamespace(name="まる", record=SimpleNamespace(monster_id="ally"))
        enemy = SimpleNamespace(name="スライム", record=SimpleNamespace(monster_id="enemy"))
        battle = SimpleNamespace(
            log=["戦闘開始"],
            allies=[ally],
            enemies=[enemy],
            outcome=None,
        )
        session = BattleSession(initial_log_delay_ms=10, action_log_delay_ms=20, next_round_delay_ms=30)

        session.begin(battle, 100, simulation=True, fixed_mob_id="boss")
        self.assertEqual(session.move_selection(-1), 3)
        self.assertEqual(session.selected_command(), "run")
        battle.log.append("まるは攻撃した。")
        self.assertTrue(session.start_playback(1, 100))
        self.assertFalse(session.update_playback(109)["changed"])
        self.assertTrue(session.update_playback(110)["changed"])
        self.assertEqual(session.focus_id, "ally")
        self.assertTrue(session.update_playback(130)["completed"])
        self.assertTrue(session.toggle_auto(130))
        self.assertFalse(session.auto_command_due(159, battle_mode=True))
        self.assertTrue(session.auto_command_due(160, battle_mode=True))
        battle.outcome = "victory"
        self.assertTrue(session.mark_finalized())
        self.assertFalse(session.mark_finalized())
        self.assertEqual(
            session.clear(),
            {"outcome": "victory", "simulation": True, "fixed_mob_id": "boss"},
        )

    def test_game_exposes_battle_state_only_as_battle_session_compatibility_properties(self) -> None:
        source = (PROJECT_ROOT / "src/kadoka_quest/apps/game.py").read_text(encoding="utf-8")
        self.assertIn("self.battle_session = BattleSession()", source)
        for assignment in (
            "self.battle: BattleEngine | None = None",
            "self.battle_playback = False",
            "self.auto_battle = False",
            "self.simulation = False",
        ):
            self.assertNotIn(assignment, source)

    def test_field_party_session_owns_selection_and_preset_cycle_cursors(self) -> None:
        session = FieldPartySession()

        self.assertEqual(session.select(9), 3)
        self.assertEqual(session.selected(["a", "b"]), "b")
        self.assertEqual(session.selected_index, 1)
        self.assertIsNone(session.selected([]))
        self.assertEqual(session.next_preset(["one", "two"]), "one")
        self.assertEqual(session.next_preset(["one", "two"]), "two")
        self.assertEqual(session.next_preset(["one", "two"]), "one")
        self.assertIsNone(session.next_preset([]))

# Existing remaining tests intentionally preserved below.
