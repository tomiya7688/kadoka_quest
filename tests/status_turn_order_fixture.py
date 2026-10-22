"""状態補正済み順序の要求と、実Pythonの速度ソートだけを観測する比較fixtureです。"""
# {
#   責務: [status_turn_order_fixture: 個体/AIを保存しない比較用の要求生成とPython順序観測を提供します]
#   フィールド: []
# }
from __future__ import annotations

import copy
from unittest import mock

import test_gdscript_turn_order as turn
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.combatant import Combatant
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [request: 数値snapshotと状態/一時倍率を分離した五キーの独立要求を作ります]
#   処理: [1: 両陣営を複製し、全員の空状態/倍率1と生存者の初期順を設定します]
#   引数: [
#     allies: 任意の味方snapshot列。Noneならally一体です（listまたはNone）
#     enemies: 任意の敵snapshot列。Noneならenemy一体です（listまたはNone）
#   ]
#   戻り値: [result: 両陣営/全状態/全倍率/明示順を持つ辞書（dict）]
# }
def request(allies=None, enemies=None):
    # 呼出元や別ケースの配列へ、状態や倍率の変更を伝播させないため専用の要求を作ります。
    allies = copy.deepcopy([turn.member("ally")] if allies is None else allies)
    enemies = copy.deepcopy([turn.member("enemy")] if enemies is None else enemies)
    result = {"allies": allies, "enemies": enemies, "statuses": {}, "speed_multipliers": {},
              "shuffle_order": turn.participants(allies, enemies)}
    for side in ("allies", "enemies"):
        result["statuses"][side] = {member["identity"]["id"]: [] for member in result[side]}
        result["speed_multipliers"][side] = {member["identity"]["id"]: 1.0 for member in result[side]}
    return result


# {
#   責務: [python_result: 実Python Combatant.speedとrun_roundの安定ソートから比較用の速度と順序を取得します]
#   処理: [
#     1: 独立した個体/AIと明示状態/倍率を設定し、保存しない比較戦闘を作ります
#     2: shuffle順だけを明示入力に置き換え、行動/勝敗/継続効果/期限を止めたrun_roundのソート列を観測します
#   ]
#   引数: [parameters: 全て正常な五キーの行動順要求（dict）]
#   戻り値: [result: 実Pythonによるinitial/order/speeds。要求・保有個体/AIを変更しません（dict）]
# }
def python_result(parameters):
    original = copy.deepcopy(parameters)
    # 参照計算は正規dataを読み取るだけで、利用者のセーブやAI学習先を持ちません。
    engine = BattleEngine(GameRepository(turn.ROOT / "data"), [], [], learning_enabled=False)
    speeds = {"allies": {}, "enemies": {}}
    keys_by_object = {}
    for side in ("allies", "enemies"):
        team = []
        for snapshot in parameters[side]:
            identifier = snapshot["identity"]["id"]
            actor = Combatant(MonsterRecord(copy.deepcopy(snapshot["identity"]), {"kept": [1, {"ai": True}]}),
                              copy.deepcopy(snapshot["stats"]), [], {})
            actor.hp, actor.mp, actor.fled = snapshot["hp"], snapshot["mp"], snapshot["fled"]
            actor.status_effects = copy.deepcopy(parameters["statuses"][side][identifier])
            actor.speed_multiplier = parameters["speed_multipliers"][side][identifier]
            team.append(actor)
            keys_by_object[id(actor)] = turn.key(side, identifier)
            speeds[side][identifier] = actor.speed
        setattr(engine, side, team)
    records_before = [copy.deepcopy(actor.record) for actor in engine.allies + engine.enemies]
    captured = {}

    # {
    #   責務: [shuffle: 実Pythonの生存候補を指定順へ並べ替え、ソート対象の配列参照を保持します]
    #   処理: [1: 初期順を記録し、陣営/IDで指定したshuffle順へ同じ配列を並べ替えます]
    #   引数: [actors: run_roundが作った生存個体と敵/味方列の組の配列（list）]
    #   戻り値: [result: なし（None）。参照戦闘の専用配列と観測値だけを変更します]
    # }
    def shuffle(actors):
        # Python本体のソートを置き換えず、ソート前の配列だけを明示順へ揃えます。
        captured["initial"] = [keys_by_object[id(actor)] for actor, _, _ in actors]
        by_key = {(keys_by_object[id(entry[0])]["side"], keys_by_object[id(entry[0])]["id"]): entry for entry in actors}
        actors[:] = [by_key[(key["side"], key["id"])] for key in parameters["shuffle_order"]]
        captured["actors"] = actors

    engine.rng = mock.Mock()
    engine.rng.shuffle.side_effect = shuffle
    # ソートだけの比較で、未移植の行動・継続ダメージ・勝敗・倍率期限が成功したとは扱いません。
    with mock.patch.multiple(engine, _take_action=mock.Mock(), _check_end=mock.Mock(),
                             _tick_end_turn_status=mock.Mock(), _tick_timed_buffs=mock.Mock()):
        engine.run_round()
    engine.rng.shuffle.assert_called_once()
    assert parameters == original
    assert records_before == [actor.record for actor in engine.allies + engine.enemies]
    return {"initial": captured["initial"],
            "order": [keys_by_object[id(actor)] for actor, _, _ in captured["actors"]], "speeds": speeds}
