# {
#   責務: [test_battle_buff_duration: 一時強化の継続期間・再付与・期限切れと元倍率への復元をPython正本で検査します]
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


PIO = {
    "id": "piora",
    "display_name": "ピオラ",
    "kind": "buff",
    "speed_multiplier": 1.5,
    "duration": [3, 6],
    "mp_cost": 5,
}
CHEER = {
    "id": "cheer",
    "display_name": "おうえん",
    "kind": "buff",
    "attack_multiplier": 1.2,
    "mp_cost": 3,
}
ATTACK = {
    "id": "attack",
    "display_name": "こうげき",
    "kind": "physical",
    "power": 1.0,
    "mp_cost": 0,
}


# {
#   責務: [SequenceRng: 継続ターン数の返却順を保持し、範囲指定の抽選を再現可能な値へ固定します]
#   フィールド: [durations: randintで先頭から一件ずつ使う継続ターン数の独立した列（list[int]）]
# }
class SequenceRng:
    # {
    #   責務: [__init__: 継続ターン数の指定列を、元の列と共有しないようコピーして保持します]
    #   処理: [1: randintで消費する専用のリストを作ります]
    #   引数: [
    #     self: 抽選用ターン数の返却順を所有するSequenceRng
    #     durations: テストで返したい継続ターン数の列（list[int]）
    #   ]
    #   戻り値: [result: なし（None）。呼出側のdurationsは変更しません]
    # }
    def __init__(self, durations: list[int]) -> None:
        # 乱数スタブで要素を消費しても、呼出側の期待値用リストを変更しないようにします。
        self.durations = list(durations)

    # {
    #   責務: [randint: 保存した次の継続ターン数を一件消費し、要求された上下限内であることを確認します]
    #   処理: [1: 先頭の値を取り出し、範囲外ならAssertionError、範囲内なら値を返します]
    #   引数: [
    #     self: 次の返却ターン数を保持するSequenceRng
    #     low: 許可する継続ターン数の下限を含む値（int）
    #     high: 許可する継続ターン数の上限を含む値（int）
    #   ]
    #   戻り値: [result: low以上high以下の次のターン数（int）。空列ならIndexErrorです]
    # }
    def randint(self, low: int, high: int) -> int:
        # 期間抽選の範囲変更を、固定値の不正としてテストで検出できるようにします。
        value = self.durations.pop(0)
        if not low <= value <= high:
            raise AssertionError(f"duration {value} outside {low}..{high}")
        return value

    # {
    #   責務: [random: 戦闘テストの確率入力を境界値1.0へ固定します]
    #   処理: [1: 状態を消費せず、毎回同じ小数値を返します]
    #   引数: []
    #   戻り値: [result: 常に1.0（float）。通常の乱数分布を再現するものではありません]
    # }
    @staticmethod
    def random() -> float:
        # 継続期間以外の確率入力も固定し、テスト実行ごとの揺らぎをなくします。
        return 1.0

    # {
    #   責務: [uniform: sequence・乱数供給元のuniformを求める]
    #   処理: [1: sequence・乱数供給元のuniformを求める]
    #   引数: [
    #     _low: low（float）
    #     _high: high（float）
    #   ]
    #   戻り値: [result: sequence・乱数供給元のuniformを求めるための結果（float）]
    # }
    @staticmethod
    def uniform(_low: float, _high: float) -> float:
        return 1.0

    # {
    #   責務: [shuffle: sequence・乱数供給元の並べ替えを求める]
    #   処理: [1: sequence・乱数供給元の並べ替えを求める]
    #   引数: [_items: アイテム一覧（list）]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @staticmethod
    def shuffle(_items: list) -> None:
        return None


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
#   ]
#   戻り値: [result: 戦闘個体を構築するための結果（Combatant）]
# }
def make_combatant(name: str, skills: list[dict]) -> Combatant:
    return Combatant(
        record=MonsterRecord(
            {"id": name, "species_id": "test", "name": name, "level": 1},
            {},
        ),
        stats={"hp": 100, "mp": 20, "attack": 20, "defense": 5, "magic": 10, "speed": 10},
        skills=skills,
        resistances={},
    )


# {
#   責務: [make_engine: ルール処理を構築する]
#   処理: [1: ルール処理を構築する]
#   引数: [durations: durations（list[int]）]
#   戻り値: [result: ルール処理（BattleEngine）]
# }
def make_engine(durations: list[int]) -> BattleEngine:
    engine = BattleEngine.__new__(BattleEngine)
    engine.rng = SequenceRng(durations)
    engine.learning_enabled = False
    engine.inference = FirstUsableInference()
    engine.log = []
    engine.round_number = 0
    engine.outcome = None
    engine.data_loader = SimpleNamespace(species_definition=lambda _species_id: {})
    return engine


