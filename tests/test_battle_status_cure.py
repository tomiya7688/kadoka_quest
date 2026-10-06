# {
#   責務: [test_battle_status_cure: test・戦闘・状態異常・cureの公開機能・宣言を定義する]
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


SPIRIT_RECOVER = {
    "id": "spirit_recover",
    "display_name": "きあいでなおす",
    "kind": "heal",
    "heal_ratio": 0.03,
    "status_cure_chance": 0.03,
    "mp_cost": 4,
}
ATTACK = {
    "id": "attack",
    "display_name": "こうげき",
    "kind": "physical",
    "power": 1.0,
    "mp_cost": 0,
}


# {
#   責務: [FixedRng: fixed・乱数供給元の状態と振る舞いを担当する]
#   フィールド: [
#     values: 値一覧
#     random_calls: 乱数・calls
#   ]
# }
class FixedRng:
    # {
    #   責務: [__init__: fixed・乱数供給元が利用する初期状態と依存を設定する]
    #   処理: [1: fixed・乱数供給元が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     values: 値一覧（list[float]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, values: list[float]) -> None:
        self.values = list(values)
        self.random_calls = 0

    # {
    #   責務: [random: fixed・乱数供給元の乱数を求める]
    #   処理: [1: fixed・乱数供給元の乱数を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: fixed・乱数供給元の乱数を求めるための結果（float）]
    # }
    def random(self) -> float:
        self.random_calls += 1
        if not self.values:
            raise AssertionError("unexpected random() call")
        return self.values.pop(0)


# {
#   責務: [FirstUsableInference: first・usable・inferenceの状態と振る舞いを担当する]
#   フィールド: []
# }
class FirstUsableInference:
    # {
    #   責務: [choose: first・usable・inferenceを選択する]
    #   処理: [1: first・usable・inferenceを選択する]
    #   引数: [
    #     _ai: AI
    #     skills: スキル一覧
    #     _args: args
    #   ]
    #   戻り値: [result: first・usable・inferenceを選択するための結果（型注釈なし）]
    # }
    @staticmethod
    def choose(_ai, skills, *_args):
        return skills[0] if skills else None


# {
#   責務: [make_combatant: 戦闘個体を構築する]
#   処理: [1: 戦闘個体を構築する]
#   引数: [
#     name: 名前（str）
#     skills: スキル一覧（list[dict]）
#     hp: HP（int）
#     status_effects: 状態異常・effects（list[dict | str] | None）
#   ]
#   戻り値: [result: 戦闘個体（Combatant）]
# }
def make_combatant(
    name: str,
    skills: list[dict],
    *,
    hp: int = 100,
    status_effects: list[dict | str] | None = None,
) -> Combatant:
    combatant = Combatant(
        record=MonsterRecord(
            {"id": name, "species_id": "test", "name": name, "level": 1},
            {},
        ),
        stats={"hp": 100, "mp": 20, "attack": 20, "defense": 5, "magic": 10, "speed": 10},
        skills=skills,
        resistances={},
        status_effects=list(status_effects or []),
    )
    combatant.hp = hp
    return combatant


# {
#   責務: [make_engine: ルール処理を構築する]
#   処理: [1: ルール処理を構築する]
#   引数: [values: 値一覧（list[float]）]
#   戻り値: [result: ルール処理（BattleEngine）]
# }
def make_engine(values: list[float]) -> BattleEngine:
    engine = BattleEngine.__new__(BattleEngine)
    engine.rng = FixedRng(values)
    engine.learning_enabled = False
    engine.inference = FirstUsableInference()
    engine.log = []
    engine.round_number = 0
    engine.outcome = None
    engine.data_loader = SimpleNamespace(species_definition=lambda _species_id: {})
    return engine


# {
#   責務: [StatusCureTests: 状態異常・cure・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class StatusCureTests(unittest.TestCase):
    # {
    #   責務: [test_spirit_recover_cures_removable_status_on_success: 検証: spirit recover cures removable status on success]
    #   処理: [1: 検証: spirit recover cures removable status on success]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_spirit_recover_cures_removable_status_on_success(self) -> None:
        engine = make_engine([0.02])
        caster = make_combatant("caster", [SPIRIT_RECOVER])
        target = make_combatant(
            "target",
            [ATTACK],
            hp=50,
            status_effects=[{"id": "poison", "display_name": "毒", "removable": True}],
        )
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.hp, 53)
        self.assertEqual(target.status_effects, [])
        self.assertEqual(engine.rng.random_calls, 1)
        self.assertTrue(any("毒が治った" in line for line in engine.log))

    # {
    #   責務: [test_spirit_recover_leaves_status_on_failed_roll: 検証: spirit recover leaves status on failed roll]
    #   処理: [1: 検証: spirit recover leaves status on failed roll]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_spirit_recover_leaves_status_on_failed_roll(self) -> None:
        engine = make_engine([0.50])
        caster = make_combatant("caster", [SPIRIT_RECOVER])
        status = {"id": "poison", "display_name": "毒", "removable": True}
        target = make_combatant("target", [ATTACK], hp=50, status_effects=[status])
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.hp, 53)
        self.assertEqual(target.status_effects, [status])
        self.assertEqual(engine.rng.random_calls, 1)
        self.assertFalse(any("が治った" in line for line in engine.log))

    # {
    #   責務: [test_no_status_heals_without_consuming_cure_randomness: 検証: no status heals without consuming cure randomness]
    #   処理: [1: 検証: no status heals without consuming cure randomness]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_no_status_heals_without_consuming_cure_randomness(self) -> None:
        engine = make_engine([])
        caster = make_combatant("caster", [SPIRIT_RECOVER])
        target = make_combatant("target", [ATTACK], hp=50)
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.hp, 53)
        self.assertEqual(target.status_effects, [])
        self.assertEqual(engine.rng.random_calls, 0)

    # {
    #   責務: [test_nonremovable_status_is_not_considered_for_cure: 検証: nonremovable status is not considered for cure]
    #   処理: [1: 検証: nonremovable status is not considered for cure]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_nonremovable_status_is_not_considered_for_cure(self) -> None:
        engine = make_engine([])
        caster = make_combatant("caster", [SPIRIT_RECOVER])
        status = {"id": "special_lock", "display_name": "特殊拘束", "removable": False}
        target = make_combatant("target", [ATTACK], hp=50, status_effects=[status])
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.hp, 53)
        self.assertEqual(target.status_effects, [status])
        self.assertEqual(engine.rng.random_calls, 0)

    # {
    #   責務: [test_cure_skips_nonremovable_status_and_removes_removable_one: 検証: cure skips nonremovable status and removes removable one]
    #   処理: [1: 検証: cure skips nonremovable status and removes removable one]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_cure_skips_nonremovable_status_and_removes_removable_one(self) -> None:
        engine = make_engine([0.0])
        caster = make_combatant("caster", [SPIRIT_RECOVER])
        locked = {"id": "special_lock", "display_name": "特殊拘束", "removable": False}
        poison = {"id": "poison", "display_name": "毒", "removable": True}
        target = make_combatant("target", [ATTACK], hp=50, status_effects=[locked, poison])
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.status_effects, [locked])
        self.assertTrue(any("毒が治った" in line for line in engine.log))


if __name__ == "__main__":
    unittest.main()
