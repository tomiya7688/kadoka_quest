from __future__ import annotations

import copy
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
from kadoka_quest.apps.manager_command_app import ManagerCommandApplication
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
from kadoka_quest.core.monster import calculate_stats
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
                write_json(path, {"map_id": "greenwood", "x": 7})

            self.assertEqual(read_json(path), {"map_id": "greenwood", "x": 7})
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
            "src/kadoka_quest/apps/battle_command_app.py",
            "src/kadoka_quest/apps/battle_session.py",
            "src/kadoka_quest/apps/password_command_app.py",
            "src/kadoka_quest/apps/password_session.py",
            "src/kadoka_quest/apps/manager_command_app.py",
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

    def test_password_session_owns_input_limit_validation_and_reset(self) -> None:
        session = PasswordSession("へいわ", "へいわな")

        session.open()
        self.assertTrue(session.active)
        self.assertTrue(session.message)
        self.assertFalse(session.append("外"))
        for character in "へいわな":
            session.append(character)
        self.assertEqual(session.input_text, "へいわ")
        self.assertTrue(session.backspace())
        self.assertFalse(session.submit())
        self.assertTrue(session.message)
        session.backspace()
        session.backspace()
        for character in "へいわ":
            session.append(character)
        self.assertTrue(session.submit())
        self.assertFalse(session.active)
        session.open()
        session.append("へ")
        session.cancel()
        self.assertEqual((session.input_text, session.message, session.active), ("", "", False))

    def test_game_exposes_password_state_as_password_session_compatibility_properties(self) -> None:
        source = (PROJECT_ROOT / "src/kadoka_quest/apps/game.py").read_text(encoding="utf-8")
        self.assertIn("self.password_session = PasswordSession(PASSWORD, KANA_KEYS)", source)
        self.assertNotIn('self.password_input = ""', source)
        self.assertNotIn('self.password_message = ""', source)

    def test_runtime_orchestrator_owns_modes_and_routes_cross_app_effects(self) -> None:
        session = SimpleNamespace(
            status="",
            mode="field",
            change_map=mock.Mock(),
            register_church=mock.Mock(),
            gain_field_item=mock.Mock(),
            despawn_fixed_mob_by_id=mock.Mock(),
            open_password_input=mock.Mock(),
            open_manager=mock.Mock(),
            refresh_manager_if_closed=mock.Mock(),
        )
        runtime = RuntimeOrchestrator(session)

        self.assertEqual(runtime.transition_to("password"), "password")
        self.assertEqual(runtime.previous_mode, "field")
        with self.assertRaises(ValueError):
            runtime.transition_to("unknown")
        runtime.apply_field_effect(
            {
                "kind": "transition",
                "status": "move",
                "target": {"map_id": "greenwood", "x": 4, "y": 5},
            }
        )
        session.change_map.assert_called_once_with("greenwood", 4, 5, "move")
        runtime.apply_field_effect({"kind": "open_password", "status": "spring"})
        session.open_password_input.assert_called_once_with()
        runtime.apply_field_effect({"kind": "open_manager", "status": "ranch"})
        session.open_manager.assert_called_once_with()
        runtime.dispatch("manager", "refresh")
        session.refresh_manager_if_closed.assert_called_once_with()

    def test_field_effect_payload_never_contains_runtime_objects(self) -> None:
        npc = {
            "id": "guide",
            "species_id": "ghost",
            "name": "guide",
            "interaction": "battle",
            "level": 3,
            "_movement": object(),
        }
        effect = FieldEventApplication().resolve_interaction(npc, None, "front", "hello")

        self.assertNotIn("npc", effect)
        self.assertEqual(effect["npc_id"], "guide")
        self.assertEqual(
            set(type(value) for value in effect.values()),
            {str, dict},
        )


class DataFormatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = GameRepository(PROJECT_ROOT / "data")

    def test_required_sample_species_and_full_level_tables_exist(self) -> None:
        required = {"slime", "ball_slime", "metal_slime", "ghost", "maru", "kadoka", "dice_slime"}
        self.assertTrue(required.issubset(set(self.repository.list_species_ids())))
        for species_id in required:
            bundle = self.repository.get_species(species_id)
            self.assertEqual(set(bundle.stats["levels"]), {str(level) for level in range(1, 101)})
            self.assertEqual(set(bundle.stats["levels"]["100"]), set(STAT_KEYS))
            self.assertEqual(len(bundle.plus["stages"]), 10)

    def test_hero_uses_square_pixel_art_on_exact_64_pixel_canvases(self) -> None:
        definition = self.repository.get_species("hero").definition
        paths = [definition["portrait_path"], *definition["field_sprites"].values()]
        self.assertTrue(all("square" in str(path) for path in paths))
        for relative in paths:
            image = pygame.image.load(str(PROJECT_ROOT / "assets" / relative))
            self.assertEqual(image.get_size(), (64, 64))

    def test_blocks_split_all_three_rules(self) -> None:
        for block in self.repository.list_blocks():
            self.assertIsInstance(block["player_walkable"], bool)
            self.assertIsInstance(block["enemy_spawnable"], bool)
            self.assertIsInstance(block["enemy_walkable"], bool)
            self.assertIn(block["appearance"]["type"], {"color", "path"})
    def test_map_references_known_blocks_and_species(self) -> None:
        block_ids = {item["id"] for item in self.repository.list_blocks()}
        species_ids = set(self.repository.list_species_ids())
        self.assertEqual(set(self.repository.list_maps()), {"starting_town", "starting_ranch", "greenwood", "fresh_forest", "rokuta_village", "ghost_home"})
        for map_id in self.repository.list_maps():
            map_data = self.repository.get_map(map_id)
            self.assertEqual(len(map_data["tiles"]), map_data["height"])
            self.assertTrue(all(len(row) == map_data["width"] for row in map_data["tiles"]))
            self.assertTrue(all(tile in block_ids for row in map_data["tiles"] for tile in row))
            self.assertTrue(all(item["species_id"] in species_ids for item in map_data["spawns"]))
            self.assertNotIn("ball_slime", {item["species_id"] for item in map_data["spawns"]})
            transitions = [item for item in map_data["events"] if item.get("type") == "transition"]
            self.assertTrue(all(item.get("activation") in {"step", "interact"} for item in transitions))

    def test_equipment_owns_species_restrictions(self) -> None:
        species_ids = set(self.repository.list_species_ids())
        for species_id in species_ids:
            self.assertNotIn("equipment_categories", self.repository.get_species(species_id).definition)
        for equipment in self.repository.get_equipment().values():
            self.assertIn("allowed_species_ids", equipment)
            self.assertTrue(set(equipment["allowed_species_ids"]).issubset(species_ids))

    def test_ghost_home_entrance_is_only_in_fresh_forest_side_path(self) -> None:
        greenwood = self.repository.get_map("greenwood")
        fresh = self.repository.get_map("fresh_forest")
        self.assertFalse(any("ghost_home" in str(item) for item in greenwood["events"]))
        rock = next(item for item in fresh["events"] if item["id"] == "ghost_home_rock")
        self.assertEqual(rock["activation"], "interact")
        self.assertEqual(rock["target"]["map_id"], "ghost_home")
        self.assertTrue(any(item["id"] == "ghost_home_note" for item in fresh["events"]))
        self.assertTrue(any(item["type"] == "church" for item in self.repository.get_map("rokuta_village")["events"]))

    def test_starting_town_precedes_forest_and_contains_ranch_management(self) -> None:
        town = self.repository.get_map("starting_town")
        ranch = self.repository.get_map("starting_ranch")
        town_exit = next(item for item in town["events"] if item["id"] == "to_starting_forest")
        ranch_door = next(item for item in town["events"] if item["id"] == "to_starting_ranch")
        manager = next(item for item in ranch["events"] if item["id"] == "ranch_manager")
        self.assertEqual(town_exit["target"]["map_id"], "greenwood")
        self.assertEqual(ranch_door["target"]["map_id"], "starting_ranch")
        self.assertEqual(manager["type"], "open_manager")
        self.assertTrue(manager["blocking"])

    def test_main_roads_are_three_tiles_wide_and_signs_block(self) -> None:
        checks = (("starting_town", 14, 20), ("greenwood", 6, 12), ("fresh_forest", 15, 12), ("rokuta_village", 12, 20))
        for map_id, center_y, x in checks:
            data = self.repository.get_map(map_id)
            self.assertTrue(all(data["tiles"][y][x] == "path" for y in range(center_y - 1, center_y + 2)))
        for map_id in ("starting_town", "greenwood", "fresh_forest", "rokuta_village"):
            signs = [event for event in self.repository.get_map(map_id)["events"] if "sign" in event["id"]]
            self.assertTrue(signs)
            self.assertTrue(all(event.get("blocking") for event in signs))

    def test_ghost_home_password_is_at_the_water_spring_and_art_exists(self) -> None:
        home = self.repository.get_map("ghost_home")
        self.assertEqual(home["block_color_overrides"]["safe"], "#101B3A")
        spring = next(item for item in home["events"] if item["id"] == "ghost_spring")
        self.assertEqual(spring["type"], "password_spring")
        self.assertEqual(home["tiles"][spring["y"]][spring["x"]], "water")
        for species_id in ("hero", "slime", "ball_slime", "metal_slime", "ghost", "maru", "kadoka", "dice_slime"):
            definition = self.repository.get_species(species_id).definition
            portrait = PROJECT_ROOT / "assets" / definition["portrait_path"]
            self.assertTrue(portrait.is_file())
            self.assertEqual(pygame.image.load(str(portrait)).get_size(), (64, 64))
            self.assertTrue((PROJECT_ROOT / "assets" / definition["field_sprite_path"]).is_file())
            self.assertEqual(set(definition["field_sprites"]), {"front", "right", "left", "back"})
            for path in definition["field_sprites"].values():
                image_path = PROJECT_ROOT / "assets" / path
                self.assertTrue(image_path.is_file())
                image = pygame.image.load(str(image_path))
                self.assertEqual(image.get_size(), (64, 64))
        for species_id in ("maru", "kadoka"):
            definition = self.repository.get_species(species_id).definition
            for direction in ("left", "right"):
                image = pygame.image.load(str(PROJECT_ROOT / "assets" / definition["field_sprites"][direction]))
                bounds = image.get_bounding_rect(min_alpha=128)
                self.assertGreaterEqual(bounds.width / max(1, bounds.height), 0.75)
                self.assertGreater(sum(image.get_at((x, y)).a >= 128 for y in range(image.get_height()) for x in range(image.get_width())), 1000)

    def test_ghost_home_fixed_mobs_have_editable_dialogue_decks_and_ai(self) -> None:
        fixed_mobs = self.repository.get_map("ghost_home")["fixed_mobs"]
        self.assertEqual({item["species_id"] for item in fixed_mobs}, {"maru", "kadoka"})
        for item in fixed_mobs:
            self.assertIn(item["ai"], {"idle", "random", "chase"})
            self.assertGreaterEqual(item["move_interval_ms"], 100)
            self.assertTrue(0 <= item["move_chance"] <= 100)
            self.assertTrue(3 <= len(item["dialogue"]) <= 5)
            self.assertIn(item["interaction"], {"talk", "battle"})
            self.assertIn("despawn_after_interaction", item)
            self.assertIn("respawn_on_map_enter", item)

    def test_maru_left_is_a_transparent_mirror_without_a_white_backdrop(self) -> None:
        definition = self.repository.get_species("maru").definition
        front = pygame.image.load(str(PROJECT_ROOT / "assets" / definition["field_sprites"]["front"]))
        right = pygame.image.load(str(PROJECT_ROOT / "assets" / definition["field_sprites"]["right"]))
        left = pygame.image.load(str(PROJECT_ROOT / "assets" / definition["field_sprites"]["left"]))
        self.assertEqual(left.get_size(), (64, 64))
        self.assertTrue(all(left.get_at(point).a == 0 for point in ((0, 0), (63, 0), (0, 63), (63, 63))))
        self.assertEqual(
            [left.get_at((x, y)).a for y in range(64) for x in range(64)],
            [front.get_at((x, y)).a for y in range(64) for x in range(64)],
        )
        mirrored = pygame.transform.flip(right, True, False)
        self.assertEqual(pygame.image.tobytes(left, "RGBA"), pygame.image.tobytes(mirrored, "RGBA"))


