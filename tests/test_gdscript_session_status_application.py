"""取得済み予約の一回付与を実Godot/Pythonで比較し、予約/数値/保存ダミーの保持を検証します。"""
# {
#   責務: [test_gdscript_session_status_application: 予約付き付与の一回判定・対象/生存/拒否・治療共存・独立コピーを確認します]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import copy
import importlib.util
import itertools
import unittest

import test_gdscript_roster_status_application as roster
import test_gdscript_status_apply as application
import test_gdscript_status_cure as fixture
import test_gdscript_normal_attack_action as normal


# {
#   責務: [reserved_case: 両陣営同IDの独立参加者と状態・行動順を用意し、取得までの手順を作ります]
#   処理: [1: 共用八体/同IDfixtureから開始情報を作り、begin/next/claimを既定操作にします]
#   引数: [
#     effects: 各個体へ独立コピーする初期状態。Noneなら空一覧です
#     count: 各陣営の参加数。既定1、八体検証4です（int）
#     changes: ケースごとの開始/操作を上書きする値
#   ]
#   戻り値: [result: 状態付きSessionの独立観測ケース（dict）]
# }
def reserved_case(effects=None, count=1, **changes):
    # 数値参加者と状態は既存fixtureへ任せ、予約取得までの手順だけを追加します。
    case = roster.roster_case(effects, count)
    order = [normal.key(side, member["identity"]["id"]) for side, members in case["snapshots"].items() for member in members]
    return {**case, "steps": [{"operation": "begin", "order": order}, {"operation": "next"}, {"operation": "claim"}], **changes}


