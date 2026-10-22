"""Session終端の速度期間経過を実Godotで観測し、Python正本の復元規則と照合します。"""
# {
#   責務: [test_gdscript_speed_round: 通常終了・途中停止・末尾スキップの一回経過と、拒否/読取の非変更を検証します]
#   フィールド: []
# }
from __future__ import annotations
import copy
import unittest

import test_gdscript_claimed_speed as claimed
import test_gdscript_session_speed as joined
import test_gdscript_speed_state as speed
import test_gdscript_status_cure as fixture

ACTOR, ENEMY = claimed.ACTOR, claimed.ENEMY
ORDER = [ACTOR, ENEMY]


# {
#   責務: [SpeedRoundBoundaryTests: 速度期間の数式をSessionへ複写せず、終端から集合へだけ委譲する境界を確認します]
#   フィールド: []
# }
class SpeedRoundBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_expiration_stays_in_owners_and_session_has_no_public_tick: Session終端の一か所だけが集合の経過APIを呼ぶことを確認します]
    #   処理: [1: 個体所有者への委譲・一回段階ガード・I/O分離と上位の生経過APIの未追加を静的照合します]
    #   引数: [self: 速度経過の責務境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_expiration_stays_in_owners_and_session_has_no_public_tick(self):
        root = fixture.godot_fixture.ROOT / "gdscript"
        collection = (root / "engine/battle_speed_state.gd").read_text(encoding="utf-8")
        session = (root / "engine/battle_session.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "randf(", "randi(", "res://data/", "res://ui/", "remaining_turns -="):
            self.assertNotIn(forbidden, collection)
        self.assertIn('_by_id[side][id].elapse_round()', collection)
        terminal = session.split("func _end_round(", 1)[1].split("\nfunc ", 1)[0]
        self.assertLess(terminal.index('_phase != "round_active"'), terminal.index("_speeds.elapse_round()"))
        self.assertEqual(session.count("_speeds.elapse_round()"), 1)
        for relative in ("engine/battle_session.gd", "application/battle_session_application.gd"):
            self.assertNotIn("func elapse_round(", (root / relative).read_text(encoding="utf-8"))


# {
#   責務: [SpeedRoundTests: 隔離した要求と保存ダミーを所有し、実Godotの速度終端とPython倍率ヘルパーを比較します]
#   フィールド: [
#     folder: 実セーブと分離した要求領域（Path）
#     saved_files: 個体/AI/items/party/stateの不変を確認する保存ダミー（list）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for speed round expiration")
class SpeedRoundTests(unittest.TestCase):
    setUp = fixture.StatusCureQuoteTests.setUp
    run_probe = speed.SpeedStateTests.run_probe
    observe = joined.SessionSpeedTests.observe

    # {
    #   責務: [test_collection_ticks_all_eight_independent_owners_like_python: 集合経過は両陣営の八体を各一回進め、期限切れをPython正本へ照合します]
    #   処理: [1: 各個体へ異なる期間を付与し、四回の経過の全中間状態を実Pythonヘルパーと比較します]
    #   引数: [self: 参加者集合の経過を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_collection_ticks_all_eight_independent_owners_like_python(self):
        case = claimed.rounds.roster.roster_case([], count=4)
        case["mode"] = "collection"
        requests = [(claimed.rounds.normal.key(side, f"same_{index}"),
                     {"multiplier": 1.5, "duration": index % 3 + 1})
                    for side in ("allies", "enemies") for index in range(4)]
        case["steps"] = [claimed.apply_step(key, request) for key, request in requests]
        case["steps"] += [{"operation": "elapse"} for _ in range(4)]
        observed = self.observe([case])[0]
        for elapsed in range(1, 5):
            step = observed["steps"][7 + elapsed]
            self.assertEqual(step["result"], {"ok": True, "scope": "battle_speed_elapsed"})
            for key, request in requests:
                expected = speed.python_trace([{"method": "start"}, {"method": "apply", "value": request}]
                                              + [{"method": "elapse"}] * elapsed)[-1]
                self.assertEqual(step["state"]["speeds"]["teams"][key["side"]][key["id"]], expected)

    # {
    #   責務: [test_unstarted_and_empty_collections_preserve_contracts: 集合の未開始経過を拒否し、空集合の経過は安全な成功にします]
    #   処理: [1: 未開始と両陣営空のケースで、経過結果と空の所有状態を照合します]
    #   引数: [self: 開始段階と空集合を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_unstarted_and_empty_collections_preserve_contracts(self):
        missing = claimed.claimed_case(mode="collection", no_start=True, steps=[{"operation": "elapse"}])
        empty = claimed.claimed_case(mode="collection", snapshots={"allies": [], "enemies": []},
                                     initial_speed_multipliers=None, steps=[{"operation": "elapse"}] * 3)
        left, right = self.observe([missing, empty])
        self.assertEqual(left["steps"][0]["result"], {"ok": False, "reason": "not_initialized"})
        self.assertTrue(left["steps"][0]["unchanged"])
        self.assertTrue(all(step["result"]["ok"] and step["unchanged"] for step in right["steps"]))

    # {
    #   責務: [test_normal_finish_ticks_once_even_for_last_action_and_replays: 付与した行動位置に関係なく正常終端で一回だけ期間を減らします]
    #   処理: [1: 先頭/末尾から本人/他陣営へ期間を付与し、終端後の再送・読取・不正開始で再減算しないことを照合します]
    #   引数: [self: 正常終了と再送の一回性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_normal_finish_ticks_once_even_for_last_action_and_replays(self):
        cases, checks = [], []
        for duration in (1, 2, 5):
            for target in ORDER:
                for late in (False, True):
                    case = claimed.claimed_case()
                    if late:
                        case["steps"] += [{"operation": "finish"}, {"operation": "next"}, {"operation": "claim"}]
                    case["steps"].append(claimed.apply_step(target, {"multiplier": 1.5, "duration": duration}))
                    applied_index = len(case["steps"]) - 1
                    case["steps"] += [{"operation": "finish"}] + ([] if late else claimed.rounds.complete_round(1))
                    ended_index = len(case["steps"]) - 1
                    # 終端後の公開操作だけを再送し、非公開段階を書き換えて一回性を偽装しません。
                    case["steps"] += [{"operation": "finish", "ticket": {"round": 1, "slot": 1, "actor": ENEMY}},
                                      {"operation": "next"}, {"operation": "next"}, {"operation": "begin", "order": [ACTOR]}]
                    cases.append(case)
                    checks.append((target, duration, applied_index, ended_index))
        for case, observed, (target, duration, applied, ended) in zip(cases, self.observe(cases), checks):
            expected = speed.python_trace([{"method": "start", "value": 1.2},
                {"method": "apply", "value": {"multiplier": 1.5, "duration": duration}}, {"method": "elapse"}])
            self.assertEqual(observed["steps"][applied]["state"]["speeds"]["teams"][target["side"]][target["id"]], expected[1])
            for step in observed["steps"][applied:ended]:
                self.assertEqual(step["state"]["speeds"]["teams"][target["side"]][target["id"]], expected[1])
            end = observed["steps"][ended]["state"]
            self.assertEqual(end["numeric"]["phase"], "round_finished")
            self.assertEqual(end["speeds"]["teams"][target["side"]][target["id"]], expected[2])
            self.assertEqual(end["numeric"]["teams"], case["snapshots"])
            self.assertEqual(end["statuses"]["teams"], case["initial_statuses"])
            self.assertTrue(all(step["unchanged"] for step in observed["steps"][ended + 1:]))

    # {
    #   責務: [test_expiration_changes_only_the_following_round_order: 残り一期間の強化が終端で切れ、次のラウンドは復元倍率で整列します]
    #   処理: [1: 期間二の敵強化を二ラウンド完了し、途中順固定・次回加速・期限後復元を照合します]
    #   引数: [self: 順序と期間境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_expiration_changes_only_the_following_round_order(self):
        case = claimed.claimed_case()
        case["steps"] += [claimed.apply_step(ENEMY, {"multiplier": 1.5, "duration": 2}),
                          {"operation": "finish"}, *claimed.rounds.complete_round(1),
                          {"operation": "begin", "order": ORDER}, *claimed.rounds.complete_round(2),
                          {"operation": "begin", "order": ORDER}]
        observed = self.observe([case])[0]
        self.assertEqual(observed["steps"][3]["state"]["numeric"]["order"], ORDER)
        self.assertEqual(observed["steps"][7]["state"]["speeds"]["teams"]["enemies"]["same"]["remaining_turns"], 1)
        self.assertEqual(observed["steps"][8]["result"]["plan"]["order"], [ENEMY, ACTOR])
        self.assertEqual(observed["steps"][14]["state"]["speeds"]["teams"]["enemies"]["same"],
                         {"speed_multiplier": 1.2, "remaining_turns": 0, "baseline_multiplier": 1.2})
        self.assertEqual(observed["steps"][15]["result"]["plan"]["order"], ORDER)
        self.assertEqual(observed["state"]["numeric"]["teams"], case["snapshots"])

    # {
    #   責務: [test_all_stop_paths_tick_dead_and_fled_targets_once: 完了・次候補・取得取消の途中停止は死亡/逃走対象の期間も一回進めます]
    #   処理: [1: 両陣営の死亡/逃走を三つの公開経路で作り、資源保持・防御解除と再停止の非変更を照合します]
    #   引数: [self: 途中停止と全所有者経過を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_all_stop_paths_tick_dead_and_fled_targets_once(self):
        cases, checks = [], []
        for target in ORDER:
            for operation in ("damage", "flee"):
                for route in ("finish", "next", "claim"):
                    case = claimed.claimed_case()
                    case["steps"] += [claimed.apply_step(target, {"multiplier": 1.5, "duration": 2}),
                                      {"operation": "defend", "value": 0.5}]
                    if route != "finish":
                        case["steps"].append({"operation": "finish"})
                    if route == "claim":
                        case["steps"].append({"operation": "next"})
                    case["steps"] += [{"operation": operation, "actor": target, "value": 999}, {"operation": route}]
                    ended = len(case["steps"]) - 1
                    case["steps"] += [{"operation": "next"}, {"operation": "next"},
                                      {"operation": "begin", "order": ORDER}]
                    cases.append(case)
                    checks.append((target, ended))
        for observed, (target, ended) in zip(self.observe(cases), checks):
            before, after = observed["steps"][ended - 1]["state"], observed["steps"][ended]["state"]
            self.assertEqual(after["numeric"]["phase"], "stopped")
            self.assertEqual(after["numeric"]["teams"], before["numeric"]["teams"])
            self.assertEqual(after["statuses"], before["statuses"])
            self.assertEqual(after["speeds"]["teams"][target["side"]][target["id"]],
                             {"speed_multiplier": 1.5, "remaining_turns": 1, "baseline_multiplier": 1.2})
            self.assertEqual(after["guards"]["teams"]["allies"]["same"], 1)
            self.assertTrue(all(step["unchanged"] for step in observed["steps"][ended + 1:]))

    # {
    #   責務: [test_skipped_dead_tail_closes_once_on_next_actor_not_previous_finish: 死亡した末尾候補を飛ばした時点だけで速度期間を進めます]
    #   処理: [1: 生存する最後の行動完了と死亡末尾のスキップを分け、減算前後と再送保持を照合します]
    #   引数: [self: カーソル末尾と死亡個体の期間を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_skipped_dead_tail_closes_once_on_next_actor_not_previous_finish(self):
        case = claimed.claimed_case()
        tail = copy.deepcopy(case["snapshots"]["allies"][0])
        tail["identity"]["id"], tail["stats"]["speed"] = "tail", 1
        key = {"side": "allies", "id": "tail"}
        case["snapshots"]["allies"].append(tail)
        case["initial_statuses"]["allies"]["tail"] = ["mod_unknown"]
        case["initial_speed_multipliers"]["allies"]["tail"] = 0.75
        case["steps"][0]["order"] = [ACTOR, ENEMY, key]
        case["steps"] += [claimed.apply_step(key, {"multiplier": 1.5, "duration": 1}),
                          {"operation": "damage", "actor": key, "value": 999},
                          {"operation": "finish"}, *claimed.rounds.complete_round(1),
                          {"operation": "next"}, {"operation": "next"}]
        observed = self.observe([case])[0]
        before, after = observed["steps"][8]["state"], observed["steps"][9]["state"]
        self.assertEqual(before["numeric"]["phase"], "round_active")
        self.assertEqual(before["speeds"]["teams"]["allies"]["tail"]["remaining_turns"], 1)
        self.assertEqual(after["numeric"]["phase"], "round_finished")
        self.assertEqual(observed["steps"][9]["result"]["skipped"], [key])
        self.assertEqual(after["speeds"]["teams"]["allies"]["tail"],
                         {"speed_multiplier": 0.75, "remaining_turns": 0, "baseline_multiplier": 0.75})
        self.assertEqual(after["numeric"]["teams"], before["numeric"]["teams"])
        self.assertTrue(observed["steps"][10]["unchanged"])

    # {
    #   責務: [test_reapplication_and_permanent_baseline_survive_terminal_ticks: 弱い延長と期間なし再付与の復元先を、複数終端にわたりPythonへ照合します]
    #   処理: [1: 強化・弱い延長・期間なし強化を別予約で実行し、最終期限切れと各終端の残り期間を確認します]
    #   引数: [self: 再付与と期間経過の組合せを検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_reapplication_and_permanent_baseline_survive_terminal_ticks(self):
        case, ends, operations = claimed.claimed_case(), [], [{"method": "start", "value": 1.2}]
        requests = [{"multiplier": 1.5, "duration": 2}, {"multiplier": 1.3, "duration": 3}, {"multiplier": 1.4}]
        for index, request in enumerate(requests):
            if index:
                case["steps"] += [{"operation": "begin", "order": ORDER}, {"operation": "next"}, {"operation": "claim"}]
            case["steps"] += [claimed.apply_step(ENEMY, request), {"operation": "finish"}, *claimed.rounds.complete_round(1)]
            ends.append(len(case["steps"]) - 1)
            operations += [{"method": "apply", "value": request}, {"method": "elapse"}]
        case["steps"] += [{"operation": "begin", "order": ORDER}, *claimed.rounds.complete_round(2)]
        ends.append(len(case["steps"]) - 1)
        operations.append({"method": "elapse"})
        observed = self.observe([case])[0]
        self.assertEqual([observed["steps"][index]["state"]["speeds"]["teams"]["enemies"]["same"]["remaining_turns"]
                          for index in ends], [1, 2, 1, 0])
        self.assertEqual(observed["state"]["speeds"]["teams"]["enemies"]["same"], speed.python_trace(operations)[-1])
        self.assertEqual(observed["state"]["speeds"]["teams"]["enemies"]["same"]["speed_multiplier"], 1.4)

    # {
    #   責務: [test_rejected_nonterminal_operations_and_reads_never_tick: 不正要求・進行中の読取・予約再送では期間を減らしません]
    #   処理: [1: 取得済み予約へ不正/重複/読取操作を送り、最後の非終端完了を含む全速度保持を照合します]
    #   引数: [self: 終端以外の非変更を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_rejected_nonterminal_operations_and_reads_never_tick(self):
        case = claimed.claimed_case()
        case["steps"] += [claimed.apply_step(ENEMY), {"operation": "finish", "ticket": {}},
                          {"operation": "claim"}, {"operation": "begin", "order": ORDER},
                          {"operation": "next"}, {"operation": "speed", "actor": ENEMY},
                          {"operation": "speeds"}, {"operation": "elapse"},
                          claimed.apply_step(ENEMY, {"multiplier": False}), {"operation": "finish"}]
        observed = self.observe([case])[0]
        expected = observed["steps"][3]["state"]["speeds"]
        self.assertTrue(all(step["state"]["speeds"] == expected for step in observed["steps"][4:]))
        self.assertTrue(all(step["unchanged"] for step in observed["steps"][4:-1]))
        self.assertEqual(observed["state"]["numeric"]["phase"], "round_active")
