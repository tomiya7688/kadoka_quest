# {
#   責務: [test_battle_status_cure: 実Pythonの治療付き回復について、HP回復と状態一つの解除/乱数要否を検証します]
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
#   責務: [FixedRng: 判定値を指定順に返し、予期しない乱数呼び出しを検出します]
#   フィールド: [
#     values: 次の呼び出しから順に返す未使用の判定値一覧（list[float]）
#     random_calls: randomが呼ばれた累積回数（int）
#   ]
# }
class FixedRng:
    # {
    #   責務: [__init__: 指定した判定値をコピーし、呼び出し回数を0で初期化します]
    #   処理: [1: 呼出元の一覧を変更しない未使用値一覧を作ります]
    #   引数: [
    #     self: 未使用判定値と呼び出し回数を持つ所有者
    #     values: テストが指定する乱数の代わりの判定値（list[float]）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, values: list[float]) -> None:
        self.values = list(values)
        self.random_calls = 0

    # {
    #   責務: [random: 次の指定判定値を一つ消費し、呼び出し回数を増やします]
    #   処理: [1: 未使用値があれば先頭を返し、なければ予期しない呼び出しとして失敗します]
    #   引数: [self: 判定値と呼び出し回数を持つ所有者]
    #   戻り値: [result: 次の判定値（float）。未使用値がなければAssertionErrorです]
    # }
    def random(self) -> float:
        self.random_calls += 1
        if not self.values:
            raise AssertionError("unexpected random() call")
        return self.values.pop(0)


# {
#   責務: [FirstUsableInference: 使用可能スキルの先頭を選び、治療比較でAIの行動選択だけを固定します]
#   フィールド: []
# }
class FirstUsableInference:
    # {
    #   責務: [choose: 使用可能一覧の先頭スキルだけを選び、推論や学習は行いません]
    #   処理: [1: 一覧が空ならNone、それ以外なら先頭定義を返します]
    #   引数: [
    #     _ai: 推論へ渡される個体AI。固定選択では使用しません
    #     skills: 使用可能として渡されたスキル一覧（list）
    #     _args: 実推論と呼び出し形を合わせる未使用の戦況引数
    #   ]
    #   戻り値: [result: 先頭スキルの定義、またはNone]
    # }
    @staticmethod
    def choose(_ai, skills, *_args):
        return skills[0] if skills else None


# {
#   責務: [make_combatant: 治療比較用の最大HP100/MP20の独立した戦闘個体を作ります]
#   処理: [1: 仮の個体記録・能力値・状態一覧を組み立て、現在HPを指定値にします]
#   引数: [
#     name: 仮個体のIDと表示名に使う名前（str）
#     skills: 比較用個体に与えるスキル定義一覧（list[dict]）
#     hp: 比較を開始する現在HP。最大HPは100です（int）
#     status_effects: 比較開始時の状態異常。外側の一覧だけをコピーします（list[dict | str] | None）
#   ]
#   戻り値: [result: 保存や実データ読み込みを伴わない比較用個体（Combatant）]
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
#   責務: [make_engine: 実治療を比較するため、学習なし・固定乱数/選択のBattleEngineを用意します]
#   処理: [1: 保存や正規JSONの読み込みをせず、実行に必要な比較用依存を設定します]
#   引数: [values: 治療判定で順に使う明示値。候補なしは空一覧です（list[float]）]
#   戻り値: [result: 実_try_cure_status/_take_actionを呼べる比較用エンジン（BattleEngine）]
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
#   責務: [StatusCureTests: 治療付き回復のHP53と、状態一つの解除/保持・判定回数を確認します]
#   フィールド: []
# }
class StatusCureTests(unittest.TestCase):
    # {
    #   責務: [test_spirit_recover_cures_removable_status_on_success: 3%治療が判定値0.02で毒を解除することを確認します]
    #   処理: [1: 実回復行動後のHP53・毒の除去・乱数一回と治療ログを照合します]
    #   引数: [self: 治療成立を検証するテストケース]
    #   戻り値: [result: なし（None）]
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
    #   責務: [test_spirit_recover_leaves_status_on_failed_roll: 判定値0.50で治療不成立でもHP回復だけは行うことを確認します]
    #   処理: [1: HP53・毒の保持・乱数一回と治療ログなしを照合します]
    #   引数: [self: 治療不成立を検証するテストケース]
    #   戻り値: [result: なし（None）]
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
    #   責務: [test_no_status_heals_without_consuming_cure_randomness: 状態異常なしなら治療乱数を使わずHPを回復することを確認します]
    #   処理: [1: 空の状態一覧・HP53と乱数呼び出し0回を照合します]
    #   引数: [self: 候補なしの回復を検証するテストケース]
    #   戻り値: [result: なし（None）]
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
    #   責務: [test_nonremovable_status_is_not_considered_for_cure: 解除不可の特殊拘束だけなら治療乱数を使わないことを確認します]
    #   処理: [1: HP53・特殊拘束の保持と乱数呼び出し0回を照合します]
    #   引数: [self: 解除不可状態の扱いを検証するテストケース]
    #   戻り値: [result: なし（None）]
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
    #   責務: [test_cure_skips_nonremovable_status_and_removes_removable_one: 先頭の特殊拘束を飛ばして後続の毒一つを治療することを確認します]
    #   処理: [1: 実回復行動後に特殊拘束だけが残り、毒の治療ログが出ることを照合します]
    #   引数: [self: 候補順序と一件治療を検証するテストケース]
    #   戻り値: [result: なし（None）]
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
