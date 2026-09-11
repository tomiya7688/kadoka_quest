from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.apps.simulation_facility_service import SimulationFacilityService
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository


class SimulationFacilityServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = GameRepository(PROJECT_ROOT / "data")
        self.service = SimulationFacilityService(self.repository, self.root / "simulation")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_created_individual_is_not_added_to_owned_store(self) -> None:
        created = self.service.create_individual("slime", level=12, name="練習スライム")
        self.assertEqual(created.name, "練習スライム")
        self.assertEqual([record.monster_id for record in self.service.list_individuals()], [created.monster_id])
        self.assertEqual(MonsterStore(self.root / "owned", self.repository).list_records(), [])

    def test_roster_selection_deletion_and_non_learning_battle(self) -> None:
        first = self.service.create_individual("slime", level=10)
        second = self.service.create_individual("ghost", level=12)
        selected = self.service.set_opponents([second.monster_id, first.monster_id, second.monster_id])
        self.assertEqual([record.monster_id for record in selected], [second.monster_id, first.monster_id])
        self.assertTrue(self.service.delete_individual(second.monster_id))
        self.assertEqual([record.monster_id for record in self.service.opponents()], [first.monster_id])
        ally = MonsterStore(self.root / "owned", self.repository).create("ball_slime", level=10)
        battle, message = self.service.create_battle([ally], random.Random(1))
        self.assertIsNotNone(battle)
        self.assertFalse(battle.learning_enabled)
        self.assertIn("報酬も発生しません", message)

    def test_battle_requires_explicit_opponent_party(self) -> None:
        self.service.create_individual("slime")
        battle, message = self.service.create_battle([], random.Random(1))
        self.assertIsNone(battle)
        self.assertIn("相手パーティを編成", message)


if __name__ == "__main__":
    unittest.main()
