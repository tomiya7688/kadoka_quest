"""付与付き物理行動の検証に使う独立入力・実Godot起動・実Python比較を提供します。"""
# {
#   責務: [gdscript_status_action_fixture: 実セーブを使わない付与付き物理行動テストの共用入力と比較環境を提供します]
#   フィールド: []
# }
from __future__ import annotations

import copy
from unittest import mock

import test_gdscript_normal_attack_action as normal
import test_gdscript_status_cure as fixture
import test_gdscript_status_physical_context as context
import test_gdscript_turn_order as turn

ACTOR = normal.key("allies", "same")
TARGET = normal.key("enemies", "same")
TICKET = {"round": 1, "slot": 0, "actor": ACTOR}


# {
#   責務: [action: 物理と付与の判定値を明示した、独立した攻撃操作を作ります]
#   処理: [1: 敵対象と基準乱数を付け、ケースごとの上書きを適用します]
#   引数: [changes: 対象・乱数・専用要求等を上書きする辞書展開引数]
#   戻り値: [result: operation=actionの専用観測操作（dict）]
# }
def action(**changes):
    return copy.deepcopy({"operation": "action", "target": TARGET, "critical_roll": 0.5,
                          "variance": 1.0, "status_roll": 0.49, **changes})


# {
#   責務: [action_case: 同IDの両陣営へ独立資源と状態・習得/装備を持つ付与付き物理の開始要求を作ります]
#   処理: [1: 共用MOD入力の基礎数値を固定し、現在予約の提示と一回攻撃を操作列へ追加します]
#   引数: [changes: 開始情報や操作列を上書きする辞書展開引数]
#   戻り値: [result: 実Godotに渡す独立したケース（dict）]
# }
def action_case(**changes):
    case = context.context_case()
    for side in ("allies", "enemies"):
        snapshot = case["teams"][side][0]["snapshot"]
        snapshot["stats"].update(hp=1000, mp=50, attack=100, defense=50)
        snapshot.update(hp=1000, mp=50)
    return copy.deepcopy({**case, "order": [ACTOR, TARGET],
                          "steps": [{"operation": "next"}, action()], **changes})


# {
#   責務: [StatusActionFixture: 隔離要求/保存ダミー・正規JSONのbyte保持と実Python/Godotの行動比較を共用します]
#   フィールド: [
#     folder: 共用fixtureが作る専用要求/保存ダミー領域（Path）
#     saved_files: 個体/AI/items/party/stateの内容保持を確認する保存ダミー（list[Path]）
#     content: 読取専用の正規JSONを持つチェックアウト（Path）
#   ]
# }
class StatusActionFixture:
    check_canonical = context.StatusPhysicalContextTests.check_canonical

    # {
    #   責務: [setUp: 保存ダミーの隔離領域と正規JSONの開始/終了ハッシュ確認を設定します]
    #   処理: [1: 共用の状態付き物理fixtureへ一時領域と保持検査を委譲します]
    #   引数: [self: unittestと組み合わせる検証環境の所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        context.StatusPhysicalContextTests.setUp(self)

    # {
    #   責務: [observe: 実Godotへ行動区分を指定し、要求/保存byteと返却値編集後の正本保持を検査します]
    #   処理: [1: 専用コピー要求を実行し、各ケースと操作の非変更/独立性を確認します]
    #   引数: [
    #     self: 専用環境とunittestの検査を持つ所有者
    #     payload: ケース一覧または性能反復条件（dict）
    #   ]
    #   戻り値: [result: 診断なしと内容保持を確認済みの実Godot観測（dict）]
    # }
    def observe(self, payload):
        result = fixture.StatusCureQuoteTests.run_probe(self, {**copy.deepcopy(payload), "status_physical_action": True})
        for case in result.get("results", []):
            self.assertTrue(case["input_preserved"])
            self.assertTrue(all(step["independent"] and step["request_preserved"] for step in case["steps"]))
        return result

    # {
    #   責務: [python_action: AI選択と乱数だけを固定し、実PythonのMP消費・物理攻撃・状態付与を比較します]
    #   処理: [1: 独立個体を再構築し、実_take_action後の資源/状態と元レコード/AIの不変を確認します]
    #   引数: [
    #     self: 正規JSONを読取専用で参照する検証所有者
    #     case: 満資源・状態/耐性・MOD物理定義を持つ独立した開始条件（dict）
    #     roll: 会心判定値（float）
    #     variance: 物理ダメージの揺らぎ倍率（float）
    #     status_roll: 状態付与の明示判定値（float）
    #     guard: 対象に適用中の物理防御倍率（float）
    #   ]
    #   戻り値: [result: 実消費後MP・残HP・実ダメージ・最新状態と付与乱数要否（dict）]
    # }
    def python_action(self, case, roll=0.5, variance=1.0, status_roll=0.49, guard=1.0):
        source = copy.deepcopy(case)
        engine = turn.GDScriptTurnTests.engine(self, [source["teams"]["allies"][0]["snapshot"]],
                                             [source["teams"]["enemies"][0]["snapshot"]])
        actor, target = engine.allies[0], engine.enemies[0]
        skill = source["skills"]["skills"][0]
        actor.skills = [skill]
        actor.equipment = source["teams"]["allies"][0]["equipment"]
        actor.status_effects = source["initial_statuses"]["allies"]["same"]
        target.status_effects = source["initial_statuses"]["enemies"]["same"]
        target.status_resistances = source["teams"]["enemies"][0]["status_resistances"]
        target.guard = guard
        preserved = copy.deepcopy([actor.record, target.record, case])
        initial_hp = target.hp
        # MP消費と付与を予測式へ置き換えず、実行処理そのものを比較します。
        engine.inference.choose = mock.Mock(return_value=skill)
        engine.learning.learn = mock.Mock()
        engine.rng = mock.Mock()
        engine.rng.random.side_effect = [roll, status_roll]
        engine.rng.uniform.return_value = variance
        engine._take_action(actor, [target], [actor])
        engine.learning.learn.assert_not_called()
        self.assertEqual([actor.record, target.record, case], preserved)
        return {"remaining_mp": actor.mp, "remaining_hp": target.hp, "dealt": initial_hp - target.hp,
                "status_effects": target.status_effects, "roll_required": engine.rng.random.call_count == 2}
