# {
#   責務: [test_simulation_facility_service: test・simulation・facility・serviceの公開機能・宣言を定義する]
#   フィールド: []
# }
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


# {
#   責務: [SimulationFacilityServiceTests: simulation・facility・service・testsの状態と振る舞いを担当する]
#   フィールド: [
#     temporary: temporary
#     root: 基準ディレクトリ
#     repository: データ取得先
#     service: service
#   ]
# }
class SimulationFacilityServiceTests(unittest.TestCase):
    # {
    #   責務: [setUp: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = GameRepository(PROJECT_ROOT / "data")
        self.service = SimulationFacilityService(self.repository, self.root / "simulation")

    # {
    #   責務: [tearDown: 検証用fixtureと一時的な変更を後始末する]
    #   処理: [1: 検証用fixtureと一時的な変更を後始末する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def tearDown(self) -> None:
        self.temporary.cleanup()

    # {
    #   責務: [test_created_individual_is_not_added_to_owned_store: 検証: created individual is not added to owned store]
    #   処理: [1: 検証: created individual is not added to owned store]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_created_individual_is_not_added_to_owned_store(self) -> None:
        created = self.service.create_individual("slime", level=12, name="練習スライム")
        self.assertEqual(created.name, "練習スライム")
        self.assertEqual([record.monster_id for record in self.service.list_individuals()], [created.monster_id])
        self.assertEqual(MonsterStore(self.root / "owned", self.repository).list_records(), [])

    # {
    #   責務: [test_roster_selection_deletion_and_non_learning_battle: 検証: roster selection deletion and non learning battle]
    #   処理: [1: 検証: roster selection deletion and non learning battle]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [test_battle_requires_explicit_opponent_party: 検証: battle requires explicit opponent party]
    #   処理: [1: 検証: battle requires explicit opponent party]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_battle_requires_explicit_opponent_party(self) -> None:
        self.service.create_individual("slime")
        battle, message = self.service.create_battle([], random.Random(1))
        self.assertIsNone(battle)
        self.assertIn("相手パーティを編成", message)


if __name__ == "__main__":
    unittest.main()