# {
#   責務: [SessionStatusApplicationBoundaryTests: 予約付き状態更新の依存と数値/スキル/画面からの分離を確認します]
#   フィールド: []
# }
class SessionStatusApplicationBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_reservation_owner_has_no_io_rng_or_skill_rules: 新規所有者が状態委譲と種類別一回記録だけを担当するか確認します]
    #   処理: [1: 禁止依存とSessionへの逆参照を検査し、行動/Applicationへの付与入口未追加を確認します]
    #   引数: [self: 内部状態更新の責務境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_reservation_owner_has_no_io_rng_or_skill_rules(self):
        # 内部更新所有者の禁止依存と公開範囲をソースで確認し、GUI成功の証拠にはしません。
        root = fixture.godot_fixture.ROOT / "gdscript"
        source = (root / "engine/claimed_status_updates.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "randf(", "RandomNumberGenerator", ".pay_mp(", ".heal(",
                          "res://application/", "res://data/", "res://ui/", "skill_ids", "MULTIPLIERS", "battle_session.gd"):
            self.assertNotIn(forbidden, source)
        self.assertIn('.apply(target, request)', source)
        self.assertIn('ticket.duplicate(true)', source)
        self.assertNotIn("func resolve_status_application(", (root / "application/battle_session_application.gd").read_text(encoding="utf-8"))


# {
#   責務: [SessionStatusApplicationTests: 専用要求/保存ダミーと実Godot/Python比較の検証を所有します]
#   フィールド: [
#     folder: 共用fixtureが作る要求/保存ダミーの専用領域（Path）
#     saved_files: 毎起動後にbyte保持を確認する五種類の保存ダミー（list[Path]）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for claimed status updates")
class SessionStatusApplicationTests(unittest.TestCase):
    setUp = fixture.StatusCureQuoteTests.setUp

    # {
    #   責務: [observe: 状態付きSession専用区分で共用起動/診断/保存ダミー保持検査へ委譲します]
    #   処理: [1: 専用コピー要求にsession_status_apply=trueを追加して実Godot結果を取得します]
    #   引数: [
    #     self: 専用領域と保存ダミーの所有者
    #     payload: casesまたは性能条件の観測要求（dict）
    #   ]
    #   戻り値: [result: 診断/専用要求/保存ダミー保持を確認した実観測（dict）]
    # }
    def observe(self, payload):
        # 共用起動fixtureへ専用区分を渡し、実セーブや重複した起動実装を使いません。
        return fixture.StatusCureQuoteTests.run_probe(self, {**copy.deepcopy(payload), "session_status_apply": True})

    # {
    #   責務: [check_independence: 初期/要求/返却の編集がSessionの状態と数値へ伝播しないことを確認します]
    #   処理: [1: 観測数・原本保持・各操作の要求保持と返却独立性を照合します]
    #   引数: [
    #     self: 独立コピーを検証するテストケース
    #     case: 専用の開始/操作要求（dict）
    #     actual: 実Godotの観測（dict）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def check_independence(self, case, actual):
        # 欠落した観測でzipが短く終わる偽成功を防ぎ、全操作の独立性まで確認します。
        self.assertEqual(len(actual["steps"]), len(case["steps"]))
        self.assertTrue(actual["source_independent"] and actual["input_preserved"])
        self.assertTrue(all(step["independent"] and step["request_preserved"] for step in actual["steps"]))

    # {
    #   責務: [test_latest_application_matches_python_and_is_once_per_ticket: 両陣営/本人への付与を実Pythonと照合し、異なる対象への同予約再判定も拒否します]
    #   処理: [1: 陣営/初期状態/耐性/rollの組合せで対象一体の更新と予約/数値の不変を比較します]
    #   引数: [self: 最新状態の互換性と一回判定を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_latest_application_matches_python_and_is_once_per_ticket(self):
        # 行動者と対象の陣営を独立に変え、本人/味方/敵を同じ予約条件で比較します。
        cases = []
        for actor_side, target_side, initial, resistance, roll in itertools.product(
            ("allies", "enemies"), ("allies", "enemies"), ([], ["bleeding"], ["poison"]),
            ("normal", "weak", "immune"), (0, 0.4, 0.9)
        ):
            actor, target = normal.key(actor_side, "same"), normal.key(target_side, "same")
            order = [actor, normal.key("enemies" if actor_side == "allies" else "allies", "same")]
            case = reserved_case(initial)
            request = {"effect": {"id": " bleeding ", "display_name": "出血", "chance": 0.4,
                                  "metadata": {"deck": [1, {"kept": True}]}}, "resistance_level": resistance, "roll": roll}
            case["steps"][0]["order"] = order
            case["steps"] += [{"operation": "apply_status", "actor": target, "request": request},
                              {"operation": "apply_status", "actor": actor, "request": {"effect": {"id": "other", "chance": 1}, "roll": 0}},
                              {"operation": "finish"}]
            cases.append(case)
        # 実Godotと実Pythonを照合し、対象以外と数値/予約が変わらないことも確認します。
        results = self.observe({"cases": cases})["results"]
        self.assertEqual(len(results), len(cases))
        for case, actual in zip(cases, results):
            with self.subTest(case=case):
                self.check_independence(case, actual)
                update = case["steps"][3]
                target = update["actor"]
                expected = application.StatusApplyQuoteTests.python_result(
                    self, {"status_effects": copy.deepcopy(case["initial_statuses"][target["side"]][target["id"]]), **update["request"]})
                result = actual["steps"][3]["result"]
                for field, value in expected.items():
                    self.assertEqual(result[field], value, field)
                self.assertEqual(result["scope"], "combatant_status_apply")
                self.assertEqual(actual["steps"][4]["result"], {"ok": False, "reason": "status_application_already_applied"})
                current = copy.deepcopy(case["initial_statuses"])
                current[target["side"]][target["id"]] = expected["resulting_status_effects"]
                self.assertEqual(actual["statuses"], {"teams": current, "scope": "battle_status_only"})
                self.assertEqual(actual["steps"][2]["numeric"], actual["steps"][3]["numeric"])
                self.assertEqual(actual["steps"][3]["numeric"], actual["steps"][4]["numeric"])
                self.assertEqual(actual["numeric"]["teams"], case["snapshots"])

    # {
    #   責務: [test_normal_noops_also_consume_the_single_check: IDなし/重複/確率0/無効/不成立を正常な一回判定として記録します]
    #   処理: [1: 正常な付与なしの後は別ID/別判定でも同じ取得済み予約を拒否するか確認します]
    #   引数: [self: 再抽選による確率上昇を防ぐテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_normal_noops_also_consume_the_single_check(self):
        # 正常な不成立を全て使用済みにし、別状態での二回目判定を許しません。
        cases = []
        for request in ({"effect": {}}, {"effect": {"id": "mod", "chance": 0}}, {"effect": {"id": "mod", "chance": -1}},
                        {"effect": {"id": "bleeding", "chance": 1}}, {"effect": {"id": "mod", "chance": 1}, "resistance_level": "immune"},
                        {"effect": {"id": "mod", "chance": 0.4}, "roll": 0.4}):
            case = reserved_case(["bleeding"])
            target = normal.key("enemies", "same")
            case["steps"] += [{"operation": "apply_status", "actor": target, "request": request},
                              {"operation": "apply_status", "actor": target, "request": {"effect": {"id": "new", "chance": 1}, "roll": 0}}]
            cases.append(case)
        results = self.observe({"cases": cases})["results"]
        self.assertEqual(len(results), len(cases))
        for case, actual in zip(cases, results):
            self.check_independence(case, actual)
            self.assertTrue(actual["steps"][3]["result"]["ok"])
            self.assertFalse(actual["steps"][3]["result"]["applied"])
            self.assertEqual(actual["steps"][4]["result"]["reason"], "status_application_already_applied")
            self.assertEqual(actual["statuses"]["teams"], case["initial_statuses"])

    # {
    #   責務: [test_invalid_requests_and_native_values_can_retry_without_consumption: 不正対象/要求/予約/native値は数値/状態/取得済み票を保持し、正しい要求で再試行できます]
    #   処理: [1: 存在する対象へ不正条件を連続指定し、最後の正常要求だけが一件付与するか確認します]
    #   引数: [self: 不正入力で予約を消費しないことを確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_requests_and_native_values_can_retry_without_consumption(self):
        # 存在する対象へ不正条件を渡し、単なる対象不在で条件検査を迂回させません。
        target = normal.key("enemies", "same")
        valid = {"effect": {"id": "mod", "chance": 1}, "roll": 0}
        operations = [{"operation": "apply_status", "actor": target, "request": request}
                      for request in (None, False, 0, [], {}, {"effect": None}, {"effect": {"id": "mod", "chance": True}},
                                      {"effect": {"id": "mod", "chance": 1}, "resistance_level": False})]
        operations += [{"operation": "apply_status", "actor": target, "request": {**valid, field: value}}
                       for field, value in itertools.product(("status_effects", "resulting_status_effects", "applied", "mp_cost"), (False, 0, [], {}))]
        operations += [{"operation": "apply_status", "actor": key, "request": valid} for key in
                       (None, [], {}, {"side": "allies"}, {"side": "other", "id": "same"}, normal.key("allies", "missing"),
                        {"side": "enemies", "id": "same", "extra": False})]
        operations += [{"operation": "apply_status", "actor": target, "request": {**valid, "roll": value}}
                       for value in (None, -1, 1, True, "0")]
        for value in ("nan", "inf", "object", "cycle", "non_string_key"):
            operations.append({"operation": "apply_status", "actor": target, "request": valid,
                               "special": {"target": "effect", "field": "metadata", "value": value}})
        for place, field, value in itertools.product(("request", "actor", "ticket"), ("roll",), ("nan", "inf", "object", "cycle")):
            operations.append({"operation": "apply_status", "actor": target, "request": valid,
                               "special": {"target": place, "field": field if place == "request" else ("id" if place == "actor" else "round"), "value": value}})
        case = reserved_case()
        case["steps"] += copy.deepcopy(operations) + [{"operation": "apply_status", "actor": target, "request": valid}]
        actual = self.observe({"cases": [case]})["results"][0]
        self.check_independence(case, actual)
        # 全拒否が同じ取得済み票を保持し、最後の正常な要求だけを実付与するか確認します。
        for observation in actual["steps"][3:-1]:
            self.assertFalse(observation["result"]["ok"], observation)
            self.assertEqual(observation["numeric"], actual["steps"][2]["numeric"])
            self.assertEqual(observation["statuses"]["teams"], case["initial_statuses"])
        self.assertTrue(actual["steps"][-1]["result"]["applied"])
        self.assertEqual(len(actual["statuses"]["teams"]["enemies"]["same"]), 1)

    # {
    #   責務: [test_initialization_offered_forged_and_finished_tickets_are_rejected: 未開始/従来開始/未取得/偽造/完了済みの票を理由付きで拒否します]
    #   処理: [1: 実際の予約段階と不正票を組み合わせ、状態が更新されないことを確認します]
    #   引数: [self: 行動権を持たない更新を防ぐテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_initialization_offered_forged_and_finished_tickets_are_rejected(self):
        # 現在の予約段階での拒否と、形式不正/偽造/完了済みの票を別々に確認します。
        update = {"operation": "apply_status", "actor": normal.key("enemies", "same"), "request": {"effect": {"id": "mod", "chance": 1}, "roll": 0}}
        cases = [reserved_case(no_start=True, steps=[update]), reserved_case(legacy=True),
                 reserved_case(steps=[*reserved_case()["steps"][:2], update])]
        cases[1]["steps"].append(update)
        expected = ["not_initialized", "status_not_configured", "pending_not_claimed"]
        for case, actual, reason in zip(cases, self.observe({"cases": cases})["results"], expected):
            self.check_independence(case, actual)
            self.assertEqual(actual["steps"][-1]["result"], {"ok": False, "reason": reason})
        forged = [None, False, 0, [], {}, {"round": True, "slot": 0, "actor": normal.key("allies", "same")},
                  {"round": 1, "slot": -1, "actor": normal.key("allies", "same")},
                  {"round": 0, "slot": 0, "actor": normal.key("allies", "same")},
                  {"round": 1, "slot": 0, "actor": normal.key("enemies", "same")},
                  {"round": 1, "slot": 0, "actor": normal.key("allies", "same"), "extra": False}]
        ticket = {"round": 1, "slot": 0, "actor": normal.key("allies", "same")}
        case = reserved_case()
        case["steps"] += [{**update, "ticket": value} for value in forged] + [update, {"operation": "finish"}, {**update, "ticket": ticket}]
        actual = self.observe({"cases": [case]})["results"][0]
        self.check_independence(case, actual)
        self.assertTrue(all(not step["result"]["ok"] for step in actual["steps"][3:3 + len(forged)]))
        self.assertTrue(actual["steps"][-3]["result"]["applied"])
        self.assertEqual(actual["steps"][-1]["result"]["reason"], "ticket_not_pending")

    # {
    #   責務: [test_latest_actor_target_and_opposition_liveness: 予約取得後の行動者/対象の死亡・逃走と敵全滅を最新資源から拒否します]
    #   処理: [1: 取得後に資源を変更し、付与拒否で変更済み数値と全状態を保持するか確認します]
    #   引数: [self: 古い生存情報による更新を防ぐテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_latest_actor_target_and_opposition_liveness(self):
        # 取得後にだけ生存情報を変え、開始時の古い情報を使った付与を防ぎます。
        actor, target = normal.key("allies", "same_0"), normal.key("enemies", "same_0")
        cases, expected = [], []
        for operation, key, reason in (("damage", actor, "actor_cannot_apply_status"), ("flee", actor, "actor_cannot_apply_status"),
                                        ("damage", target, "target_not_alive"), ("flee", target, "target_not_alive")):
            case = reserved_case(count=2)
            case["steps"] += [{"operation": operation, "actor": key, "value": 10000},
                              {"operation": "apply_status", "actor": target, "request": {"effect": {"id": "mod", "chance": 1}, "roll": 0}}]
            cases.append(case)
            expected.append(reason)
        case = reserved_case(count=2)
        case["steps"] += [{"operation": "damage", "actor": normal.key("enemies", f"same_{index}"), "value": 10000} for index in range(2)]
        case["steps"].append({"operation": "apply_status", "actor": normal.key("allies", "same_1"),
                              "request": {"effect": {"id": "mod", "chance": 1}, "roll": 0}})
        cases.append(case)
        expected.append("actor_cannot_apply_status")
        for case, actual, reason in zip(cases, self.observe({"cases": cases})["results"], expected):
            self.check_independence(case, actual)
            self.assertEqual(actual["steps"][-1]["result"]["reason"], reason)
            self.assertEqual(actual["steps"][-1]["numeric"], actual["steps"][-2]["numeric"])
            self.assertEqual(actual["statuses"]["teams"], case["initial_statuses"])

    # {
    #   責務: [test_cure_and_application_have_independent_once_records_across_rounds: 治療/付与は各一回に制限し、新しい予約/ラウンドでは再判定できます]
    #   処理: [1: 同じ票で付与と治療を一回ずつ行い、次ラウンドの付与を古い票と区別します]
    #   引数: [self: 種類別制限とラウンド間の更新を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_cure_and_application_have_independent_once_records_across_rounds(self):
        # 治療と付与の使用済み記録を分離し、次ラウンドの新しい票は再使用できるか確認します。
        target = normal.key("allies", "same")
        update = {"operation": "apply_status", "actor": target, "request": {"effect": {"id": "bleeding", "chance": 1}, "roll": 0}}
        cure = {"operation": "apply_cure", "actor": target, "request": {"cure_chance": 1, "roll": 0}}
        case = reserved_case(["poison"])
        order = case["steps"][0]["order"]
        case["steps"] += [update, cure, update, cure, {"operation": "defend", "value": 0.5}, {"operation": "finish"},
                          {"operation": "next"}, {"operation": "claim"}, {"operation": "finish"},
                          {"operation": "begin", "order": order}, {"operation": "next"}, {"operation": "claim"}, cure, update]
        actual = self.observe({"cases": [case]})["results"][0]
        self.check_independence(case, actual)
        self.assertTrue(actual["steps"][3]["result"]["applied"])
        self.assertTrue(actual["steps"][4]["result"]["cured"])
        self.assertEqual(actual["steps"][5]["result"]["reason"], "status_application_already_applied")
        self.assertEqual(actual["steps"][6]["result"]["reason"], "status_cure_already_applied")
        self.assertTrue(actual["steps"][-2]["result"]["cured"] and actual["steps"][-1]["result"]["applied"])
        self.assertEqual(actual["numeric"]["round"], 2)
        self.assertEqual(actual["steps"][11]["guards"]["teams"], {"allies": {"same": 1}, "enemies": {"same": 1}})
        self.assertEqual(actual["numeric"]["teams"], case["snapshots"])

    # {
    #   責務: [test_benchmark_requires_real_updates_complete_batches_and_fixed_input: 性能検査は八体実更新/再判定拒否/全反復確認数/原本保持を必要とします]
    #   処理: [1: 少量実測は通過し、欠落/高速拒否/確認不足/原本/状態改変と不完全バッチは拒否します]
    #   引数: [self: 性能の実結果条件を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_benchmark_requires_real_updates_complete_batches_and_fixed_input(self):
        # 少量でも八体へ実追加し、高速拒否/確認不足/原本改変を性能成功と扱いません。
        result = self.observe({"performance": True, "iterations": 80, "samples": 3, "warmup": 80})
        path = fixture.godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_status_cure.py"
        spec = importlib.util.spec_from_file_location("claimed_status_checker", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        checker = module.StatusCureBenchmark("unused", argparse.Namespace(iterations=80, samples=3, warmup=80, session_status_apply=True))
        self.assertTrue(checker._valid_session_apply_result(result), result)
        for field, value in (("last", {}), ("numeric", {}), ("statuses", {}), ("original_source", {}), ("original_order", []),
                             ("completed", 319), ("input_preserved", False), ("actors", 7), ("microseconds", -1), ("microseconds", 3001)):
            changed = copy.deepcopy(result)
            changed[field] = value
            self.assertFalse(checker._valid_session_apply_result(changed), field)
        self.assertEqual(self.observe({"performance": True, "iterations": 1, "samples": 1, "warmup": 0}),
                         {"ok": False, "reason": "complete_rounds_required"})