# {
#   責務: [BuffDurationTests: buff・継続時間・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class BuffDurationTests(unittest.TestCase):
    # {
    #   責務: [test_piora_minimum_duration_expires_after_three_turn_ticks: 検証: piora minimum duration expires after three turn ticks]
    #   処理: [1: 検証: piora minimum duration expires after three turn ticks]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_piora_minimum_duration_expires_after_three_turn_ticks(self) -> None:
        engine = make_engine([3])
        caster = make_combatant("caster", [PIO])
        target = make_combatant("target", [ATTACK])
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.speed_multiplier, 1.5)
        self.assertEqual(target.timed_buff_turns["speed_multiplier"], 3)
        self.assertEqual(target.speed, 15)

        engine._tick_timed_buffs(target)
        engine._tick_timed_buffs(target)
        self.assertEqual(target.speed_multiplier, 1.5)
        self.assertEqual(target.timed_buff_turns["speed_multiplier"], 1)

        engine._tick_timed_buffs(target)
        self.assertEqual(target.speed_multiplier, 1.0)
        self.assertEqual(target.speed, 10)
        self.assertNotIn("speed_multiplier", target.timed_buff_turns)

    # {
    #   責務: [test_piora_maximum_duration_accepts_six_turn_boundary: 検証: piora maximum duration accepts six turn boundary]
    #   処理: [1: 検証: piora maximum duration accepts six turn boundary]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_piora_maximum_duration_accepts_six_turn_boundary(self) -> None:
        engine = make_engine([6])
        caster = make_combatant("caster", [PIO])
        target = make_combatant("target", [ATTACK])
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.timed_buff_turns["speed_multiplier"], 6)
        for _ in range(5):
            engine._tick_timed_buffs(target)
        self.assertEqual(target.speed_multiplier, 1.5)
        self.assertEqual(target.timed_buff_turns["speed_multiplier"], 1)

        engine._tick_timed_buffs(target)
        self.assertEqual(target.speed_multiplier, 1.0)

    # {
    #   責務: [test_reusing_same_timed_buff_never_shortens_multiplier_or_duration: 検証: reusing same timed buff never shortens multiplier or duration]
    #   処理: [1: 検証: reusing same timed buff never shortens multiplier or duration]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_reusing_same_timed_buff_never_shortens_multiplier_or_duration(self) -> None:
        engine = make_engine([3, 6])
        caster = make_combatant("caster", [PIO])
        target = make_combatant("target", [ATTACK])
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])
        engine._tick_timed_buffs(target)
        self.assertEqual(target.timed_buff_turns["speed_multiplier"], 2)

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.speed_multiplier, 1.5)
        self.assertEqual(target.timed_buff_turns["speed_multiplier"], 6)

    # {
    #   責務: [test_durationless_attack_buff_keeps_existing_until_next_attack_behavior: 検証: durationless attack buff keeps existing until next attack behavior]
    #   処理: [1: 検証: durationless attack buff keeps existing until next attack behavior]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_durationless_attack_buff_keeps_existing_until_next_attack_behavior(self) -> None:
        engine = make_engine([])
        caster = make_combatant("caster", [CHEER])
        target = make_combatant("target", [ATTACK])
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.attack_multiplier, 1.2)
        self.assertNotIn("attack_multiplier", target.timed_buff_turns)
        for _ in range(8):
            engine._tick_timed_buffs(target)
        self.assertEqual(target.attack_multiplier, 1.2)

        engine._attack(target, foe, ATTACK)
        self.assertEqual(target.attack_multiplier, 1.0)

    # {
    #   責務: [test_timed_buff_restores_preexisting_untimed_baseline: 検証: timed buff restores preexisting untimed baseline]
    #   処理: [1: 検証: timed buff restores preexisting untimed baseline]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_timed_buff_restores_preexisting_untimed_baseline(self) -> None:
        engine = make_engine([3])
        target = make_combatant("target", [ATTACK])
        target.speed_multiplier = 1.2

        BattleEngine._apply_multiplier(target, "speed_multiplier", 1.5, 3)
        self.assertEqual(target.timed_buff_baselines["speed_multiplier"], 1.2)

        for _ in range(3):
            engine._tick_timed_buffs(target)

        self.assertEqual(target.speed_multiplier, 1.2)
        self.assertNotIn("speed_multiplier", target.timed_buff_baselines)


if __name__ == "__main__":
    unittest.main()