class UiWidgetTests(unittest.TestCase):
    def test_character_image_provider_crops_scales_and_caches_pixel_art(self) -> None:
        pygame.display.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = pygame.Surface((4, 4), pygame.SRCALPHA)
            source.set_at((1, 1), pygame.Color("#FF0000"))
            source.set_at((2, 1), pygame.Color("#00FF00"))
            source.set_at((1, 2), pygame.Color("#0000FF"))
            source.set_at((2, 2), pygame.Color("#FFFFFF"))
            pygame.image.save(source, str(root / "sprite.png"))
            repository = SimpleNamespace(
                get_species=lambda _species_id: SimpleNamespace(
                    definition={
                        "portrait_path": "sprite.png",
                        "field_sprites": {"front": "sprite.png"},
                    }
                )
            )
            provider = CharacterImageProvider(repository, root)

            field = provider.get("test", "field_front", (8, 8))
            self.assertEqual(field.get_size(), (8, 8))
            self.assertEqual(field.get_at((0, 0)), pygame.Color("#FF0000"))
            self.assertEqual(field.get_at((7, 7)), pygame.Color("#FFFFFF"))
            self.assertIs(provider.get("test", "field_front", (8, 8)), field)
            self.assertEqual(provider.get("test", "portrait", (8, 8)).get_size(), (8, 8))
            provider.clear()
            self.assertEqual(provider.cache, {})

    def test_game_delegates_character_loading_and_cache_to_image_provider(self) -> None:
        source = (PROJECT_ROOT / "src/kadoka_quest/apps/game.py").read_text(encoding="utf-8")
        self.assertIn("self.character_images = CharacterImageProvider(self.repository, ASSET_ROOT)", source)
        self.assertIn("return self.character_images.get(species_id, kind, size)", source)
        self.assertNotIn("self.image_cache:", source)

    def test_shared_pixel_palette_adds_selects_and_safely_removes_colors(self) -> None:
        editor = PixelArtEditor(PROJECT_ROOT / "assets")
        original_count = len(editor.palette)

        added = editor.add_palette_color("#1234ab")
        self.assertEqual(added, (18, 52, 171, 255))
        self.assertEqual(editor.brush, added)
        self.assertEqual(len(editor.palette), original_count + 1)
        self.assertEqual(editor.color_to_hex(added), "#1234AB")

        self.assertEqual(editor.add_palette_color("1234AB"), added)
        self.assertEqual(len(editor.palette), original_count + 1)
        self.assertEqual(len(editor.palette_rects((10, 20), 4, (30, 25))), len(editor.palette))
        with self.assertRaises(ValueError):
            editor.add_palette_color("blue")

        self.assertTrue(editor.remove_palette_color())
        self.assertNotIn(added, editor.palette)
        transparent = editor.palette[0]
        editor.brush = transparent
        self.assertFalse(editor.remove_palette_color())
        self.assertIn(transparent, editor.palette)

    def test_monster_and_block_editors_use_the_same_editable_palette_api(self) -> None:
        for owner in (MonsterEditor(), BlockEditor()):
            with self.subTest(editor=type(owner).__name__):
                owner.palette_color_field.value = "#654321"
                owner.add_palette_color()
                self.assertEqual(owner.visuals.brush, (101, 67, 33, 255))
                self.assertIn(owner.visuals.brush, owner.visuals.palette)
                owner.remove_palette_color()
                self.assertNotIn((101, 67, 33, 255), owner.visuals.palette)

    def test_shared_pixel_fill_stops_at_outlines_and_is_undoable(self) -> None:
        editor = PixelArtEditor(PROJECT_ROOT / "assets")
        editor.set_targets((PixelTarget("front", "正面", "unused.png", 8),))
        image = pygame.Surface((8, 8), pygame.SRCALPHA)
        image.fill((255, 255, 255, 255))
        pygame.draw.rect(image, (0, 0, 0, 255), pygame.Rect(1, 1, 6, 6), 1)
        editor.images["front"] = image
        editor.brush = (255, 0, 0, 255)
        editor.set_tool_mode("fill")

        changed = editor.fill((35, 35), pygame.Rect(0, 0, 80, 80))

        self.assertEqual(changed, 16)
        self.assertEqual(tuple(editor.images["front"].get_at((3, 3))), (255, 0, 0, 255))
        self.assertEqual(tuple(editor.images["front"].get_at((1, 1))), (0, 0, 0, 255))
        self.assertEqual(tuple(editor.images["front"].get_at((0, 0))), (255, 255, 255, 255))
        self.assertTrue(editor.undo())
        self.assertEqual(tuple(editor.images["front"].get_at((3, 3))), (255, 255, 255, 255))

    def test_shared_pixel_editor_merges_near_colors_with_configurable_tolerance(self) -> None:
        editor = PixelArtEditor(PROJECT_ROOT / "assets")
        editor.set_targets((PixelTarget("front", "正面", "unused.png", 4),))
        image = pygame.Surface((4, 4), pygame.SRCALPHA)
        image.fill((40, 80, 120, 255))
        image.set_at((3, 3), (44, 82, 117, 255))
        image.set_at((0, 0), (0, 0, 0, 0))
        editor.images["front"] = image

        self.assertEqual(editor.merge_similar_colors(5), 0)
        self.assertEqual(editor.merge_similar_colors(6), 1)
        self.assertEqual(tuple(editor.images["front"].get_at((3, 3))), (40, 80, 120, 255))
        self.assertEqual(tuple(editor.images["front"].get_at((0, 0))), (0, 0, 0, 0))
        self.assertTrue(editor.undo())
        self.assertEqual(tuple(editor.images["front"].get_at((3, 3))), (44, 82, 117, 255))
        with self.assertRaises(ValueError):
            editor.parse_tolerance("256")

    def test_shared_pixel_editor_imports_with_nearest_downscale_and_color_reduction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = pygame.Surface((128, 32), pygame.SRCALPHA)
            source.fill((10, 20, 30, 255), pygame.Rect(0, 0, 64, 32))
            source.fill((15, 20, 30, 255), pygame.Rect(64, 0, 64, 32))
            source_path = root / "wide.png"
            pygame.image.save(source, str(source_path))
            editor = PixelArtEditor(root / "assets")
            editor.set_targets((PixelTarget("front", "正面", "unused.png"),))
            editor.images["front"] = pygame.Surface((64, 64), pygame.SRCALPHA)

            changed = editor.import_image(str(source_path), 5)

            self.assertGreater(changed, 0)
            self.assertEqual(editor.images["front"].get_size(), (64, 64))
            self.assertEqual(editor.images["front"].get_at((0, 0)).a, 0)
            self.assertEqual(tuple(editor.images["front"].get_at((0, 24))), (10, 20, 30, 255))
            self.assertEqual(tuple(editor.images["front"].get_at((63, 39))), (10, 20, 30, 255))
            self.assertTrue(editor.undo())
            self.assertEqual(editor.images["front"].get_at((0, 24)).a, 0)

    def test_monster_editor_lists_new_first_and_creates_complete_species(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data_root = root / "data"
            assets_root = root / "assets"
            write_json(data_root / "skills" / "skills.json", {
                "schema_version": 1,
                "skills": [
                    {"id": "attack", "display_name": "こうげき", "kind": "physical", "power": 1.0, "mp_cost": 0},
                    {"id": "defend", "display_name": "ぼうぎょ", "kind": "defend", "power": 0, "mp_cost": 0},
                ],
            })
            editor = MonsterEditor(GameRepository(data_root), assets_root)

            self.assertEqual(editor.species_ids, [NEW_SPECIES_ID])
            self.assertTrue(editor.creating_new)
            editor.id_field.value = "test_beast"
            editor.name_field.value = "テストビースト"
            editor.color_field.value = "#34A853"
            editor.stat_fields["attack"].value = "27"
            editor.save()

            self.assertEqual(editor.species_ids[0], NEW_SPECIES_ID)
            self.assertEqual(editor.species_id, "test_beast")
            bundle = editor.repository.get_species("test_beast")
            self.assertEqual(bundle.definition["display_name"], "テストビースト")
            self.assertEqual(bundle.stats["levels"]["1"]["attack"], 27)
            self.assertEqual(set(bundle.stats["levels"]), {str(level) for level in range(1, 101)})
            self.assertEqual(len(bundle.plus["stages"]), 10)
            self.assertEqual(bundle.skills["learnset"][0]["skill_id"], "attack")
            image_paths = [bundle.definition["portrait_path"], *bundle.definition["field_sprites"].values()]
            self.assertEqual(len(image_paths), 5)
            for relative_path in image_paths:
                image_path = assets_root / relative_path
                self.assertTrue(image_path.is_file())
                self.assertEqual(pygame.image.load(str(image_path)).get_size(), (64, 64))

            editor.select_species(0)
            editor.id_field.value = "test_beast"
            editor.save()
            self.assertIn("already exists", editor.status)

    def test_shared_pixel_editor_accepts_different_targets_and_zooms(self) -> None:
        editor = PixelArtEditor(PROJECT_ROOT / "assets")
        editor.set_targets((PixelTarget("front", "正面", "characters/slime/field_front.png"),))
        editor.images["front"] = pygame.Surface((64, 64), pygame.SRCALPHA)
        self.assertEqual(editor.zoom_percent, 100)
        self.assertTrue(editor.zoom_in())
        self.assertEqual(editor.zoom_percent, 150)
        self.assertTrue(editor.zoom_out())
        self.assertEqual(editor.zoom_percent, 100)
        editor.load_block("tiles/blocks/test.png", (30, 60, 90))
        self.assertEqual(set(editor.targets), {"appearance"})
        self.assertEqual(editor.logical_size, 64)

    def test_shared_pixel_editor_ctrl_z_history_restores_a_whole_stroke(self) -> None:
        editor = PixelArtEditor(PROJECT_ROOT / "assets")
        editor.set_targets((PixelTarget("front", "正面", "characters/slime/field_front.png"),))
        editor.images["front"] = pygame.Surface((64, 64), pygame.SRCALPHA)
        canvas = pygame.Rect(0, 0, 640, 640)

        self.assertTrue(editor.begin_stroke())
        self.assertTrue(editor.paint((15, 15), canvas))
        self.assertTrue(editor.paint((25, 25), canvas))
        editor.end_stroke()
        self.assertGreater(editor.images["front"].get_at((1, 1)).a, 0)
        self.assertGreater(editor.images["front"].get_at((2, 2)).a, 0)

        self.assertTrue(editor.undo())
        self.assertEqual(editor.images["front"].get_at((1, 1)).a, 0)
        self.assertEqual(editor.images["front"].get_at((2, 2)).a, 0)
        self.assertFalse(editor.undo())

    def test_shared_pixel_editor_pan_mode_moves_and_clamps_zoomed_view(self) -> None:
        editor = PixelArtEditor(PROJECT_ROOT / "assets")
        editor.set_targets((PixelTarget("front", "正面", "characters/slime/field_front.png"),))
        editor.images["front"] = pygame.Surface((64, 64), pygame.SRCALPHA)
        canvas = pygame.Rect(0, 0, 384, 384)
        editor.zoom_in()
        self.assertTrue(editor.set_tool_mode("pan"))

        original = editor.image_rect(canvas)
        self.assertTrue(editor.begin_pan((192, 192), canvas))
        self.assertTrue(editor.pan_to((500, 500), canvas))
        editor.end_pan()
        moved = editor.image_rect(canvas)
        self.assertGreater(moved.x, original.x)
        self.assertEqual(moved.x, 0)
        self.assertEqual(moved.y, 0)

        editor.reset_zoom()
        self.assertEqual(editor.pan_offset, pygame.Vector2())
        self.assertEqual(editor.image_rect(canvas), canvas)

    def test_text_field_click_keeps_only_one_field_active(self) -> None:
        first = TextField(pygame.Rect(0, 0, 100, 30))
        second = TextField(pygame.Rect(120, 0, 100, 30))
        handle_fields([first, second], pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10)))
        self.assertTrue(first.active)
        self.assertFalse(second.active)
        handle_fields([first, second], pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(130, 10)))
        self.assertFalse(first.active)
        self.assertTrue(second.active)

    def test_scrollbars_support_vertical_and_horizontal_overflow(self) -> None:
        vertical = ScrollBar(pygame.Rect(0, 0, 12, 200), "vertical", total=100, page=10)
        vertical.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(6, 180)))
        vertical.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(6, 180)))
        self.assertGreater(vertical.value, 0)

        horizontal = ScrollBar(pygame.Rect(0, 0, 200, 12), "horizontal", total=100, page=10)
        horizontal.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(180, 6)))
        horizontal.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(180, 6)))
        self.assertGreater(horizontal.value, 0)

    def test_map_editor_selects_maps_from_list_and_edits_both_transition_conditions(self) -> None:
        editor = MapEditor()
        self.assertEqual(set(editor.map_names), set(editor.repository.list_maps()))
        fresh_index = editor.map_ids.index("fresh_forest")
        self.assertTrue(editor.select_map(fresh_index))
        existing_conditions = {item.get("activation", "step") for item in editor.transitions}
        self.assertEqual(existing_conditions, {"step", "interact"})
        original_tile = editor.map_data["tiles"][10][10]
        self.assertTrue(editor.add_transition_at(10, 10))
        self.assertEqual(editor.map_data["tiles"][10][10], original_tile)
        self.assertFalse(editor.add_transition_at(10, 10))
        editor.set_transition_target("ghost_home")
        editor.set_transition_activation("interact")
        editor.transition_id.value = "test_interact_move"
        editor.target_x.value = "2"
        editor.target_y.value = "9"
        self.assertTrue(editor.apply_transition())
        self.assertEqual(editor.current_transition["activation"], "interact")
        self.assertEqual(editor.current_transition["target"]["map_id"], "ghost_home")
        self.assertFalse(editor.select_map(editor.map_ids.index("greenwood")))

    def test_map_editor_places_and_configures_fixed_mobs_without_replacing_tiles(self) -> None:
        editor = MapEditor()
        self.assertTrue(editor.select_map(editor.map_ids.index("greenwood")))
        editor.selected_species = editor.species_ids.index("slime")
        original_tile = editor.map_data["tiles"][10][10]
        editor.select_fixed_mob_brush()
        self.assertTrue(editor.add_fixed_mob_at(10, 10))
        self.assertEqual(editor.map_data["tiles"][10][10], original_tile)
        self.assertEqual(editor.current_fixed_mob["ai"], "idle")
        editor.cycle_fixed_mob_ai()
        editor.cycle_fixed_mob_interaction()
        editor.fixed_mob_dialogue.value = "こんにちは | また会いましたね | 森は広いですよ"
        editor.fixed_mob_interval.value = "750"
        editor.fixed_mob_chance.value = "35"
        self.assertTrue(editor.apply_fixed_mob())
        self.assertEqual(editor.current_fixed_mob["ai"], "random")
        self.assertEqual(editor.current_fixed_mob["interaction"], "battle")
        self.assertEqual(editor.current_fixed_mob["move_interval_ms"], 750)
        self.assertEqual(editor.current_fixed_mob["move_chance"], 35)
        self.assertEqual(len(editor.current_fixed_mob["dialogue"]), 3)

    def test_repository_creates_a_mod_friendly_map_from_selected_block(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(root / "blocks" / "grass.json", {
                "schema_version": 1, "id": "grass", "display_name": "草地",
                "player_walkable": True, "enemy_spawnable": True, "enemy_walkable": True,
                "appearance": {"type": "color", "value": "#00AA00"},
            })
            repository = GameRepository(root)
            created = repository.create_map("test_field", "テスト平原", 12, 8, "grass")
            self.assertEqual(repository.list_maps(), ["test_field"])
            self.assertEqual(created["start"], {"x": 6, "y": 4})
            self.assertEqual(len(created["tiles"]), 8)
            self.assertTrue(all(row == ["grass"] * 12 for row in created["tiles"]))
            self.assertEqual(created["spawns"], [])
            self.assertEqual(created["fixed_mobs"], [])
            self.assertEqual(created["events"], [])
            with self.assertRaises(ValueError):
                repository.create_map("test_field", "重複", 12, 8, "grass")

    def test_map_editor_round_trips_maps_and_presets_with_the_same_document_format(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(root / "blocks" / "grass.json", {
                "schema_version": 1, "id": "grass", "display_name": "草地",
                "player_walkable": True, "enemy_spawnable": True, "enemy_walkable": True,
                "appearance": {"type": "color", "value": "#00AA00"},
            })
            repository = GameRepository(root)
            source = repository.create_map("source_map", "元マップ", 6, 5, "grass")
            source["events"] = [{"id": "notice", "x": 2, "y": 2, "type": "message", "text": "テスト"}]
            repository.save_map(source)
            repository.create_map("target_map", "適用先", 5, 5, "grass")
            presets = MapPresetStore(root)
            editor = MapEditor(repository, presets)

            editor.preset_id.value = "forest_base"
            editor.preset_name.value = "森の基本形"
            self.assertTrue(editor.save_current_as_preset())
            preset = presets.get("forest_base")
            self.assertEqual(preset["id"], "forest_base")
            self.assertEqual(preset["events"], source["events"])

            self.assertTrue(editor.select_map(editor.map_ids.index("target_map")))
            editor.select_preset(editor.preset_ids.index("forest_base"))
            self.assertTrue(editor.apply_selected_preset())
            self.assertEqual(editor.map_data["id"], "target_map")
            self.assertEqual(editor.map_data["display_name"], "適用先")
            self.assertEqual(editor.map_data["events"], source["events"])
            self.assertTrue(editor.dirty)
            editor.save()

            editor.preset_map_id.value = "created_from_preset"
            editor.preset_map_name.value = "プリセット生成マップ"
            self.assertTrue(editor.create_map_from_selected_preset())
            created = repository.get_map("created_from_preset")
            self.assertEqual(created["display_name"], "プリセット生成マップ")
            self.assertEqual(created["tiles"], source["tiles"])
            self.assertEqual(created["events"], source["events"])
            self.assertEqual(set(created), set(preset))

            with self.assertRaises(ValueError):
                presets.save_from_map("forest_base", "重複", source)


class FolderAndPartyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = GameRepository(PROJECT_ROOT / "data")
        self.monsters = MonsterStore(self.root / "owned", self.repository)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_instances_do_not_duplicate_species_stats(self) -> None:
        record = self.monsters.create("ball_slime", "ぽん", 12)
        self.assertEqual(set(record.monster), {"schema_version", "id", "species_id", "name", "level", "experience", "plus_choices", "equipment_id", "source"})
        self.assertNotIn("attack", record.monster)
        self.assertEqual(calculate_stats(self.repository, record), self.repository.stats_at("ball_slime", 12))

    def test_equipment_uses_multipliers_and_one_slot(self) -> None:
        record = self.monsters.create("slime", level=30)
        base = calculate_stats(self.repository, record)
        record.monster["equipment_id"] = "ken"
        equipped = calculate_stats(self.repository, record)
        self.assertEqual(equipped["speed"], round(base["speed"] * 0.8))
        self.assertEqual(equipped["attack"], base["attack"])

    def test_species_not_listed_by_equipment_cannot_use_it(self) -> None:
        record = self.monsters.create("ghost", level=30)
        base = calculate_stats(self.repository, record)
        record.monster["equipment_id"] = "ken"
        self.assertEqual(calculate_stats(self.repository, record), base)
        enemy = self.monsters.create("slime", level=1)
        battle = BattleEngine(self.repository, [record], [enemy], rng=random.Random(1))
        self.assertIsNone(battle.allies[0].equipment)

    def test_ai_reset_keeps_individual_progression(self) -> None:
        record = self.monsters.create("ghost", "経験豊富なおばけ", 77)
        record.monster["plus_choices"] = ["ghost_plus_1_magic"]
        record.ai["action_preferences"] = {"possess": 0.9}
        record.ai["context_preferences"] = {"self:critical": {"possess": 0.5}}
        self.monsters.save(record)
        reset = self.monsters.reset_ai(record.monster_id)
        self.assertEqual(reset.level, 77)
        self.assertEqual(reset.plus_choices, ["ghost_plus_1_magic"])
        self.assertEqual(reset.ai["action_preferences"], {})
        self.assertEqual(reset.ai["context_preferences"], {})

    def test_rescan_acquires_missing_folder_and_skips_duplicate(self) -> None:
        external = self.root / "external" / "friend_monster"
        write_json(external / "monster.json", {
            "schema_version": 1,
            "id": "friend_001",
            "species_id": "slime",
            "name": "友達スライム",
            "level": 9,
            "experience": 0,
            "plus_choices": [],
            "equipment_id": None,
            "source": "import",
        })
        write_json(external / "ai.json", {"schema_version": 1, "profile": "normal", "tactic": "balanced", "weights": {}, "kind_preferences": {}, "action_preferences": {}, "battles": 2, "actions": 8})
        self.assertEqual(self.monsters.acquire_from_scan(self.root / "external"), (1, 0))
        self.assertEqual(self.monsters.acquire_from_scan(self.root / "external"), (0, 1))
        self.assertEqual(self.monsters.get("friend_001").name, "友達スライム")

    def test_party_missing_id_becomes_empty_and_presets_are_unlimited_files(self) -> None:
        first = self.monsters.create("slime")
        parties = PartyStore(self.root / "parties")
        for index in range(12):
            parties.save(f"編成 {index}", [first.monster_id, "missing", None, None])
        self.assertEqual(len(parties.list_presets()), 12)
        loaded = parties.load(parties.list_presets()[0], self.monsters)
        self.assertEqual(loaded[0].monster_id, first.monster_id)
        self.assertIsNone(loaded[1])


class DeveloperMonsterCreatorTests(unittest.TestCase):
    def test_creator_previews_and_writes_existing_individual_format_to_all_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = GameRepository(PROJECT_ROOT / "data")
            output_roots = {target: root / target for target in DeveloperMonsterCreator.TARGETS}
            creator = DeveloperMonsterCreator(repository, output_roots)

            preview = creator.preview("ghost", 42)
            self.assertEqual(preview["stats"], repository.stats_at("ghost", 42))
            self.assertEqual(preview["skill_ids"], repository.skill_ids_at("ghost", 42))

            for target in DeveloperMonsterCreator.TARGETS:
                with self.subTest(target=target):
                    monster_id = f"developer_{target}"
                    record, folder = creator.create("ghost", 42, "開発おばけ", target, monster_id)
                    self.assertEqual(record.monster_id, monster_id)
                    self.assertEqual(record.level, 42)
                    self.assertEqual(record.monster["source"], f"developer_{target}")
                    self.assertEqual(read_json(folder / "monster.json"), record.monster)
                    self.assertEqual(read_json(folder / "ai.json"), record.ai)

            with self.assertRaises(ValueError):
                creator.create("ghost", 101, "範囲外", "owned")
            with self.assertRaises(ValueError):
                creator.create("ghost", 1, "危険ID", "owned", "../outside")
            with self.assertRaises(FileExistsError):
                creator.create("ghost", 42, "重複", "owned", "developer_owned")


class SaveDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_named_save_contains_monsters_ai_items_and_can_be_copied_and_loaded(self) -> None:
        manager = SaveDataManager(self.root / "savedata")
        profile = manager.create("冒険その1")
        states = StateStore(profile / "state.json")
        state = states.load()
        state["inventory"]["orange"] = 9
        states.save(state)
        monsters = MonsterStore(profile / "monsters", GameRepository(PROJECT_ROOT / "data"))
        record = monsters.create("slime", "セーブスライム", 7)
        record.ai["battles"] = 12
        monsters.save(record)
        copy_path = manager.copy_profile("冒険その1", "予備データ")
        manager.set_active("冒険その1")
        self.assertEqual(manager.active_name(), "冒険その1")
        self.assertNotIn("inventory", read_json(profile / "state.json"))
        self.assertEqual(read_json(profile / "items" / "items.json")["items"]["orange"], 9)
        self.assertEqual(read_json(profile / "monsters" / record.monster_id / "ai.json")["battles"], 12)
        self.assertTrue((copy_path / "monsters" / record.monster_id / "monster.json").is_file())


class ContextLearningTests(unittest.TestCase):
    def test_context_tags_describe_health_resources_numbers_and_target_state(self) -> None:
        self.assertEqual(
            describe_battle_context(0.2, 0.8, 0.1, 1, 3, 0.25, 10, 20),
            ("self:critical", "allies:critical", "mp:low", "numbers:outnumbered", "target:near_defeat", "threat:stronger"),
        )
        self.assertEqual(
            describe_battle_context(1.0, 0.0, 1.0, 3, 1, 1.0, 20, 10),
            ("self:healthy", "allies:stable", "mp:ready", "numbers:advantage", "target:healthy", "threat:weaker"),
        )

    def test_context_preferences_change_action_choice_without_state_combinations(self) -> None:
        ai = default_ai()
        skills = [
            {"id": "first", "kind": "physical", "mp_cost": 0},
            {"id": "second", "kind": "physical", "mp_cost": 0},
        ]
        ai["context_preferences"] = {
            "self:critical": {"first": 0.6, "second": -0.6},
            "self:healthy": {"first": -0.6, "second": 0.6},
        }
        rng = mock.Mock()
        rng.uniform.return_value = 0.0

        critical = choose_skill(ai, skills, 0.2, 0.0, 1.0, rng, ("self:critical",))
        healthy = choose_skill(ai, skills, 1.0, 0.0, 1.0, rng, ("self:healthy",))

        self.assertEqual(critical["id"], "first")
        self.assertEqual(healthy["id"], "second")

    def test_context_learning_is_sparse_clamped_and_counts_each_tag_once(self) -> None:
        ai = default_ai()
        tags = ("self:hurt", "numbers:even", "self:hurt")
        for _ in range(200):
            learn_from_action(ai, "attack", 1.0, tags)

        self.assertEqual(ai["actions"], 200)
        self.assertEqual(ai["context_preferences"]["self:hurt"]["attack"], 0.6)
        self.assertEqual(ai["context_preferences"]["numbers:even"]["attack"], 0.6)
        self.assertEqual(ai["context_actions"]["self:hurt"], 200)
        self.assertEqual(set(ai["context_preferences"]), {"self:hurt", "numbers:even"})


class BattleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repository = GameRepository(PROJECT_ROOT / "data")
        self.monsters = MonsterStore(Path(self.temporary.name) / "owned", self.repository)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_fight_command_uses_ai_for_every_member(self) -> None:
        hero = self.monsters.create("hero", level=10)
        ball = self.monsters.create("ball_slime", level=10)
        enemy = self.monsters.create("slime", level=8)
        engine = BattleEngine(self.repository, [hero, ball], [enemy], random.Random(3), learning_enabled=True)
        engine.run_round()
        self.assertGreaterEqual(len(engine.allies[0].action_history) + len(engine.allies[1].action_history), 1)
        self.assertTrue(any("ダメージ" in line or "防御" in line or "回復" in line for line in engine.log))
        learned_contexts = [member.record.ai.get("context_preferences", {}) for member in engine.allies]
        self.assertTrue(any(contexts for contexts in learned_contexts))
        self.assertTrue(all(len(contexts) <= 6 for contexts in learned_contexts))

    def test_engine_delegates_data_inference_and_learning_to_injected_responsibilities(self) -> None:
        ally = self.monsters.create("hero", level=10)
        enemy = self.monsters.create("slime", level=8)
        loader = BattleDataLoader(self.repository)
        inference = mock.create_autospec(BattleInference, instance=True)
        inference.choose.side_effect = lambda _ai, skills, *_args: next(
            (skill for skill in skills if skill.get("kind") == "physical"),
            skills[0] if skills else None,
        )
        learning = mock.create_autospec(BattleLearning, instance=True)

        with mock.patch.object(loader, "build_combatant", wraps=loader.build_combatant) as build:
            engine = BattleEngine(
                self.repository,
                [ally],
                [enemy],
                random.Random(21),
                learning_enabled=True,
                data_loader=loader,
                inference=inference,
                learning=learning,
            )
        self.assertEqual(build.call_count, 2)
        engine.run_round()
        self.assertTrue(inference.choose.called)
        self.assertTrue(learning.learn.called)

        learning.reset_mock()
        simulation = BattleEngine(
            self.repository,
            [ally],
            [enemy],
            random.Random(22),
            learning_enabled=False,
            data_loader=loader,
            inference=inference,
            learning=learning,
        )
        simulation.run_round()
        learning.learn.assert_not_called()

    def test_battle_modules_keep_screen_data_inference_and_learning_boundaries(self) -> None:
        engine_source = (PROJECT_ROOT / "src/kadoka_quest/core/battle.py").read_text(encoding="utf-8")
        renderer_source = (PROJECT_ROOT / "src/kadoka_quest/ui/battle_renderer.py").read_text(encoding="utf-8")
        self.assertNotIn("choose_skill", engine_source)
        self.assertNotIn("learn_from_action", engine_source)
        self.assertNotIn(".get_species(", engine_source)
        self.assertNotIn("run_round", renderer_source)
        self.assertNotIn(".learn(", renderer_source)

    def test_simulation_battle_never_updates_ai(self) -> None:
        ally = self.monsters.create("metal_slime", level=20)
        enemy = self.monsters.create("ghost", level=20)
        before_ally = copy.deepcopy(ally.ai)
        before_enemy = copy.deepcopy(enemy.ai)
        engine = BattleEngine(self.repository, [ally], [enemy], random.Random(4), learning_enabled=False)
        for _ in range(5):
            if engine.outcome:
                break
            engine.run_round()
        engine.mark_battle_complete()
        self.assertEqual(ally.ai, before_ally)
        self.assertEqual(enemy.ai, before_enemy)

    def test_guard_reduces_only_physical_damage(self) -> None:
        ally = self.monsters.create("ghost", level=100)
        enemy = self.monsters.create("hero", level=100)
        engine = BattleEngine(self.repository, [ally], [enemy], random.Random(9), learning_enabled=False)
        actor = engine.allies[0]
        target = engine.enemies[0]

        attack = engine.skill_catalog["attack"]
        engine.rng.seed(99)
        physical_damage = engine._attack(actor, target, attack)
        target.hp = target.stats["hp"]
        target.guard = 0.5
        engine.rng.seed(99)
        guarded_physical_damage = engine._attack(actor, target, attack)
        self.assertLess(guarded_physical_damage, physical_damage)

        weaken = engine.skill_catalog["weaken"]
        target.hp = target.stats["hp"]
        target.guard = 1.0
        engine.rng.seed(99)
        magic_damage = engine._attack(actor, target, weaken)
        target.hp = target.stats["hp"]
        target.guard = 0.5
        engine.rng.seed(99)
        guarded_magic_damage = engine._attack(actor, target, weaken)
        self.assertEqual(guarded_magic_damage, magic_damage)

    def test_normal_attack_critical_is_one_in_sixteen_and_ignores_defense(self) -> None:
        ally = self.monsters.create("ghost", level=100)
        enemy = self.monsters.create("hero", level=100)
        engine = BattleEngine(self.repository, [ally], [enemy], random.Random(12), learning_enabled=False)
        actor = engine.allies[0]
        target = engine.enemies[0]
        attack = engine.skill_catalog["attack"]
        engine.rng = mock.Mock()
        engine.rng.uniform.return_value = 1.0
        target.stats["hp"] = 100_000

        engine.rng.random.return_value = 1 / 16 - 0.000001
        target.stats["defense"] = 1
        target.hp = target.stats["hp"]
        low_defense_damage = engine._attack(actor, target, attack)
        low_defense_dealt = round(low_defense_damage * target.stats["hp"])

        target.stats["defense"] = 100_000
        target.hp = target.stats["hp"]
        high_defense_damage = engine._attack(actor, target, attack)
        high_defense_dealt = round(high_defense_damage * target.stats["hp"])
        self.assertEqual(low_defense_dealt, high_defense_dealt)
        self.assertEqual(high_defense_dealt, actor.stats["attack"])
        self.assertTrue(any("会心" in line for line in engine.log))

        engine.log.clear()
        engine.rng.random.return_value = 1 / 16
        target.hp = target.stats["hp"]
        noncritical_damage = engine._attack(actor, target, attack)
        self.assertEqual(round(noncritical_damage * target.stats["hp"]), 1)
        self.assertFalse(any("会心" in line for line in engine.log))

    def test_physical_evade_wording_is_specific_to_species_and_skill(self) -> None:
        attack_record = self.monsters.create("hero", level=30)

        def evade_log(species_id: str, source: str) -> str:
            target_record = self.monsters.create(species_id, level=30)
            engine = BattleEngine(
                self.repository, [attack_record], [target_record], random.Random(14), learning_enabled=False,
            )
            target = engine.enemies[0]
            target.evade_physical = True
            target.evade_physical_source = source
            self.assertEqual(engine._attack(engine.allies[0], target, engine.skill_catalog["attack"]), 0.0)
            return engine.log[-1]

        for species_id in ("maru", "kadoka"):
            with self.subTest(species_id=species_id):
                self.assertIn("すり抜けた", evade_log(species_id, "vanish"))

        fluid_log = evade_log("metal_slime", "fluid_defense")
        self.assertIn("流体防御", fluid_log)
        self.assertIn("受け流した", fluid_log)
        self.assertNotIn("すり抜けた", fluid_log)

        generic_log = evade_log("ghost", "vanish")
        self.assertIn("かわした", generic_log)
        self.assertNotIn("すり抜けた", generic_log)

    def test_bundled_external_folder_is_simulation_ready(self) -> None:
        imported = self.monsters.discover_external(PROJECT_ROOT / "examples" / "simulation_party")
        self.assertEqual([record.monster_id for record in imported], ["guest_dice_slime_001"])
        ally = self.monsters.create("ball_slime", level=12)
        engine = BattleEngine(self.repository, [ally], imported, random.Random(8), learning_enabled=False)
        engine.run_round()
        self.assertGreaterEqual(engine.round_number, 1)


class FieldEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.map_data = {
            "id": "field_engine_test",
            "display_name": "field engine test",
            "width": 4,
            "height": 3,
            "tiles": [
                ["floor", "floor", "floor", "floor"],
                ["floor", "floor", "floor", "wall"],
                ["floor", "floor", "floor", "floor"],
            ],
            "events": [
                {"id": "sign", "x": 2, "y": 1, "type": "message", "blocking": True},
                {
                    "id": "exit",
                    "x": 1,
                    "y": 2,
                    "type": "transition",
                    "activation": "step",
                    "target": {"map_id": "next", "x": 1, "y": 1},
                },
            ],
        }
        self.blocks = {
            "floor": {"player_walkable": True, "enemy_walkable": True},
            "wall": {"display_name": "壁", "player_walkable": False, "enemy_walkable": False},
        }
        self.engine = FieldEngine(self.map_data, self.blocks)

    def test_core_module_has_no_pygame_or_repository_dependency(self) -> None:
        source = (PROJECT_ROOT / "src" / "kadoka_quest" / "core" / "field_engine.py").read_text(encoding="utf-8")
        self.assertNotIn("import pygame", source)
        self.assertNotIn("kadoka_quest.data", source)

    def test_move_result_is_plain_data_and_does_not_mutate_position(self) -> None:
        result = self.engine.resolve_player_move(0, 1, 1, 0, "front", [], [])
        self.assertEqual(result, {
            "kind": "moved",
            "reason": "walkable",
            "x": 1,
            "y": 1,
            "direction": "right",
            "block_id": "floor",
        })

    def test_move_result_distinguishes_characters_events_and_tiles(self) -> None:
        visible = [{"id": "villager", "x": 1, "y": 1}]
        hidden = [{"id": "enemy", "x": 1, "y": 1}]
        self.assertEqual(
            self.engine.resolve_player_move(0, 1, 1, 0, "front", visible, hidden)["reason"],
            "hidden_character",
        )
        self.assertEqual(
            self.engine.resolve_player_move(0, 1, 1, 0, "front", visible, [])["reason"],
            "visible_character",
        )
        self.assertEqual(
            self.engine.resolve_player_move(1, 1, 1, 0, "front", [], [])["reason"],
            "blocking_event",
        )
        self.assertEqual(
            self.engine.resolve_player_move(2, 1, 1, 0, "front", [], [])["reason"],
            "blocked_tile",
        )

    def test_event_direction_and_line_of_sight_queries_are_portable(self) -> None:
        self.assertEqual(self.engine.front_position(1, 1, "back"), (1, 0))
        self.assertEqual(self.engine.nearby_event(1, 1)["id"], "sign")
        self.assertEqual(self.engine.step_transition_at(1, 2)["id"], "exit")
        self.assertTrue(self.engine.has_clear_axis_path((0, 0), (3, 0), "enemy_walkable"))
        self.assertFalse(self.engine.has_clear_axis_path((3, 0), (3, 2), "enemy_walkable"))


class FieldActorControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.map_data = {
            "id": "actor_test",
            "width": 4,
            "height": 3,
            "tiles": [["floor"] * 4 for _ in range(3)],
            "fixed_mobs": [
                {
                    "id": "guide",
                    "species_id": "ghost",
                    "x": 1,
                    "y": 1,
                    "ai": "idle",
                    "dialogue": ["one", "two"],
                }
            ],
            "spawns": [
                {"species_id": "ball_slime", "weight": 99},
                {"species_id": "slime", "weight": 1},
            ],
        }
        self.blocks = {
            "floor": {
                "player_walkable": True,
                "enemy_spawnable": True,
                "enemy_walkable": True,
            }
        }
        self.field = FieldEngine(self.map_data, self.blocks)

    def test_fixed_mob_controller_owns_runtime_state_and_dialogue_deck(self) -> None:
        controller = FixedMobController(self.field, random.Random(3))
        controller.reset(
            self.map_data,
            self.blocks,
            set(),
            (1, 1),
            100,
            lambda species_id: species_id.upper(),
        )

        self.assertEqual(len(controller.npcs), 1)
        npc = controller.npcs[0]
        self.assertNotEqual((npc["x"], npc["y"]), (1, 1))
        self.assertEqual(npc["name"], "GHOST")
        self.assertNotEqual(controller.next_dialogue(npc), controller.next_dialogue(npc))

    def test_hidden_enemy_controller_excludes_starter_and_owns_timers(self) -> None:
        controller = HiddenEnemyController(self.field, random.Random(4), 320, 950, 8)
        controller.set_world(self.map_data, self.blocks)
        controller.reset((0, 0), {}, 100)

        self.assertTrue(controller.monsters)
        self.assertEqual({item["spawn"]["species_id"] for item in controller.monsters}, {"slime"})
        self.assertTrue(all(item["next_move_tick"] == 1050 for item in controller.monsters))

    def test_actor_controllers_are_portable_and_runtime_delegates_to_them(self) -> None:
        for relative in (
            "src/kadoka_quest/core/fixed_mob_controller.py",
            "src/kadoka_quest/core/hidden_enemy_controller.py",
        ):
            source = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("import pygame", source)
            self.assertNotIn("kadoka_quest.data", source)
        runtime = (PROJECT_ROOT / "src/kadoka_quest/apps/game.py").read_text(encoding="utf-8")
        self.assertIn("self.fixed_mobs.update(", runtime)
        self.assertIn("self.hidden_enemies.update(", runtime)


class FieldSessionSeparationTests(unittest.TestCase):
    def test_player_controller_owns_grid_position_facing_and_repeat_state(self) -> None:
        map_data = {
            "width": 3,
            "height": 1,
            "tiles": [["floor", "floor", "floor"]],
            "events": [],
        }
        field = FieldEngine(
            map_data,
            {"floor": {"player_walkable": True, "enemy_walkable": True}},
        )
        player = PlayerFieldController(0, 0, 120, 180, 90)

        result = player.attempt_move(field, 1, 0, [], [], 1000)
        self.assertEqual(result["kind"], "moved")
        self.assertEqual((player.x, player.y, player.direction), (1, 0, "right"))
        self.assertEqual(player.begin_hold("right", 1100), (1, 0))
        self.assertIsNone(player.repeated_vector(1279))
        self.assertEqual(player.repeated_vector(1280), (1, 0))
        self.assertEqual(player.next_move_tick, 1370)

    def test_event_application_emits_one_plain_effect_for_cross_app_work(self) -> None:
        events = FieldEventApplication()
        npc = {
            "id": "boss",
            "species_id": "ghost",
            "name": "boss ghost",
            "direction": "left",
            "interaction": "battle",
            "level": 12,
        }

        battle = events.resolve_interaction(npc, None, "right", "fight")
        self.assertEqual(battle["kind"], "npc_battle")
        self.assertEqual(battle["spawn"]["min_level"], 12)
        self.assertEqual(npc["direction"], "left")
        church = events.resolve_interaction(
            None,
            {"type": "church", "text": "registered", "revive": {"map_id": "town", "x": 2, "y": 3}},
            "front",
        )
        self.assertEqual(church["kind"], "register_church")
        self.assertEqual(church["revive"]["map_id"], "town")

    def test_field_data_and_progress_own_loading_clamping_and_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = GameRepository(PROJECT_ROOT / "data")
            loader = FieldDataLoader(repository)
            loaded = loader.load_map("greenwood", -10, 999)
            self.assertEqual(loaded["x"], 0)
            self.assertEqual(loaded["y"], loaded["map"]["height"] - 1)

            states = StateStore(Path(temporary) / "state.json")
            progress = FieldProgressStore(states)
            state = {}
            progress.save_position(state, "greenwood", 4, 5)
            progress.register_church(state, {"map_id": "town", "x": 1, "y": 2})
            progress.add_item(state, "orange")
            self.assertEqual(states.load()["player"], {"x": 4, "y": 5})
            self.assertEqual(states.load()["revive_point"]["map_id"], "town")
            self.assertEqual(states.load()["inventory"]["orange"], 1)

    def test_runtime_delegates_all_four_field_session_responsibilities(self) -> None:
        runtime = (PROJECT_ROOT / "src/kadoka_quest/apps/game.py").read_text(encoding="utf-8")
        for call in (
            "self.player_field.attempt_move(",
            "self.field_events.resolve_interaction(",
            "self.field_progress.save_position(",
            "self.field_data.load_map(",
        ):
            self.assertIn(call, runtime)
        for relative in (
            "src/kadoka_quest/core/player_field_controller.py",
            "src/kadoka_quest/apps/field_event_app.py",
        ):
            self.assertNotIn("import pygame", (PROJECT_ROOT / relative).read_text(encoding="utf-8"))


class GridMovementTests(unittest.TestCase):
    def test_grid_movement_interpolates_and_can_retarget_without_a_visual_jump(self) -> None:
        movement = GridMovement(2, 3, duration_ms=120)
        movement.move_to(3, 3, 1000)
        self.assertEqual(movement.position(1000), (2.0, 3.0))
        self.assertEqual(movement.position(1060), (2.5, 3.0))

        movement.move_to(4, 3, 1060)
        self.assertEqual(movement.position(1060), (2.5, 3.0))
        halfway_x, halfway_y = movement.position(1120)
        self.assertAlmostEqual(halfway_x, 3.25)
        self.assertEqual(halfway_y, 3.0)
        self.assertEqual(movement.position(1180), (4.0, 3.0))
        self.assertFalse(movement.moving)

    def test_snap_is_used_for_non_walking_position_changes(self) -> None:
        movement = GridMovement(1, 1)
        movement.move_to(2, 1, 100)
        movement.snap(8, 9)
        self.assertEqual(movement.position(101), (8.0, 9.0))
        self.assertFalse(movement.moving)


class FieldFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.repository = GameRepository(PROJECT_ROOT / "data")
        self.monsters = MonsterStore(root / "monsters", self.repository)
        self.states = StateStore(root / "state.json")
        self.parties = PartyStore(root / "parties")
        self.game = KadokaQuest(self.repository, self.monsters, self.states, self.parties, random.Random(11))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_new_game_starts_in_starting_town(self) -> None:
        self.assertEqual(self.game.map_data["id"], "starting_town")
        self.assertEqual((self.game.player_x, self.game.player_y), (18, 14))

    def test_field_events_do_not_cover_the_underlying_block_color(self) -> None:
        self.game.map_data = {
            "id": "event_render_test",
            "display_name": "event render test",
            "width": 3,
            "height": 3,
            "tiles": [["grass"] * 3 for _ in range(3)],
            "events": [
                {"id": "step", "x": 2, "y": 0, "type": "transition", "activation": "step"},
                {"id": "inspect", "x": 2, "y": 1, "type": "message", "activation": "interact"},
            ],
        }
        self.game.player_x = 0
        self.game.player_y = 0
        self.game.home_npcs = []
        pygame.font.init()
        screen = pygame.Surface((1200, 720))

        draw_field(screen, self.game)

        grass = pygame.Color("#4E9F3D")
        for x, y in ((2, 0), (2, 1)):
            pixel = screen.get_at((FIELD_RECT.x + x * TILE + TILE // 2, FIELD_RECT.y + y * TILE + TILE // 2))
            self.assertEqual(pixel, grass)

    def test_hidden_monsters_are_not_ball_slimes_and_collision_starts_battle(self) -> None:
        self.game.change_map("greenwood", 6, 6)
        self.assertTrue(self.game.hidden_monsters)
        self.assertNotIn("ball_slime", {item["spawn"]["species_id"] for item in self.game.hidden_monsters})
        hidden = self.game.hidden_monsters[0]
        self.game.hidden_monsters = [hidden]
        self.game.player_x, self.game.player_y = 6, 6
        self.game.player_direction = "right"
        hidden["x"], hidden["y"] = 7, 6
        self.assertTrue(self.game.check_hidden_collision())
        self.assertEqual(self.game.mode, "battle")

    def test_field_mobs_use_timers_and_chasers_move_faster_than_wanderers(self) -> None:
        self.game.change_map("greenwood", 6, 6)
        spawn = {"species_id": "slime", "min_level": 1, "max_level": 1}
        chaser = {"x": 9, "y": 6, "spawn": spawn, "next_move_tick": 1000}
        self.game.hidden_monsters = [chaser]
        self.assertFalse(self.game.update_field_mobs(999))
        self.assertTrue(self.game.update_field_mobs(1000))
        self.assertTrue(chaser["sees_player"])
        self.assertEqual(chaser["next_move_tick"], 1320)
        wanderer = {"x": 9, "y": 8, "spawn": spawn, "next_move_tick": 2000}
        self.game.hidden_monsters = [wanderer]
        self.game.update_field_mobs(2000)
        self.assertFalse(wanderer["sees_player"])
        self.assertEqual(wanderer["next_move_tick"], 2950)

    def test_holding_a_move_key_repeats_after_a_short_delay(self) -> None:
        self.game.change_map("greenwood", 9, 6)
        self.game.hidden_monsters = []
        self.assertTrue(self.game.start_held_move(pygame.K_RIGHT, 1000))
        self.assertEqual((self.game.player_x, self.game.player_y), (10, 6))
        self.assertFalse(self.game.update_held_move(1179))
        self.assertTrue(self.game.update_held_move(1180))
        self.assertEqual((self.game.player_x, self.game.player_y), (11, 6))
        self.game.stop_held_move(pygame.K_RIGHT)
        self.assertFalse(self.game.update_held_move(1270))

    def test_player_logic_stays_on_grid_while_display_position_moves_smoothly(self) -> None:
        self.game.change_map("greenwood", 9, 6)
        self.game.hidden_monsters = []

        self.game.move(1, 0, now=1000)

        self.assertEqual((self.game.player_x, self.game.player_y), (10, 6))
        self.assertEqual(self.game.state["player"], {"x": 10, "y": 6})
        self.assertEqual(self.game.player_movement.position(1000), (9.0, 6.0))
        middle_x, middle_y = self.game.player_movement.position(1060)
        self.assertEqual((middle_x, middle_y), (9.5, 6.0))
        self.assertEqual(self.game.player_movement.position(1120), (10.0, 6.0))

        self.game.change_map("starting_town", 18, 14)
        self.assertEqual(self.game.player_movement.position(1121), (18.0, 14.0))

    def test_battle_selection_and_auto_battle_run_with_keyboard_facing_methods(self) -> None:
        self.game.change_map("greenwood", 6, 6)
        self.game.start_wild_battle({"species_id": "slime", "min_level": 1, "max_level": 1})
        self.game.battle_selection = 0
        self.assertEqual(self.game.selected_battle_command(), "fight")
        self.game.toggle_auto_battle()
        self.game.last_auto_tick = -1000
        self.game.update_auto_battle()
        self.assertGreaterEqual(self.game.battle.round_number, 1)
        self.assertTrue(self.game.battle_playback)

    def test_battle_actions_are_revealed_one_at_a_time_before_next_command(self) -> None:
        self.game.change_map("greenwood", 6, 6)
        self.game.start_wild_battle({"species_id": "slime", "min_level": 5, "max_level": 5})
        self.game.handle_battle_command("fight")
        battle = self.game.battle
        self.assertTrue(self.game.battle_playback)
        visible_before = self.game.battle_visible_log_count
        round_before = battle.round_number
        self.game.handle_battle_command("fight")
        self.assertEqual(battle.round_number, round_before)
        self.assertFalse(self.game.update_battle_playback(self.game.battle_next_log_tick - 1))
        self.assertTrue(self.game.update_battle_playback(self.game.battle_next_log_tick))
        self.assertEqual(self.game.battle_visible_log_count, visible_before + 1)
        saw_focused_actor = False
        for _ in range(40):
            if not self.game.battle_playback:
                break
            self.game.update_battle_playback(self.game.battle_next_log_tick)
            saw_focused_actor = saw_focused_actor or self.game.battle_focus_id is not None
        self.assertFalse(self.game.battle_playback)
        self.assertTrue(saw_focused_actor)
        self.assertEqual(self.game.battle_visible_log_count, len(battle.log))

    def test_detailed_critical_log_uses_the_short_battle_delay(self) -> None:
        self.assertEqual(
            self.game.battle_log_delay("会心！相手の防御力を無視した！"),
            self.game.battle_log_delay("会心！"),
        )

    def test_sign_cannot_be_walked_through(self) -> None:
        self.game.change_map("starting_town", 24, 14)
        self.game.move(1, 0)
        self.assertEqual((self.game.player_x, self.game.player_y), (24, 14))
        self.assertIn("通り抜けられません", self.game.status)

    def test_rock_interaction_enters_ghost_home_directly(self) -> None:
        self.game.change_map("fresh_forest", 22, 26)
        self.game.move(0, 1)
        self.assertEqual((self.game.player_x, self.game.player_y), (22, 26))
        self.assertIn("通り抜けられません", self.game.status)
        self.game.interact()
        self.assertEqual(self.game.map_data["id"], "ghost_home")

    def test_home_ghosts_wander_even_before_acquisition(self) -> None:
        self.game.change_map("ghost_home", 2, 9)
        self.assertEqual({npc["species_id"] for npc in self.game.home_npcs}, {"maru", "kadoka"})
        self.assertFalse(any(record.species_id in {"maru", "kadoka"} for record in self.monsters.list_records()))
        before = [(npc["x"], npc["y"]) for npc in self.game.home_npcs]
        visited = {tuple(before)}
        for _ in range(20):
            self.game.move_home_npcs()
            visited.add(tuple((npc["x"], npc["y"]) for npc in self.game.home_npcs))
        self.assertGreater(len(visited), 1)
        activity = {npc["species_id"]: npc["move_count"] for npc in self.game.home_npcs}
        self.assertGreater(activity["maru"], activity["kadoka"])
        positions = [(npc["x"], npc["y"]) for npc in self.game.home_npcs]
        self.assertEqual(len(positions), len(set(positions)))
        self.assertNotIn((self.game.player_x, self.game.player_y), positions)

    def test_visible_fixed_mob_keeps_grid_collision_while_its_sprite_interpolates(self) -> None:
        self.game.change_map("ghost_home", 2, 9)
        maru = next(npc for npc in self.game.home_npcs if npc["species_id"] == "maru")
        start = (int(maru["x"]), int(maru["y"]))
        maru["ai"] = "random"
        maru["move_chance"] = 100

        self.assertTrue(self.game.move_home_npc(maru, now=2000))

        target = (int(maru["x"]), int(maru["y"]))
        self.assertNotEqual(target, start)
        self.assertEqual(maru["_movement"].position(2000), tuple(float(value) for value in start))
        middle = maru["_movement"].position(2090)
        self.assertNotEqual(middle, tuple(float(value) for value in start))
        self.assertNotEqual(middle, tuple(float(value) for value in target))
        self.assertEqual(maru["_movement"].position(2180), tuple(float(value) for value in target))

    def test_player_and_home_npcs_cannot_share_a_tile(self) -> None:
        self.game.change_map("ghost_home", 9, 7)
        maru = next(npc for npc in self.game.home_npcs if npc["species_id"] == "maru")
        self.assertEqual((maru["x"], maru["y"]), (10, 7))
        self.game.move(1, 0)
        self.assertEqual((self.game.player_x, self.game.player_y), (9, 7))
        self.assertIn("キャラクター", self.game.status)

    def test_fixed_mob_dialogue_deck_does_not_repeat_and_facing_player_pauses_movement(self) -> None:
        self.game.change_map("ghost_home", 9, 7)
        self.game.player_direction = "right"
        maru = next(npc for npc in self.game.home_npcs if npc["species_id"] == "maru")
        before = (maru["x"], maru["y"])
        lines = []
        for _ in range(5):
            self.game.interact()
            lines.append(self.game.status)
        self.assertEqual(len(set(lines)), 5)
        self.assertTrue(self.game.npc_faces_player(maru))
        self.assertFalse(self.game.move_home_npc(maru))
        self.assertEqual((maru["x"], maru["y"]), before)

    def test_non_respawning_fixed_mob_stays_gone_after_talking(self) -> None:
        self.game.change_map("ghost_home", 5, 5)
        self.game.player_direction = "right"
        source = {
            "id": "one_time_boss", "species_id": "ghost", "name": "一度きりのおばけ",
            "x": 6, "y": 5, "direction": "left", "enabled": True, "ai": "idle",
            "move_interval_ms": 900, "move_chance": 100, "interaction": "talk", "despawn_after_interaction": True,
            "respawn_on_map_enter": False, "dialogue": ["さらばだ。"],
        }
        self.game.map_data.setdefault("fixed_mobs", []).append(source)
        self.game.reset_home_npcs()
        self.assertIsNotNone(next((npc for npc in self.game.home_npcs if npc["id"] == "one_time_boss"), None))
        self.game.interact()
        self.assertIsNone(next((npc for npc in self.game.home_npcs if npc["id"] == "one_time_boss"), None))
        self.game.reset_home_npcs()
        self.assertIsNone(next((npc for npc in self.game.home_npcs if npc["id"] == "one_time_boss"), None))

    def test_fixed_boss_starts_battle_and_can_disappear_after_victory(self) -> None:
        self.game.change_map("ghost_home", 5, 5)
        self.game.player_direction = "right"
        source = {
            "id": "test_boss", "species_id": "ghost", "name": "ボスおばけ", "level": 12,
            "x": 6, "y": 5, "direction": "left", "enabled": True, "ai": "idle",
            "move_interval_ms": 900, "move_chance": 100, "interaction": "battle",
            "despawn_after_interaction": True, "respawn_on_map_enter": False,
            "dialogue": ["勝負だ。"],
        }
        self.game.map_data.setdefault("fixed_mobs", []).append(source)
        self.game.reset_home_npcs()
        self.game.interact()
        self.assertEqual(self.game.mode, "battle")
        self.assertEqual(self.game.battle.enemies[0].record.level, 12)
        self.game.battle.outcome = "victory"
        self.game.return_to_field()
        self.assertIsNone(next((npc for npc in self.game.home_npcs if npc["id"] == "test_boss"), None))

    def test_seven_character_spring_password_acquires_maru_and_kadoka(self) -> None:
        self.game.change_map("ghost_home", 17, 8)
        self.game.interact()
        self.assertEqual(self.game.mode, "password")
        for character in "へいわなすみか余":
            self.game.append_password(character)
        self.assertEqual(self.game.password_input, "へいわなすみか")
        self.assertTrue(self.game.submit_password())
        self.assertEqual(self.game.mode, "field")
        species = {record.species_id for record in self.monsters.list_records()}
        self.assertTrue({"maru", "kadoka"}.issubset(species))

    def test_defeat_revives_at_saved_church(self) -> None:
        self.game.state["revive_point"] = {"map_id": "rokuta_village", "x": 14, "y": 10, "name": "ロクター教会"}
        self.game.battle = SimpleNamespace(outcome="defeat")
        self.game.mode = "battle"
        self.game.simulation = False
        self.game.return_to_field()
        self.assertEqual(self.game.map_data["id"], "rokuta_village")
        self.assertEqual((self.game.player_x, self.game.player_y), (14, 10))
        self.assertIn("ロクター教会から復活", self.game.status)

    def test_rokuta_church_updates_revival_point(self) -> None:
        self.game.change_map("rokuta_village", 14, 9)
        self.game.interact()
        self.assertEqual(self.game.state["revive_point"]["map_id"], "rokuta_village")
        self.assertEqual(self.game.state["revive_point"]["name"], "ロクター教会")


if __name__ == "__main__":
    unittest.main()

