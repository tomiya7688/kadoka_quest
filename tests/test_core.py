from __future__ import annotations

import copy
from pathlib import Path
import random
import sys
import tempfile
from types import SimpleNamespace
import unittest

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.apps.game import KadokaQuest
from kadoka_quest.core.monster import calculate_stats
from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository, STAT_KEYS
from kadoka_quest.data.savedata import SaveDataManager
from kadoka_quest.data.state import StateStore


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
        spring = next(item for item in home["events"] if item["id"] == "ghost_spring")
        self.assertEqual(spring["type"], "password_spring")
        self.assertEqual(home["tiles"][spring["y"]][spring["x"]], "water")
        for species_id in ("hero", "slime", "ball_slime", "metal_slime", "ghost", "maru", "kadoka", "dice_slime"):
            definition = self.repository.get_species(species_id).definition
            portrait = PROJECT_ROOT / "assets" / definition["portrait_path"]
            self.assertTrue(portrait.is_file())
            self.assertLessEqual(pygame.image.load(str(portrait)).get_width(), 64)
            self.assertLessEqual(pygame.image.load(str(portrait)).get_height(), 64)
            self.assertTrue((PROJECT_ROOT / "assets" / definition["field_sprite_path"]).is_file())
            self.assertEqual(set(definition["field_sprites"]), {"front", "right", "left", "back"})
            for path in definition["field_sprites"].values():
                image_path = PROJECT_ROOT / "assets" / path
                self.assertTrue(image_path.is_file())
                image = pygame.image.load(str(image_path))
                self.assertLessEqual(image.get_width(), 64)
                self.assertLessEqual(image.get_height(), 64)


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
        record = self.monsters.create("hero", level=30)
        base = calculate_stats(self.repository, record)
        record.monster["equipment_id"] = "ken"
        equipped = calculate_stats(self.repository, record)
        self.assertEqual(equipped["speed"], round(base["speed"] * 0.8))
        self.assertEqual(equipped["attack"], base["attack"])

    def test_ai_reset_keeps_individual_progression(self) -> None:
        record = self.monsters.create("ghost", "経験豊富なおばけ", 77)
        record.monster["plus_choices"] = ["ghost_plus_1_magic"]
        record.ai["action_preferences"] = {"possess": 0.9}
        self.monsters.save(record)
        reset = self.monsters.reset_ai(record.monster_id)
        self.assertEqual(reset.level, 77)
        self.assertEqual(reset.plus_choices, ["ghost_plus_1_magic"])
        self.assertEqual(reset.ai["action_preferences"], {})

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

    def test_bundled_external_folder_is_simulation_ready(self) -> None:
        imported = self.monsters.discover_external(PROJECT_ROOT / "examples" / "simulation_party")
        self.assertEqual([record.monster_id for record in imported], ["guest_dice_slime_001"])
        ally = self.monsters.create("ball_slime", level=12)
        engine = BattleEngine(self.repository, [ally], imported, random.Random(8), learning_enabled=False)
        engine.run_round()
        self.assertGreaterEqual(engine.round_number, 1)


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

    def test_hidden_monsters_are_not_ball_slimes_and_collision_starts_battle(self) -> None:
        self.game.change_map("greenwood", 6, 6)
        self.assertTrue(self.game.hidden_monsters)
        self.assertNotIn("ball_slime", {item["spawn"]["species_id"] for item in self.game.hidden_monsters})
        hidden = self.game.hidden_monsters[0]
        self.game.player_x, self.game.player_y = hidden["x"], hidden["y"]
        self.assertTrue(self.game.check_hidden_collision())
        self.assertEqual(self.game.mode, "battle")

    def test_battle_selection_and_auto_battle_run_with_keyboard_facing_methods(self) -> None:
        self.game.change_map("greenwood", 6, 6)
        self.game.start_wild_battle({"species_id": "slime", "min_level": 1, "max_level": 1})
        self.game.battle_selection = 0
        self.assertEqual(self.game.selected_battle_command(), "fight")
        self.game.toggle_auto_battle()
        self.game.last_auto_tick = -1000
        self.game.update_auto_battle()
        self.assertGreaterEqual(self.game.battle.round_number, 1)

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

