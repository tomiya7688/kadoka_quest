"""実Pythonと実Godotで、状態補正済み順序と非破壊の拒否境界を照合します。"""
# {
#   責務: [test_gdscript_status_turn_order: 安定順序・最新状態・陣営分離・不正入力と返却値の独立性を検査します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import itertools
import random
import unittest

import status_turn_order_fixture as fixture
import test_gdscript_roster as godot
import test_gdscript_status_cure as cure
import test_gdscript_turn_order as turn


# {
#   責務: [StatusTurnBoundaryTests: 状態補正済み順序をI/O・UI・乱数生成・資源更新・Sessionから分離します]
#   フィールド: []
# }
class StatusTurnBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_pure_contract_reuses_stats_and_order_without_session_connection: 補正式と安定ソートを共用し、実戦闘への接続や状態所有を追加しないことを確認します]
    #   処理: [1: 新契約の依存とSession/Application/UIによる未使用を静的に確認します]
    #   引数: [self: 純粋計算の依存境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_pure_contract_reuses_stats_and_order_without_session_connection(self):
        # 数値処理の複製や未実装のSession接続が、純粋な順序計算へ混入していないか確認します。
        source = (godot.ROOT / "gdscript/engine/status_turn_order.gd").read_text(encoding="utf-8")
        self.assertIn("Stats.quote_stats(", source)
        self.assertIn("Order.plan(", source)
        for forbidden in ("FileAccess", "DirAccess", "OS.", "randf(", "randi(", "RandomNumberGenerator", "Input.",
                          "res://data/", "res://ui/", "res://application/", "battle_session", "sort_custom(",
                          ".pay_mp(", ".take_damage(", ".learn(", "0.9"):
            self.assertNotIn(forbidden, source)
        for relative in ("engine/battle_session.gd", "application/battle_session_application.gd"):
            self.assertNotIn("status_turn_order", (godot.ROOT / "gdscript" / relative).read_text(encoding="utf-8"))


