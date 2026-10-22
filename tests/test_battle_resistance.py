# {
#   責務: [test_battle_resistance: test・戦闘・resistanceの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.combatant import Combatant
from kadoka_quest.core.monster import MonsterRecord


MAGIC_SKILL = {
    "id": "test_magic",
    "display_name": "テスト魔法",
    "kind": "magic",
    "element": "fire",
    "power": 1.0,
    "mp_cost": 1,
}
DRAIN_SKILL = {
    "id": "test_drain",
    "display_name": "テスト吸収",
    "kind": "drain_mp",
    "element": "mental",
    "power": 1.0,
    "mp_power": 0.5,
    "mp_cost": 1,
}


# {
#   責務: [FixedRng: fixed・乱数供給元の状態と振る舞いを担当する]
#   フィールド: []
# }
class FixedRng:
    # {
    #   責務: [uniform: fixed・乱数供給元のuniformを求める]
    #   処理: [1: fixed・乱数供給元のuniformを求める]
    #   引数: [
    #     _low: low（float）
    #     _high: high（float）
    #   ]
    #   戻り値: [result: fixed・乱数供給元のuniformを求めるための結果（float）]
    # }
    @staticmethod
    def uniform(_low: float, _high: float) -> float:
        return 1.0


# {
#   責務: [make_combatant: 戦闘個体を構築する]
#   処理: [1: 戦闘個体を構築する]
#   引数: [
#     name: 名前（str）
#     hp: HP（int）
#     mp: MP（int）
#     resistances: resistances（dict[str, str] | None）
#   ]
#   戻り値: [result: 戦闘個体（Combatant）]
# }
def make_combatant(
    name: str,
    *,
    hp: int = 100,
    mp: int = 10,
    resistances: dict[str, str] | None = None,
) -> Combatant:
    record = MonsterRecord(
        {"id": name, "species_id": "test", "name": name, "level": 1},
        {},
    )
    combatant = Combatant(
        record=record,
        stats={"hp": 100, "mp": 20, "attack": 20, "defense": 5, "magic": 20, "speed": 10},
        skills=[],
        resistances=resistances or {},
    )
    combatant.hp = hp
    combatant.mp = mp
    return combatant


# {
#   責務: [make_engine: ルール処理を構築する]
#   処理: [1: ルール処理を構築する]
#   引数: []
#   戻り値: [result: ルール処理（BattleEngine）]
# }
def make_engine() -> BattleEngine:
    engine = BattleEngine.__new__(BattleEngine)
    engine.rng = FixedRng()
    engine.log = []
    engine.data_loader = SimpleNamespace(species_definition=lambda _species_id: {})
    return engine


# {
#   責務: [ResistanceResolutionTests: resistance・resolution・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class ResistanceResolutionTests(unittest.TestCase):
    # {
    #   責務: [test_immune_attribute_takes_zero_damage: 検証: immune attribute takes zero damage]
    #   処理: [1: 検証: immune attribute takes zero damage]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_immune_attribute_takes_zero_damage(self) -> None:
        engine = make_engine()
        actor = make_combatant("actor")
        target = make_combatant("target", hp=70, resistances={"fire": "immune"})

        reward = engine._attack(actor, target, MAGIC_SKILL)

        self.assertEqual(target.hp, 70)
        self.assertEqual(reward, 0.0)
        self.assertTrue(any("効かなかった" in line for line in engine.log))

    # {
    #   責務: [test_absorb_attribute_recovers_hp_and_respects_max_hp: 検証: absorb attribute recovers hp and respects max hp]
    #   処理: [1: 検証: absorb attribute recovers hp and respects max hp]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_absorb_attribute_recovers_hp_and_respects_max_hp(self) -> None:
        engine = make_engine()
        actor = make_combatant("actor")
        target = make_combatant("target", hp=70, resistances={"fire": "absorb"})

        reward = engine._attack(actor, target, MAGIC_SKILL)

        self.assertEqual(target.hp, 80)
        self.assertEqual(reward, -0.1)
        self.assertTrue(any("吸収" in line for line in engine.log))

        capped_target = make_combatant("capped", hp=95, resistances={"fire": "absorb"})
        capped_reward = engine._attack(actor, capped_target, MAGIC_SKILL)
        self.assertEqual(capped_target.hp, 100)
        self.assertEqual(capped_reward, -0.05)

    # {
    #   責務: [test_weak_normal_and_strong_keep_existing_damage_multipliers: 検証: weak normal and strong keep existing damage multipliers]
    #   処理: [1: 検証: weak normal and strong keep existing damage multipliers]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_weak_normal_and_strong_keep_existing_damage_multipliers(self) -> None:
        expected_damage = {"strong": 12, "normal": 20, "weak": 28}

        for resistance, damage in expected_damage.items():
            with self.subTest(resistance=resistance):
                engine = make_engine()
                actor = make_combatant("actor")
                target = make_combatant("target", resistances={"fire": resistance})

                engine._attack(actor, target, MAGIC_SKILL)

                self.assertEqual(target.hp, 100 - damage)

    # {
    #   責務: [test_mental_immune_blocks_drain_mp_damage_and_mp_drain: 検証: mental immune blocks drain mp damage and mp drain]
    #   処理: [1: 検証: mental immune blocks drain mp damage and mp drain]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_mental_immune_blocks_drain_mp_damage_and_mp_drain(self) -> None:
        engine = make_engine()
        actor = make_combatant("actor", mp=3)
        target = make_combatant("target", hp=75, mp=12, resistances={"mental": "immune"})

        reward = engine._attack(actor, target, DRAIN_SKILL)

        self.assertEqual(target.hp, 75)
        self.assertEqual(target.mp, 12)
        self.assertEqual(actor.mp, 3)
        self.assertEqual(reward, 0.0)
        self.assertFalse(any("MPを" in line and "奪った" in line for line in engine.log))


if __name__ == "__main__":
    unittest.main()
