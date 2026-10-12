# {
#   責務: [test_battle_bleeding: 実Pythonの出血付与・耐性・重複・能力値低下/終了時ダメージと治療後の回復を検査します]
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
#   責務: [FixedRng: 出血テストの乱数依存を固定値に置き換え、判定/威力/期間を再現可能にします]
#   フィールド: []
# }
class FixedRng:
    # {
    #   責務: [random: 出血成功判定に使う固定値0.0を返します]
    #   処理: [1: 出血成功判定を再現するため0.0を返します]
    #   引数: []
    #   戻り値: [result: 出血成功判定用の固定値0.0（float）]
    # }
    @staticmethod
    def random() -> float:
        return 0.0

    # {
    #   責務: [uniform: 攻撃威力の乱数倍率を固定値1.0へ置き換えます]
    #   処理: [1: 攻撃威力を再現するため1.0を返します]
    #   引数: [
    #     _low: 実uniformと呼び出しを合わせる未使用の下限（float）
    #     _high: 実uniformと呼び出しを合わせる未使用の上限（float）
    #   ]
    #   戻り値: [result: 攻撃威力用の固定倍率1.0（float）]
    # }
    @staticmethod
    def uniform(_low: float, _high: float) -> float:
        return 1.0

    # {
    #   責務: [randint: 整数乱数を指定下限に固定して期間等の計算を再現します]
    #   処理: [1: 指定された整数下限を返します]
    #   引数: [
    #     low: 期間等の整数乱数として返す下限値（int）
    #     _high: 実randintと呼び出しを合わせる未使用の上限（int）
    #   ]
    #   戻り値: [result: 指定下限lowと同じ整数（int）]
    # }
    @staticmethod
    def randint(low: int, _high: int) -> int:
        return low

    # {
    #   責務: [shuffle: テストの行動順を再現するため渡された一覧を並べ替えません]
    #   処理: [1: 一覧を変更せず返ります]
    #   引数: [_items: 並べ替えず保持する行動者等の一覧（list）]
    #   戻り値: [result: なし（None）]
    # }
    @staticmethod
    def shuffle(_items: list) -> None:
        return None


# {
#   責務: [make_combatant: 保存を使わず最大HP100/MP20と指定状態耐性の比較用個体を作ります]
#   処理: [1: 仮の個体記録・能力値・指定耐性から独立したCombatantを作ります]
#   引数: [
#     name: 比較個体のIDと表示名に使う名前（str）
#     status_resistances: 状態IDごとの付与耐性。省略時は空辞書です（dict[str, str] | None）
#   ]
#   戻り値: [result: 現在HP100/MP20・空スキル/状態一覧の比較用個体（Combatant）]
# }
def make_combatant(
    name: str,
    *,
    status_resistances: dict[str, str] | None = None,
) -> Combatant:
    # 実セーブや正規種族を使わず、出血の能力値変化を固定した独立個体で観測します。
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
#   責務: [make_engine: 実出血処理を呼ぶ比較用BattleEngineへ固定乱数と空ログを設定します]
#   処理: [1: 保存を使わず、出血/攻撃比較に必要なエンジン依存だけを用意します]
#   引数: []
#   戻り値: [result: 固定乱数と空ログを持つ比較用エンジン（BattleEngine）]
# }
def make_engine() -> BattleEngine:
    # 実出血処理は置換せず、乱数と種族読込だけを専用テスト依存へ固定します。
    engine = BattleEngine.__new__(BattleEngine)
    engine.rng = FixedRng()
    engine.log = []
    engine.data_loader = SimpleNamespace(species_definition=lambda _species_id: {})
    return engine


# {
#   責務: [BleedingStatusTests: 実出血の耐性補正・無効・重複防止・能力値低下/末尾ダメージと治療を確認します]
#   フィールド: []
# }
class BleedingStatusTests(unittest.TestCase):
    # {
    #   責務: [test_status_resistance_levels_scale_application_chance: 基礎確率0.4へ六段階の状態耐性倍率を適用した0.0〜0.6を照合します]
    #   処理: [1: 基礎確率0.4へ六段階の状態耐性倍率を適用した0.0〜0.6を照合します]
    #   引数: [self: 出血の期待動作を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_status_resistance_levels_scale_application_chance(self) -> None:
        # 基礎確率を共通の0.4にし、耐性による倍率だけを比較します。
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
    #   責務: [test_bleeding_immune_target_cannot_be_inflicted: 出血無効耐性の対象を攻撃しても出血が付かず、無効ログが出ることを確認します]
    #   処理: [1: 出血無効耐性の対象を攻撃しても出血が付かず、無効ログが出ることを確認します]
    #   引数: [self: 出血の期待動作を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_bleeding_immune_target_cannot_be_inflicted(self) -> None:
        # 攻撃のダメージ処理を実行し、出血無効と無効ログを観測します。
        engine = make_engine()
        actor = make_combatant("actor")
        target = make_combatant("target", status_resistances={"bleeding": "immune"})

        engine._attack(actor, target, BLEEDING_ATTACK)

        self.assertFalse(has_status(target.status_effects, "bleeding"))
        self.assertTrue(any("出血が効かなかった" in line for line in engine.log))

    # {
    #   責務: [test_bleeding_reduces_speed_and_defense_and_deals_small_turn_damage: 出血後の速度36/防御45と最大HP100に対する終了時ダメージ2を確認します]
    #   処理: [1: 出血後の速度36/防御45と最大HP100に対する終了時ダメージ2を確認します]
    #   引数: [self: 出血の期待動作を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_bleeding_reduces_speed_and_defense_and_deals_small_turn_damage(self) -> None:
        # 同じ個体で付与直後の能力値とターン終了時HP減少を確認します。
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
    #   責務: [test_bleeding_does_not_stack_and_cure_restores_stats: 出血の二回目付与が重ならず、治療後に速度40/防御50へ戻ることを確認します]
    #   処理: [1: 出血の二回目付与が重ならず、治療後に速度40/防御50へ戻ることを確認します]
    #   引数: [self: 出血の期待動作を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_bleeding_does_not_stack_and_cure_restores_stats(self) -> None:
        # 付与二回と実治療を連続実行し、重複なしと基礎能力値への回復を照合します。
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