# {
#   責務: [StatusTurnOrderTests: 専用保存ダミーを所有し、状態付き行動順の実Godot観測を実Pythonと比較します]
#   フィールド: [
#     folder: 共用fixtureが用意する要求JSONの専用一時領域（Path）
#     saved_files: byte不変を毎起動後に確認する個体/AI/items/party/stateダミー（list）
#   ]
# }
@unittest.skipUnless(godot.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real status turn-order probes")
class StatusTurnOrderTests(unittest.TestCase):
    setUp = cure.StatusCureQuoteTests.setUp

    # {
    #   責務: [observe: 共用の隔離Godot起動へ状態順序のケース一覧を渡し、入力/保存byteの保持を確認します]
    #   処理: [1: 専用区分を付けて実プローブを呼び、全ケースの参照独立性も確認します]
    #   引数: [
    #     self: 専用要求領域と保存ダミーを持つテストケース
    #     cases: requestと任意native注入条件を持つケース列（list）
    #   ]
    #   戻り値: [result: 診断なし・原本保持・返却独立を確認した観測列（list）]
    # }
    def observe(self, cases):
        # 正常値だけでなく拒否結果も原本と返却値を分離することを、各実起動の観測で確認します。
        observations = cure.StatusCureQuoteTests.run_probe(self, {"status_turn_order": True, "cases": cases})["results"]
        self.assertEqual(len(observations), len(cases))
        for observed in observations:
            self.assertTrue(observed["input_preserved"])
            self.assertTrue(observed["result_independent"])
            self.assertTrue(observed["lists_independent"])
        return observations

    # {
    #   責務: [test_all_shuffle_permutations_match_actual_python_status_speed_sort: 出血・重複・未知状態と端数倍率で実Pythonの安定ソートを再現します]
    #   処理: [1: 四体の全24明示順と六状態条件を比較し、両陣営の同IDと同速の指定順保持を確認します]
    #   引数: [self: 実装間の順序一致を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_all_shuffle_permutations_match_actual_python_status_speed_sort(self):
        # 四体の全順列で比較し、特定のIDや入力枠順に依存した同速整列を見逃さないようにします。
        cases = []
        decks = ([], ["bleeding"], ["bleeding", {"id": "bleeding", "removable": False}],
                 [" bleeding ", "Bleeding"], ["poison", "sleep"], [{"id": "mod", "metadata": {"kept": [1, True]}}])
        for deck in decks:
            request = fixture.request([turn.member("shared", 3), turn.member("a", 4)],
                                      [turn.member("shared", 3), turn.member("e", 4)])
            request["statuses"]["allies"]["shared"] = copy.deepcopy(deck)
            request["statuses"]["enemies"]["e"] = copy.deepcopy(deck)
            request["speed_multipliers"]["allies"]["shared"] = 1.5
            for order in itertools.permutations(request["shuffle_order"]):
                case = copy.deepcopy(request)
                case["shuffle_order"] = list(order)
                cases.append({"request": case})
        for case, observed in zip(cases, self.observe(cases)):
            with self.subTest(request=case["request"]):
                self.assertEqual(observed["result"], {"ok": True, "scope": "status_turn_order",
                                                     **fixture.python_result(case["request"])})

    # {
    #   責務: [test_eight_actor_mixed_liveness_and_empty_teams_match_python: 最大八体・片側空・全員死亡/逃走で生存候補だけを順序へ含めます]
    #   処理: [1: 固定seedの混在ケースと空陣営を実Pythonへ照合し、死亡/逃走者の速度も独立して返すことを確認します]
    #   引数: [self: 生存と補正の組合せを検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_eight_actor_mixed_liveness_and_empty_teams_match_python(self):
        # 再現可能な混在ケースで、速度補正と生存者の抽出を同時に照合します。
        generator = random.Random(120)
        cases = [fixture.request([], []), fixture.request([], [turn.member("e")]),
                 fixture.request([turn.member("a")], []),
                 fixture.request([turn.member("a", hp=0)], [turn.member("e", fled=True)])]
        for _ in range(80):
            teams = [[turn.member(f"member_{slot}", generator.choice((0, 1, 3, 11, 41, 2**53 - 1)),
                                  hp=generator.choice((0, 1, 30)), fled=generator.choice((False, False, True)))
                      for slot in range(4)] for _ in range(2)]
            request = fixture.request(*teams)
            for side in ("allies", "enemies"):
                for member in request[side]:
                    identifier = member["identity"]["id"]
                    request["statuses"][side][identifier] = generator.choice(([], ["bleeding"], ["poison", "bleeding"]))
                    request["speed_multipliers"][side][identifier] = generator.choice((0, 0.1, 0.5, 1, 1e-300))
            generator.shuffle(request["shuffle_order"])
            cases.append(request)
        for request, observed in zip(cases, self.observe([{"request": request} for request in cases])):
            with self.subTest(request=request):
                self.assertEqual(observed["result"], {"ok": True, "scope": "status_turn_order", **fixture.python_result(request)})

    # {
    #   責務: [test_latest_status_multiplier_and_base_speed_are_recomputed_without_double_adjustment: 出血解除・倍率変更・基礎値変更を再入力した順序をキャッシュせず計算します]
    #   処理: [1: 補正前11対10の速度から順序が逆転/復帰する連続ケースと倍率0の下限を固定値へ照合します]
    #   引数: [self: 最新入力と整数化境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_latest_status_multiplier_and_base_speed_are_recomputed_without_double_adjustment(self):
        # 同一の補正前資源へ変更後の状態を渡し、過去の補正値を保持してしまう実装を検出します。
        request = fixture.request([turn.member("ally", 11)], [turn.member("enemy", 10)])
        cases = [copy.deepcopy(request)]
        request["statuses"]["allies"]["ally"] = ["bleeding"]
        cases.append(copy.deepcopy(request))
        request["speed_multipliers"]["allies"]["ally"] = 1.5
        cases.append(copy.deepcopy(request))
        request["statuses"]["allies"]["ally"] = []
        cases.append(copy.deepcopy(request))
        request["allies"][0]["stats"]["speed"] = 0.0
        request["speed_multipliers"]["allies"]["ally"] = 0
        cases.append(request)
        observed = self.observe([{"request": entry} for entry in cases])
        for result, speed, first in zip(observed, (11, 9, 14, 16, 1), ("ally", "enemy", "ally", "ally", "enemy")):
            self.assertEqual(result["result"]["speeds"]["allies"]["ally"], speed)
            self.assertEqual(result["result"]["order"][0]["id"], first)
        # 同じ補正前入力の再送が0.9を再累積しないことも確認します。
        self.assertEqual(self.observe([{"request": cases[1]}])[0]["result"], observed[1]["result"])

    # {
    #   責務: [test_invalid_request_snapshots_maps_and_shuffle_return_no_partial_plan: 要求・参加者・対応辞書・明示順の不正を暗黙補完せず拒否します]
    #   処理: [1: 欠損/未知キー/型/上限/重複/不整合を渡し、順序や速度の部分結果が出ないことを確認します]
    #   引数: [self: 厳密入力契約を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_request_snapshots_maps_and_shuffle_return_no_partial_plan(self):
        # 不正な層を一つずつ作り、正常な参加者だけの部分計画で成功を装わないことを確認します。
        cases = [None, [], 1, "invalid", {}]
        base = fixture.request()
        for field in base:
            request = copy.deepcopy(base)
            request.pop(field)
            cases.append(request)
        for field in ("effective_speed", "guard", "result"):
            cases.append({**copy.deepcopy(base), field: False})
        for field in ("allies", "enemies", "shuffle_order"):
            for value in (None, {}, "invalid", True):
                cases.append({**copy.deepcopy(base), field: value})
        for value in ([turn.member("ally"), turn.member("ally")], [turn.member(str(i)) for i in range(5)]):
            cases.append({**copy.deepcopy(base), "allies": value})
        for field, value in (("alive", False), ("hp", -1), ("mp", True), ("fled", 0), ("identity", None),
                             ("stats", {}), ("status_effects", []), ("speed_multiplier", 1)):
            request = copy.deepcopy(base)
            request["allies"][0][field] = value
            cases.append(request)
        for stat, value in itertools.product(base["allies"][0]["stats"], (None, True, -1, 0.5, "1", 2**53)):
            request = copy.deepcopy(base)
            request["allies"][0]["stats"][stat] = value
            cases.append(request)
        for field in ("statuses", "speed_multipliers"):
            for value in (None, [], {}, {"allies": {}, "enemies": {}, "other": {}},
                          {"allies": [], "enemies": {}}, {"allies": {}, "enemies": {"enemy": []}},
                          {"allies": {"unknown": []}, "enemies": {"enemy": []}}):
                cases.append({**copy.deepcopy(base), field: value})
        for order in ([], [turn.key("allies", "ally")] * 2,
                      [turn.key("allies", "missing"), turn.key("enemies", "enemy")],
                      [{"side": "other", "id": "ally"}, turn.key("enemies", "enemy")],
                      [{"side": "allies", "id": "ally", "extra": False}, turn.key("enemies", "enemy")]):
            cases.append({**copy.deepcopy(base), "shuffle_order": order})
        for observed in self.observe([{"request": request} for request in cases]):
            self.assertFalse(observed["result"]["ok"])
            self.assertTrue("reason" in observed["result"])
            self.assertFalse(set(observed["result"]) & {"initial", "order", "speeds", "scope"})

    # {
    #   責務: [test_invalid_statuses_and_multipliers_include_dead_and_fled_actors: 死亡/逃走個体の不正一覧や倍率も拒否し、出血後の上限内への縮小で途中精度超過を隠しません]
    #   処理: [1: 非対象個体も含めた状態全体検証と倍率/途中積の数値制限を確認します]
    #   引数: [self: 補正前検証と失敗対象の陣営/IDを検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_statuses_and_multipliers_include_dead_and_fled_actors(self):
        # 順序に含まれない個体でも検証を省かず、無効な状態や倍率を次回へ持ち越さないようにします。
        cases = []
        for hp, fled in ((30, False), (0, False), (30, True)):
            for field, values in (("statuses", (None, {}, [1], [True], [[]], ["bleeding", {"id": 1}], [{"removable": 0}])),
                                  ("speed_multipliers", (None, True, "1", -0.1, 2**53, {}, []))):
                for value in values:
                    request = fixture.request([turn.member("ally", hp=hp, fled=fled)])
                    request[field]["allies"]["ally"] = value
                    cases.append(request)
        overflow = fixture.request([turn.member("ally", 2**53 - 1)])
        overflow["statuses"]["allies"]["ally"] = ["bleeding"]
        overflow["speed_multipliers"]["allies"]["ally"] = 1.01
        cases.append(overflow)
        for observed in self.observe([{"request": request} for request in cases]):
            result = observed["result"]
            self.assertFalse(result["ok"])
            self.assertEqual((result["side"], result["id"]), ("allies", "ally"))
            self.assertEqual(set(result), {"ok", "reason", "side", "id"})

    # {
    #   責務: [test_native_non_json_inputs_and_status_depth_are_rejected_before_copy: 非有限値/Object/循環/非文字列キーと深さ33を部分結果なしで拒否します]
    #   処理: [1: 専用プローブでnative値を注入し、深さ32の正常一覧だけは実Pythonにも照合します]
    #   引数: [self: JSON外と深さ上限を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_native_non_json_inputs_and_status_depth_are_rejected_before_copy(self):
        # JSONファイルでは表せない値はプローブ内へ注入し、APIの型境界を直接確認します。
        cases = []
        paths = [["speed_multipliers", "allies", "ally"], ["allies", 0, "stats", "speed"],
                 ["statuses", "allies", "ally", 1, "metadata"]]
        for path, value in itertools.product(paths, ("nan", "inf", "object", "cycle")):
            request = fixture.request()
            request["statuses"]["allies"]["ally"] = ["bleeding", {"id": "mod"}]
            cases.append({"request": request, "special": {"path": path, "value": value}})
        for path in (["unused"], ["statuses", "unused"], ["speed_multipliers", "allies", "unused"],
                     ["statuses", "allies", "ally", 1, "unused"]):
            request = fixture.request()
            request["statuses"]["allies"]["ally"] = ["bleeding", {"id": "mod"}]
            cases.append({"request": request, "special": {"path": path, "value": "non_string_key"}})
        for observed in self.observe(cases):
            self.assertFalse(observed["result"]["ok"])
            self.assertFalse(set(observed["result"]) & {"order", "initial", "speeds"})
        for container in (list, dict):
            nested = "leaf"
            for _ in range(30):
                nested = [nested] if container is list else {"child": nested}
            valid = fixture.request()
            valid["statuses"]["allies"]["ally"] = [{"id": "bleeding", "metadata": nested}]
            invalid = copy.deepcopy(valid)
            invalid["statuses"]["allies"]["ally"][0]["metadata"] = [nested] if container is list else {"child": nested}
            observed = self.observe([{"request": valid}, {"request": invalid}])
            self.assertEqual(observed[0]["result"], {"ok": True, "scope": "status_turn_order", **fixture.python_result(valid)})
            self.assertEqual(observed[1]["result"], {"ok": False, "reason": "invalid_status_effects", "side": "allies", "id": "ally"})
