"""取得済み予約による速度付与の一回制限・非変更境界を、実Godotと実Pythonで確認します。"""
# {
#   責務: [test_gdscript_claimed_speed: 速度集合/Sessionの実付与、拒否後再試行、予約・最新生存・順序固定を検証します]
#   フィールド: []
# }
from __future__ import annotations
import copy
import importlib.util
import math
import unittest

import test_gdscript_session_speed as joined
import test_gdscript_speed_state as speed
import test_gdscript_status_cure as fixture
import test_gdscript_status_session_round as rounds

ACTOR, ENEMY = rounds.ACTOR, rounds.ENEMY
TICKET = {"round": 1, "slot": 0, "actor": ACTOR}
REQUEST = {"multiplier": 1.5, "duration": 3}


# {
#   責務: [claimed_case: 明示初期倍率1.2の両陣営を開始し、味方の行動予約を取得する独立要求を作ります]
#   処理: [1: 共用の数値/状態を複製し、begin/next/claimを既定の操作列へ設定します]
#   引数: [changes: 参加者・開始区分・操作列の個別上書き（dict）]
#   戻り値: [result: 実セーブから独立した速度付与の観測要求（dict）]
# }
def claimed_case(**changes):
    # 速度11対10・倍率は共通1.2で、最初の行動者を味方へ固定します。
    return {**rounds.round_case([]), "initial_speed_multipliers": {"allies": {"same": 1.2}, "enemies": {"same": 1.2}},
            "steps": [{"operation": "begin", "order": [ACTOR, ENEMY]}, {"operation": "next"}, {"operation": "claim"}],
            **changes}


# {
#   責務: [apply_step: 指定対象への正規化済み速度付与要求を、呼出元と独立した操作として作ります]
#   処理: [1: 対象/要求と任意の予約・native注入条件を複製します]
#   引数: [
#     target: 付与するside/id。省略時は味方sameです（dict）
#     request: 倍率と任意期間。省略時は1.5倍/3ラウンドです（dictまたは不正検査値）
#     options: 明示ticketや不正値注入の追加条件（dict）
#   ]
#   戻り値: [result: speed_apply操作（dict）]
# }
def apply_step(target=ACTOR, request=REQUEST, **options):
    # テストの共有定数をプローブの編集対象へ渡さず、ケースごとに独立した要求を作ります。
    return copy.deepcopy({"operation": "speed_apply", "target": target, "request": request, **options})


# {
#   責務: [ClaimedSpeedBoundaryTests: 予約所有者をI/O・AI・速度計算・期間経過・Applicationの生更新から分離します]
#   フィールド: []
# }
class ClaimedSpeedBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_update_delegates_rules_without_io_or_implicit_expiration: 予約所有者は速度規則を委譲し、期限経過はSession終端へ分離します]
    #   処理: [1: 予約所有者の禁止依存と、Sessionから速度集合への一か所の経過委譲・上位入口/数値snapshotの分離を照合します]
    #   引数: [self: 責務境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_update_delegates_rules_without_io_or_implicit_expiration(self):
        root = fixture.godot_fixture.ROOT / "gdscript"
        source = (root / "engine/claimed_speed_update.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "res://data/", "res://ui/", "res://application/",
                          "randf(", "randi(", ".pay_mp(", ".take_damage(", ".finish(", ".elapse_round(", "maxf("):
            self.assertNotIn(forbidden, source)
        self.assertIn("_speeds.apply_multiplier(target, request)", source)
        self.assertEqual((root / "engine/battle_session.gd").read_text(encoding="utf-8").count("_speeds.elapse_round()"), 1)
        self.assertNotIn("func apply_speed_multiplier(", (root / "application/battle_session_application.gd").read_text(encoding="utf-8"))
        self.assertNotIn("speed_multiplier", (root / "engine/combatant_state.gd").read_text(encoding="utf-8"))


