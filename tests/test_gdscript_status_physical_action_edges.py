"""付与付き物理の不正要求・最新生存・二重実行・内部拒否を実Godotで確認します。"""
# {
#   責務: [test_gdscript_status_physical_action_edges: 予約前の非変更拒否、最新生存による取消と予約取得後の失敗を検証します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import itertools
import unittest

from gdscript_status_action_fixture import ACTOR, TARGET, TICKET, StatusActionFixture, action, action_case, fixture


# {
#   責務: [StatusPhysicalActionEdgeTests: 不正入力/不足の非変更、取消・再試行と内部失敗の順序を実Godotで検証します]
#   フィールド: [folder: 共用fixtureが所有する専用要求/保存ダミー領域（Path）]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for status physical action edges")
class StatusPhysicalActionEdgeTests(StatusActionFixture, unittest.TestCase):
    # {
    #   責務: [test_invalid_requests_and_rolls_do_not_consume_current_ticket: 欠損・未知キー・対象・乱数の不正を資源変更なしで拒否します]
    #   処理: [1: 不正ケースを現在offeredへ渡し、拒否後も予約/HPMP/状態/guardが同一であることを確認します]
    #   引数: [self: 予約取得前の拒否を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_requests_and_rolls_do_not_consume_current_ticket(self):
        cases = [action_case(steps=[{"operation": "next"}, action(request=request)]) for request in (None, [], {}, False)]
        required = {"ticket": TICKET, "target": TARGET, "skill_id": "mod_status_hit", "critical_roll": 0.5, "variance": 1}
        for field in required:
            request = copy.deepcopy(required)
            request.pop(field)
            cases.append(action_case(steps=[{"operation": "next"}, action(request=request)]))
        for field, value in itertools.product(("attack", "guard", "current_mp", "status_effects", "status_resistance_level", "mode"),
                                             (False, 0, "", {}, [])):
            cases.append(action_case(steps=[{"operation": "next"}, action(extra={field: value})]))
        for field, values in (("critical_roll", (True, -1, 1, [], {})), ("variance", (True, 0, 2, [], {})),
                              ("status_roll", (True, -1, 1, "0", [], {})),
                              ("target", (None, ACTOR, {"side": "enemies", "id": "missing"})),
                              ("skill_id", (None, "unknown", "body_bash"))):
            for value in values:
                cases.append(action_case(steps=[{"operation": "next"}, action(extra={field: value})]))
        for field, value in itertools.product(("critical_roll", "variance", "status_roll"), ("nan", "object")):
            cases.append(action_case(steps=[{"operation": "next"}, action(special={"field": field, "value": value})]))
        missing_roll = action()
        missing_roll.pop("status_roll")
        cases.append(action_case(steps=[{"operation": "next"}, missing_roll]))
        for case, observed in zip(cases, self.observe({"cases": cases})["results"]):
            with self.subTest(step=case["steps"][-1]):
                step = observed["steps"][-1]
                self.assertFalse(step["result"]["ok"], step)
                self.assertTrue(step["unchanged"])
                self.assertEqual(observed["numeric"]["pending"]["stage"], "offered")

    # {
    #   責務: [test_mp_shortage_and_selected_definition_errors_preserve_resources: 最新MP不足と未習得/重複/未対応効果を、付与付き攻撃の成功として扱いません]
    #   処理: [1: 開始後のMP減少と選択定義/装備の不正を実行し、拒否時の完全非変更を確認します]
    #   引数: [self: 開始情報と最新MPの拒否を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_mp_shortage_and_selected_definition_errors_preserve_resources(self):
        cases = [action_case(steps=[{"operation": "next"}, {"operation": "pay", "actor": ACTOR, "value": 48}, action()])]
        unlearned = action_case()
        unlearned["teams"]["allies"][0]["skill_ids"] = ["body_bash"]
        duplicate = action_case()
        duplicate["skills"]["skills"].append(copy.deepcopy(duplicate["skills"]["skills"][0]))
        unsupported = action_case()
        unsupported["skills"]["skills"][0]["all_targets"] = False
        wrong_effect = action_case()
        wrong_effect["skills"]["skills"][0]["status_effect"]["chance"] = True
        gear = action_case()
        gear["teams"]["allies"][0]["equipment"] = {"allowed_species_ids": ["slime"],
            "skill_modifiers": {"mod_status_hit": {"power_multiplier": True}}}
        cases += [unlearned, duplicate, unsupported, wrong_effect, gear]
        observed_cases = self.observe({"cases": cases})["results"]
        for observed in observed_cases:
            self.assertFalse(observed["steps"][-1]["result"]["ok"])
            self.assertTrue(observed["steps"][-1]["unchanged"])
        self.assertEqual(observed_cases[0]["steps"][-1]["result"]["reason"], "insufficient_mp")

    # {
    #   責務: [test_retry_after_invalid_roll_and_reject_completed_or_claimed_tickets: 不正判定値の修正は実行でき、取得済み/完了済み票は再実行できないことを確認します]
    #   処理: [1: 不正→正常→同票再送と外部claim済みのケースを実行し、追加のMP/HP/状態変化を拒否します]
    #   引数: [self: 修正再試行と二重実行防止を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_retry_after_invalid_roll_and_reject_completed_or_claimed_tickets(self):
        retry = action_case(steps=[{"operation": "next"}, action(status_roll=True), action(), action(ticket=TICKET)])
        claimed = action_case(steps=[{"operation": "next"}, {"operation": "claim"}, action()])
        observed = self.observe({"cases": [retry, claimed]})["results"]
        self.assertTrue(observed[0]["steps"][1]["unchanged"])
        self.assertTrue(observed[0]["steps"][2]["result"]["executed"])
        self.assertFalse(observed[0]["steps"][3]["result"]["ok"])
        self.assertTrue(observed[0]["steps"][3]["unchanged"])
        self.assertEqual(observed[0]["numeric"]["teams"]["allies"][0]["mp"], 47)
        self.assertEqual(observed[1]["steps"][-1]["result"]["reason"], "already_claimed")
        self.assertTrue(observed[1]["steps"][-1]["unchanged"])

    # {
    #   責務: [test_actor_death_flee_and_no_opponent_cancel_without_payment: 予約後の最新生存を使い、行動不能ならMP不足に置き換えず一回取消します]
    #   処理: [1: 死亡/逃走/敵なしを提示後に作り、不正判定値拒否の後に資源を使わない取消を確認します]
    #   引数: [self: 最新行動可否と取消を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_actor_death_flee_and_no_opponent_cancel_without_payment(self):
        cases = []
        for change in ({"operation": "damage", "actor": ACTOR, "value": 1000},
                       {"operation": "flee", "actor": ACTOR}, {"operation": "damage", "actor": TARGET, "value": 1000}):
            valid = action()
            valid.pop("status_roll")
            cases.append(action_case(steps=[{"operation": "next"}, {"operation": "pay", "actor": ACTOR, "value": 50},
                                           change, action(status_roll=True), valid]))
        for observed in self.observe({"cases": cases})["results"]:
            invalid, canceled = observed["steps"][-2:]
            self.assertFalse(invalid["result"]["ok"])
            self.assertTrue(invalid["unchanged"])
            self.assertTrue(canceled["result"]["ok"], canceled)
            self.assertFalse(canceled["result"]["executed"])
            self.assertEqual(canceled["numeric"]["cursor"], 1)
            self.assertEqual(canceled["numeric"]["teams"]["allies"][0]["mp"], 0)
            self.assertEqual(canceled["statuses"], invalid["statuses"])

    # {
    #   責務: [test_lethal_attack_skips_application_and_bad_unused_roll_still_rejects: 致死攻撃は付与を実行せず、不要でも指定済みの不正付与判定値を拒否します]
    #   処理: [1: HP1へ不正判定値を拒否後、付与判定値なしの攻撃で停止・MP消費・状態保持を確認します]
    #   引数: [self: 非致死条件と判定不要の境界を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_lethal_attack_skips_application_and_bad_unused_roll_still_rejects(self):
        valid = action()
        valid.pop("status_roll")
        case = action_case(steps=[{"operation": "next"}, action(status_roll=True), valid])
        case["teams"]["enemies"][0]["snapshot"].update(hp=1)
        case["teams"]["enemies"][0]["snapshot"]["stats"]["hp"] = 1
        observed = self.observe({"cases": [case]})["results"][0]
        self.assertTrue(observed["steps"][1]["unchanged"])
        result = observed["steps"][-1]["result"]
        self.assertTrue(result["executed"])
        self.assertEqual(result["dealt"], 1)
        self.assertEqual(result["applied_status"], {})
        self.assertEqual(result["numbers"]["status"]["outcome"], "target_defeated")
        self.assertEqual(result["session"]["phase"], "stopped")
        self.assertEqual(result["statuses"]["teams"]["enemies"]["same"], [])

    # {
    #   責務: [test_post_claim_failures_stop_at_first_rejection_without_replay: 各更新段階の注入拒否を成功扱いせず、取得後の予約を再利用しないことを確認します]
    #   処理: [1: claim/pay/damage/status/finishを順に拒否し、呼出順・部分資源・再送時の追加更新拒否を照合します]
    #   引数: [self: 内部失敗時の観測可能な境界を検査するテストケース]
    #   戻り値: [result: なし（None）。注入した内部異常の巻き戻しを保証するテストではありません]
    # }
    def test_post_claim_failures_stop_at_first_rejection_without_replay(self):
        operations = ["claim", "pay", "damage", "status", "finish"]
        cases = [action_case(fail_at=operation, steps=[{"operation": "next"}, action(), action(ticket=TICKET)]) for operation in operations]
        for index, observed in enumerate(self.observe({"cases": cases})["results"]):
            with self.subTest(failure=operations[index]):
                failure = observed["steps"][1]["result"]
                self.assertFalse(failure["ok"])
                if index == 0:
                    self.assertEqual(observed["calls"], ["claim", "claim"])
                    self.assertTrue(observed["steps"][1]["unchanged"])
                else:
                    self.assertTrue(failure["action_consumed"])
                    self.assertEqual(observed["calls"], operations[:index + 1])
                    self.assertEqual(observed["steps"][-1]["result"]["reason"], "already_claimed")
                    self.assertTrue(observed["steps"][-1]["unchanged"])
                self.assertEqual(observed["numeric"]["teams"]["allies"][0]["mp"], 50 if index < 2 else 47)
                self.assertEqual(observed["numeric"]["teams"]["enemies"][0]["hp"], 1000 if index < 3 else 921)

    # {
    #   責務: [test_no_roll_is_needed_for_duplicate_immune_or_zero_chance: 付与判定が不要な重複/無効/確率0では判定値を省略して攻撃できることを確認します]
    #   処理: [1: 三種類の正常不成立を実行し、MP消費・物理ダメージと状態一覧の保持を確認します]
    #   引数: [self: 任意付与判定値の省略条件を検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_no_roll_is_needed_for_duplicate_immune_or_zero_chance(self):
        hit = action()
        hit.pop("status_roll")
        cases = [action_case(steps=[{"operation": "next"}, hit]) for _ in range(3)]
        cases[0]["initial_statuses"]["enemies"]["same"] = ["bleeding"]
        cases[1]["teams"]["enemies"][0]["status_resistances"] = {"bleeding": "immune"}
        cases[2]["skills"]["skills"][0]["status_effect"]["chance"] = 0
        for case, observed in zip(cases, self.observe({"cases": cases})["results"]):
            result = observed["steps"][-1]["result"]
            self.assertTrue(result["executed"])
            self.assertEqual(result["spent_mp"], 3)
            self.assertGreater(result["dealt"], 0)
            self.assertFalse(result["applied_status"]["applied"])
            self.assertFalse(result["numbers"]["status"]["roll_required"])
            self.assertEqual(result["statuses"]["teams"]["enemies"]["same"], case["initial_statuses"]["enemies"]["same"])

    # {
    #   責務: [test_dead_selected_enemy_is_rejected_when_another_enemy_is_alive: 他の敵が生存する場合、指定した死亡対象への攻撃を取消ではなく非消費拒否にします]
    #   処理: [1: 二体の敵のうち指定対象だけを倒し、拒否後に生存対象へ同じ予約で攻撃できることを確認します]
    #   引数: [self: 指定対象と全敵生存条件の違いを検査するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_dead_selected_enemy_is_rejected_when_another_enemy_is_alive(self):
        other = {"side": "enemies", "id": "other"}
        case = action_case(order=[ACTOR, TARGET, other], steps=[{"operation": "next"},
            {"operation": "damage", "actor": TARGET, "value": 1000}, action(), action(target=other)])
        member = copy.deepcopy(case["teams"]["enemies"][0])
        member["snapshot"]["identity"]["id"] = "other"
        case["teams"]["enemies"].append(member)
        case["initial_statuses"]["enemies"]["other"] = []
        observed = self.observe({"cases": [case]})["results"][0]
        self.assertEqual(observed["steps"][2]["result"]["reason"], "target_not_alive")
        self.assertTrue(observed["steps"][2]["unchanged"])
        self.assertTrue(observed["steps"][3]["result"]["executed"])
        self.assertEqual(observed["numeric"]["teams"]["allies"][0]["mp"], 47)
