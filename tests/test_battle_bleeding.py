# {
#   責務: [test_battle_bleeding: test・戦闘・bleedingの公開機能・宣言を定義する]
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
from kadoka_quest.core.status_effects import has_status, status_apply_chance


BLEEDING_EFFECT = {
    "id": "bleeding",
    "display_name": "出血",
    "chance": 1.0,
    "removable": True,
}
BLEEDING_ATTACK = {
    "id": "test_bleeding_attack",
    "display_name": "テストひっかき",
    "kind": "physical",
    "power": 0.8,
    "mp_cost": 0,
    "status_effect": BLEEDING_EFFECT,
}


# {
#   責務: [FixedRng: fixed・乱数供給元の状態と振る舞いを担当する]
#   フィールド: []
# }
class FixedRng:
    # {
    #   責務: [random: fixed・乱数供給元の乱数を求める]
    #   処理: [1: fixed・乱数供給元の乱数を求める]
    #   引数: []
    #   戻り値: [result: fixed・乱数供給元の乱数を求めるための結果（float）]
    # }
    @staticmethod
    def random() -> float:
        return 0.0

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
    #   責務: [randint: fixed・乱数供給元のrandintを求める]
    #   処理: [1: fixed・乱数供給元のrandintを求める]
    #   引数: [
    #     low: low（int）
    #     _high: high（int）
    #   ]
    #   戻り値: [result: low（int）]
    # }
    @staticmethod
    def randint(low: int, _high: int) -> int:
        return low

    # {
    #   責務: [shuffle: fixed・乱数供給元の並べ替えを求める]
    #   処理: [1: fixed・乱数供給元の並べ替えを求める]
    #   引数: [_items: アイテム一覧（list）]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @staticmethod
    def shuffle(_items: list) -> None:
        return None


# {
#   責務: [make_combatant: 戦闘個体を構築する]
#   処理: [1: 戦闘個体を構築する]
#   引数: [
#     name: 名前（str）
#     status_resistances: 状態異常・resistances（dict[str, str] | None）
#   ]
#   戻り値: [result: 戦闘個体を構築するための結果（Combatant）]
# }
def make_combatant(
    name: str,
    *,
    status_resistances: dict[str, str] | None = None,
) -> Combatant:
    return Combatant(
        record=MonsterRecord(
            {"id": name, "species_id": "test", "name": name, "level": 1},
            {},
        ),
        stats={"hp": 100, "mp": 20, "attack": 40, "defense": 50, "magic": 20, "speed": 40},
        skills=[],
        resistances={},
        status_resistances=dict(status_resistances or {}),
    )


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
#   責務: [BleedingStatusTests: bleeding・状態異常・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class BleedingStatusTests(unittest.TestCase):
    # {
    #   責務: [test_status_resistance_levels_scale_application_chance: 検証: status resistance levels scale application chance]
    #   処理: [1: 検証: status resistance levels scale application chance]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_status_resistance_levels_scale_application_chance(self) -> None:
        expected = {
            "very_weak": 0.60,
            "weak": 0.50,
            "normal": 0.40,
            "resist": 0.30,
            "strong": 0.20,
            "immune": 0.00,
        }
        for level, chance in expected.items():
            with self.subTest(level=level):
                self.assertAlmostEqual(status_apply_chance(0.4, level), chance)

    # {
    #   責務: [test_bleeding_immune_target_cannot_be_inflicted: 検証: bleeding immune target cannot be inflicted]
    #   処理: [1: 検証: bleeding immune target cannot be inflicted]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_bleeding_immune_target_cannot_be_inflicted(self) -> None:
        engine = make_engine()
        actor = make_combatant("actor")
        target = make_combatant("target", status_resistances={"bleeding": "immune"})

        engine._attack(actor, target, BLEEDING_ATTACK)

        self.assertFalse(has_status(target.status_effects, "bleeding"))
        self.assertTrue(any("出血が効かなかった" in line for line in engine.log))

    # {
    #   責務: [test_bleeding_reduces_speed_and_defense_and_deals_small_turn_damage: 検証: bleeding reduces speed and defense and deals small turn damage]
    #   処理: [1: 検証: bleeding reduces speed and defense and deals small turn damage]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_bleeding_reduces_speed_and_defense_and_deals_small_turn_damage(self) -> None:
        engine = make_engine()
        actor = make_combatant("actor")
        target = make_combatant("target")

        engine._attack(actor, target, BLEEDING_ATTACK)

        self.assertTrue(has_status(target.status_effects, "bleeding"))
        self.assertEqual(target.speed, 36)
        self.assertEqual(target.defense, 45)

        before = target.hp
        engine._tick_end_turn_status(target)
        self.assertEqual(before - target.hp, 2)

    # {
    #   責務: [test_bleeding_does_not_stack_and_cure_restores_stats: 検証: bleeding does not stack and cure restores stats]
    #   処理: [1: 検証: bleeding does not stack and cure restores stats]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_bleeding_does_not_stack_and_cure_restores_stats(self) -> None:
        engine = make_engine()
        target = make_combatant("target")

        self.assertTrue(engine._try_apply_status(target, BLEEDING_EFFECT))
        self.assertFalse(engine._try_apply_status(target, BLEEDING_EFFECT))
        self.assertEqual(sum(1 for effect in target.status_effects if effect.get("id") == "bleeding"), 1)
        self.assertEqual(target.speed, 36)
        self.assertEqual(target.defense, 45)

        cured = engine._try_cure_status(target, 1.0)

        self.assertEqual(cured, "出血")
        self.assertFalse(has_status(target.status_effects, "bleeding"))
        self.assertEqual(target.speed, 40)
        self.assertEqual(target.defense, 50)


if __name__ == "__main__":
    unittest.main()