# {
#   責務: [ClaimedSpeedTests: 専用要求・保存ダミーと実Godotの予約付き速度付与観測を所有します]
#   フィールド: [
#     folder: 要求を置く専用一時領域（Path）
#     saved_files: 個体/AI/items/party/stateの不変を確認する保存ダミー（list）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for claimed speed updates")
class ClaimedSpeedTests(unittest.TestCase):
    setUp = fixture.StatusCureQuoteTests.setUp
    run_probe = speed.SpeedStateTests.run_probe
    observe = joined.SessionSpeedTests.observe

    # {
    #   責務: [test_roster_sequences_match_python_and_keep_other_side_independent: 集合の最新速度付与を実Pythonへ比較し、同IDの反対陣営を変更しません]
    #   処理: [1: 初期倍率四種で強い/弱い再付与と期間なしを連続実行し、全中間状態を比較します]
    #   引数: [self: 速度集合とPython倍率規則を照合するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_roster_sequences_match_python_and_keep_other_side_independent(self):
        requests = [REQUEST, {"multiplier": 1.3, "duration": 5}, {"multiplier": 1.4},
                    {"multiplier": 0, "duration": 1}, {"multiplier": 2, "duration": None}]
        cases = [claimed_case(mode="collection", initial_speed_multipliers={"allies": {"same": initial}, "enemies": {"same": 0.75}},
                 steps=[apply_step(request=value) for value in requests]) for initial in (0, 1, 1.2, 2)]
        for case, result in zip(cases, self.observe(cases)):
            operations = [{"method": "start", "value": case["initial_speed_multipliers"]["allies"]["same"]}]
            operations += [{"method": "apply", "value": value} for value in requests]
            for step, expected in zip(result["steps"], speed.python_trace(operations)[1:]):
                self.assertEqual(step["result"]["snapshot"], expected)
                self.assertEqual(step["state"]["speeds"]["teams"]["allies"]["same"], expected)
                self.assertEqual(step["state"]["speeds"]["teams"]["enemies"]["same"]["speed_multiplier"], 0.75)

    # {
    #   責務: [test_claimed_sequences_fix_current_order_and_use_owned_speed_next_round: 予約付き再付与は最新倍率を使い、現在順を保持して次ラウンドだけ速度を反映します]
    #   処理: [1: 別予約で敵へ強化/弱い延長/期間なしを付与し、三ラウンドの順序と終端だけの期間減算を照合します]
    #   引数: [self: 最新倍率・現在順固定・終端経過を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_claimed_sequences_fix_current_order_and_use_owned_speed_next_round(self):
        case = claimed_case()
        case["steps"] += [apply_step(ENEMY), {"operation": "finish"}, {"operation": "next"}, {"operation": "claim"},
            apply_step(ENEMY, {"multiplier": 1.3, "duration": 5}), {"operation": "finish"},
            {"operation": "begin", "order": [ACTOR, ENEMY]}, {"operation": "next"}, {"operation": "claim"},
            apply_step(ENEMY, {"multiplier": 1.4}), {"operation": "finish"}, *rounds.complete_round(1),
            {"operation": "begin", "order": [ACTOR, ENEMY]}]
        result = self.observe([case])[0]
        self.assertEqual(result["steps"][3]["state"]["numeric"]["order"], [ACTOR, ENEMY])
        self.assertEqual(result["steps"][9]["result"]["plan"]["order"], [ENEMY, ACTOR])
        self.assertEqual(result["state"]["numeric"]["order"], [ENEMY, ACTOR])
        expected = speed.python_trace([{"method": "start", "value": 1.2},
            {"method": "apply", "value": REQUEST}, {"method": "apply", "value": {"multiplier": 1.3, "duration": 5}},
            {"method": "elapse"}, {"method": "apply", "value": {"multiplier": 1.4}}, {"method": "elapse"}])[-1]
        self.assertEqual(result["state"]["speeds"]["teams"]["enemies"]["same"], expected)
        self.assertEqual(result["state"]["numeric"]["teams"], case["snapshots"])
        for index in (3, 7, 12):
            self.assertTrue(result["steps"][index]["result"]["ok"])
            for field in ("numeric", "statuses", "guards"):
                self.assertEqual(result["steps"][index]["state"][field], result["steps"][index - 1]["state"][field])

    # {
    #   責務: [test_noop_consumes_once_and_status_updates_have_separate_records: 倍率不変でも正常付与は一回を消費し、治療/状態付与と速度付与の記録は独立です]
    #   処理: [1: 強い初期倍率へ弱い付与を行い、治療・状態付与・入力票編集後も速度の再送を拒否します]
    #   引数: [self: no-opと一回記録の独立性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_noop_consumes_once_and_status_updates_have_separate_records(self):
        case = claimed_case(initial_speed_multipliers={"allies": {"same": 2}, "enemies": {"same": 1}})
        case["initial_statuses"]["allies"]["same"] = ["poison"]
        case["steps"] += [apply_step(request={"multiplier": 1}, ticket=TICKET), {"operation": "edit_step_ticket", "index": 3},
            {"operation": "apply_cure", "actor": ACTOR, "request": {"cure_chance": 1, "roll": 0}},
            {"operation": "apply_status", "actor": ACTOR, "request": {"effect": {"id": "bleeding", "chance": 1}, "roll": 0}},
            apply_step(ENEMY, {"multiplier": 4, "duration": 9}), {"operation": "defend", "value": 0.5},
            apply_step(ENEMY), {"operation": "finish"}]
        result = self.observe([case])[0]
        self.assertTrue(result["steps"][3]["result"]["ok"] and result["steps"][3]["unchanged"])
        for index in (5, 6):
            self.assertTrue(result["steps"][index]["result"]["ok"])
        for index in (7, 9):
            self.assertEqual(result["steps"][index]["result"], {"ok": False, "reason": "speed_multiplier_already_applied"})
            self.assertTrue(result["steps"][index]["unchanged"])
        self.assertEqual(result["steps"][9]["state"]["guards"]["teams"]["allies"]["same"], 0.5)

    # {
    #   責務: [test_invalid_requests_and_native_values_preserve_and_allow_retry: 不正倍率/期間/未知キーとnative値は予約・全状態を変更せず正常再試行できます]
    #   処理: [1: 不正要求を取得済み票へ渡し、拒否後の正常成功と二回目拒否を確認します]
    #   引数: [self: 要求検証の非変更と再試行を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_requests_and_native_values_preserve_and_allow_retry(self):
        invalid = [None, False, 1, [], {}, {"duration": 3}]
        invalid += [{"multiplier": value} for value in (None, True, "1.5", {}, [], -1, 2**53)]
        invalid += [{"multiplier": 1.5, "duration": value} for value in (False, "3", 0, -1, 1.5, [], [3, 6], {}, 2**53)]
        invalid += [{**REQUEST, key: value} for key in ("snapshot", "ticket", "speed_multiplier", "other")
                    for value in (False, 0, [])]
        bad_steps = [apply_step(request=value) for value in invalid]
        bad_steps += [apply_step(update_special=kind, special_field=field)
                      for kind in ("nan", "inf", "object") for field in ("multiplier", "duration")]
        cases = []
        for bad in bad_steps:
            case = claimed_case()
            case["steps"] += [bad, apply_step(), apply_step(ENEMY)]
            cases.append(case)
        for result in self.observe(cases):
            self.assertFalse(result["steps"][3]["result"]["ok"])
            self.assertTrue(result["steps"][3]["unchanged"])
            self.assertTrue(result["steps"][4]["result"]["ok"])
            self.assertEqual(result["steps"][5]["result"]["reason"], "speed_multiplier_already_applied")
            self.assertTrue(result["steps"][5]["unchanged"])

    # {
    #   責務: [test_phase_ticket_target_and_liveness_boundaries_do_not_consume_updates: 未開始/未取得/偽造票/不正対象と最新死亡・逃走を非変更で拒否します]
    #   処理: [1: 段階・予約・対象の不正と取得後の離脱を作り、拒否理由と全状態保持を照合します]
    #   引数: [self: 予約と最新生存の境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_phase_ticket_target_and_liveness_boundaries_do_not_consume_updates(self):
        cases = [(claimed_case(no_start=True, steps=[apply_step()]), "not_initialized"),
                 (claimed_case(legacy=True), "speed_not_configured"),
                 (claimed_case(steps=[{"operation": "begin", "order": [ACTOR, ENEMY]}, {"operation": "next"}]), "pending_not_claimed")]
        for case, reason in cases:
            if not case.get("no_start"):
                case["steps"].append(apply_step())
            observed = self.observe([case])[0]["steps"][-1]
            self.assertEqual(observed["result"]["reason"], reason)
            self.assertTrue(observed["unchanged"])
        targets = [None, False, [], {}, {**ACTOR, "extra": 1}, {"side": "other", "id": "same"},
                   {"side": "allies", "id": "missing"}]
        tickets = [None, False, {}, {**TICKET, "extra": 1}, {**TICKET, "round": True},
                   {**TICKET, "slot": 0.5}, {**TICKET, "round": 2}, {**TICKET, "actor": ENEMY}]
        cases = []
        for step in [apply_step(target) for target in targets] + [apply_step(ticket=ticket) for ticket in tickets]:
            case = claimed_case()
            case["steps"] += [step, apply_step(ticket={"round": 1.0, "slot": 0.0, "actor": ACTOR})]
            cases.append(case)
        for result in self.observe(cases):
            self.assertFalse(result["steps"][3]["result"]["ok"])
            self.assertTrue(result["steps"][3]["unchanged"])
            self.assertTrue(result["steps"][4]["result"]["ok"])
        # 生存変化は公開資源APIで作り、速度付与から死亡/逃走を取り消させません。
        for who, target, reason in ((ACTOR, ENEMY, "actor_cannot_apply_speed"),
                                   (ENEMY, ENEMY, "target_not_alive"), (ENEMY, ACTOR, "actor_cannot_apply_speed")):
            for operation in ("damage", "flee"):
                case = claimed_case()
                case["steps"] += [{"operation": operation, "actor": who, "value": 999}, apply_step(target)]
                observed = self.observe([case])[0]["steps"][-1]
                self.assertEqual(observed["result"]["reason"], reason)
                self.assertTrue(observed["unchanged"])

    # {
    #   責務: [test_eight_independent_owners_new_rounds_and_old_tickets: 八体を別予約で一回ずつ更新し、次ラウンドの新規付与と古い票拒否を確認します]
    #   処理: [1: 同ID両陣営の全員へ公開APIで付与して完了し、終端の一回減算・次回予約・旧票を照合します]
    #   引数: [self: 最大参加者と予約寿命を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_eight_independent_owners_new_rounds_and_old_tickets(self):
        case = rounds.roster.roster_case([], count=4)
        order = [rounds.normal.key(side, f"same_{index}") for side in ("allies", "enemies") for index in range(4)]
        case["steps"] = [{"operation": "begin", "order": order}]
        for actor in order:
            target = {"side": "enemies" if actor["side"] == "allies" else "allies", "id": actor["id"]}
            case["steps"] += [{"operation": "next"}, {"operation": "claim"}, apply_step(target),
                             apply_step(actor), {"operation": "finish"}]
        old = {"round": 1, "slot": 7, "actor": order[-1]}
        case["steps"] += [{"operation": "begin", "order": order}, apply_step(order[0], ticket=old),
                         {"operation": "next"}, {"operation": "claim"}, apply_step(order[0], {"multiplier": 2, "duration": 2})]
        result = self.observe([case])[0]
        self.assertEqual(result["steps"][40]["state"]["numeric"]["phase"], "round_finished")
        for members in result["steps"][40]["state"]["speeds"]["teams"].values():
            for state in members.values():
                self.assertEqual(state, {"speed_multiplier": 1.5, "remaining_turns": 2, "baseline_multiplier": 1})
        self.assertEqual(result["steps"][42]["result"]["reason"], "ticket_not_pending")
        self.assertTrue(result["steps"][42]["unchanged"])
        self.assertTrue(result["steps"][-1]["result"]["ok"])
        for index in range(8):
            self.assertEqual(result["steps"][4 + 5 * index]["result"]["reason"], "speed_multiplier_already_applied")

    # {
    #   責務: [test_json_and_native_ticket_forms_share_once_records_for_all_updates: JSONのfloat票と内部int票を同じ予約として速度/治療/状態付与の各一回記録へ照合します]
    #   処理: [1: 明示JSON票と自動取得票の順を両方向で入れ替え、同じ予約の二回目更新を拒否します]
    #   引数: [self: 予約番号の型差による再送を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_json_and_native_ticket_forms_share_once_records_for_all_updates(self):
        cases = []
        reasons = []
        for first, second, reason in (
                (apply_step(), apply_step(ENEMY), "speed_multiplier_already_applied"),
                ({"operation": "apply_cure", "actor": ACTOR, "request": {"cure_chance": 1, "roll": 0}},
                 {"operation": "apply_cure", "actor": ACTOR, "request": {"cure_chance": 1, "roll": 0}},
                 "status_cure_already_applied"),
                ({"operation": "apply_status", "actor": ACTOR, "request": {"effect": {"id": "sleep", "chance": 1}, "roll": 0}},
                 {"operation": "apply_status", "actor": ACTOR, "request": {"effect": {"id": "bleeding", "chance": 1}, "roll": 0}},
                 "status_application_already_applied")):
            # JSON.parseの整数はfloatになり、自動取得したSession内部票はintなので、両方の順序を通します。
            for explicit_first in (True, False):
                case = claimed_case()
                case["initial_statuses"]["allies"]["same"] = ["poison", "poison"]
                pair = copy.deepcopy([first, second])
                pair[0 if explicit_first else 1]["ticket"] = copy.deepcopy(TICKET)
                case["steps"] += pair
                cases.append(case)
                reasons.append(reason)
        for case, reason in zip(self.observe(cases), reasons):
            self.assertTrue(case["steps"][3]["result"]["ok"])
            self.assertEqual(case["steps"][4]["result"], {"ok": False, "reason": reason})
            self.assertTrue(case["steps"][4]["unchanged"])

    # {
    #   責務: [test_performance_validator_requires_real_updates_all_batches_and_fixed_states: 性能検査は実更新・終端復元・全反復・再送拒否・有限時間を要求します]
    #   処理: [1: 実Godotの小反復を照合し、入力・速度・数値・完了数・時間の偽装と端数反復を拒否します]
    #   引数: [self: 専用要求と保存ダミーを所有するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_performance_validator_requires_real_updates_all_batches_and_fixed_states(self):
        # 固定結果の自己一致ではなく、独立したPython期待値が不正な高速結果を拒否するか確認します。
        path = fixture.godot_fixture.ROOT / "tools/performance-check/script/check_gdscript_speed_update.py"
        spec = importlib.util.spec_from_file_location("claimed_speed_performance", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        request = {"performance": True, "claimed_speed": True, "iterations": 16, "samples": 3, "warmup": 8}
        observed = self.run_probe(request)
        # 小反復は機能結果を採取するだけです。機器依存の性能合否は標準CLIの実測値で別に判定します。
        self.assertIs(type(observed["microseconds"]), float)
        self.assertTrue(math.isfinite(observed["microseconds"]) and observed["microseconds"] >= 0)
        # 形式検査の正常時間には固定値を使い、標準計測値を書き換えた性能成功とは報告しません。
        candidate = {**observed, "microseconds": 1000.0}
        self.assertTrue(module.valid_result(candidate, request), observed)
        for field, value in (("completed", 0), ("completed", True), ("last", {}), ("speeds", {}), ("numeric", {}),
                             ("original_source", {}), ("input_preserved", False), ("iterations", True),
                             ("microseconds", float("nan")), ("microseconds", float("inf")),
                             ("microseconds", True), ("microseconds", -1), ("microseconds", 3001)):
            self.assertFalse(module.valid_result({**candidate, field: value}, request), field)
        changed = copy.deepcopy(candidate)
        changed["speeds"]["teams"]["allies"]["member_0"]["remaining_turns"] = 1
        self.assertFalse(module.valid_result(changed, request))
        changed = copy.deepcopy(candidate)
        changed["speeds"]["teams"]["enemies"]["member_3"]["speed_multiplier"] = 1.5
        self.assertFalse(module.valid_result(changed, request))
        changed = copy.deepcopy(candidate)
        changed["original_source"]["request"]["duration"] = True
        self.assertFalse(module.valid_result(changed, request))
        self.assertEqual(self.run_probe({**request, "iterations": 1}), {"ok": False, "reason": "complete_rounds_required"})
