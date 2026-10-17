"""所有資源の行動可否投影を公開生入力契約と独立期待値へ照合します。実セーブは使いません。"""
# {
#   責務: [test_gdscript_session_eligibility: 最新生存/資源・拒否順・予約/数値形式・コピー独立性の性能改善回帰を検証します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import random
import unittest

import test_gdscript_battle_session as session
import test_gdscript_roster as fixture
import test_gdscript_turn_order as turn


# {
#   責務: [expected_eligibility: Pythonで最新HP/逃走を独立に評価し、同じ形式の行動可否期待値を作ります]
#   処理: [1: HP正/未逃走の参加者を入力順で抽出し、敵なし優先の理由と読取資源を組み立てます]
#   引数: [
#     actor: 期待する行動者のside/id（dict）
#     teams: 最新資源のallies/enemies配列（dict）
#   ]
#   戻り値: [result: Godotと共有コードを使わない七キーの期待結果（dict）]
# }
def expected_eligibility(actor, teams):
    # aliveフラグをそのまま正解とせず、最新HP/逃走から生存条件を独立に計算します。
    side = actor["side"]
    other = "enemies" if side == "allies" else "allies"
    friends = [item for item in teams[side] if item["hp"] > 0 and not item["fled"]]
    foes = [item for item in teams[other] if item["hp"] > 0 and not item["fled"]]
    current = next(item for item in teams[side] if item["identity"]["id"] == actor["id"])
    reason = "ready"
    if not foes:
        reason = "no_living_foes"
    elif current["hp"] == 0 or current["fled"]:
        reason = "actor_not_alive"
    return {"ok": True, "can_act": reason == "ready", "stop": not foes, "reason": reason,
            "actor": copy.deepcopy(actor), "friends": copy.deepcopy(friends), "foes": copy.deepcopy(foes)}


# {
#   責務: [SessionEligibilityBoundaryTests: 所有者専用の生存読取と、公開生入力の厳密検査が分離されているか確認します]
#   フィールド: []
# }
class SessionEligibilityBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_owned_path_reuses_projection_without_revalidating_snapshots: Session内部は最新所有値だけを投影し、公開check_actorの検査を弱めていないことを確認します]
    #   処理: [1: 所有者の生存/投影委譲・生入力の_prepare維持と、IO/AI/保存からの分離を照合します]
    #   引数: [self: 純粋投影と所有境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_owned_path_reuses_projection_without_revalidating_snapshots(self):
        # 数値所有者を外部へ渡す別入口や、古い生存フラグのキャッシュを追加しません。
        root = fixture.ROOT / "gdscript/engine"
        source = (root / "battle_session.gd").read_text(encoding="utf-8")
        check = source.split("func _check(key: Dictionary)")[1].split("func _living_snapshots")[0]
        self.assertIn("Eligibility.project(", check)
        self.assertIn(".alive()", check)
        self.assertNotIn("Order.check_actor(", check)
        self.assertNotIn("_snapshots()", check)
        raw = (root / "turn_order.gd").read_text(encoding="utf-8")
        self.assertIn("var prepared := _prepare(allies, enemies)", raw)
        self.assertIn('if not _valid_key(key):', raw)
        projection = (root / "actor_eligibility_projection.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "randf(", "RandomNumberGenerator", "res://ui/", "res://data/", ".claim(", ".pay_mp("):
            self.assertNotIn(forbidden, projection)


# {
#   責務: [SessionEligibilityTests: 共用の隔離保存/実Godot起動を使い、所有者投影と生入力検査を比較します]
#   フィールド: [
#     setUp: 専用内容/保存ダミー領域を作る共用fixture（method）
#     invoke: 診断なしの実Godotと専用要求を使う共用起動（method）
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for owned eligibility checks")
class SessionEligibilityTests(unittest.TestCase):
    setUp = fixture.GDScriptRosterTests.setUp
    invoke = session.GDScriptSessionTests.invoke

    # {
    #   責務: [assert_parity: 所有者検査・公開生入力検査・Python期待値の完全一致と予約段階を確認します]
    #   処理: [1: 各投影観測の最新snapshotから期待値を作り、数値六キー/Session七キーと非消費を照合します]
    #   引数: [
    #     self: 実観測を比較するテストケース
    #     result: 一ケースのSession操作観測（dict）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def assert_parity(self, result):
        # 二つのGodot経路の自己一致だけでは通過させず、最新資源の独立計算とも比較します。
        self.assertTrue(result["input_preserved"])
        for observation in result["observations"]:
            value = observation["value"]
            if "inspection" not in value:
                continue
            numeric = observation["session"]
            actor = numeric["pending"]["ticket"]["actor"]
            expected = expected_eligibility(actor, numeric["teams"])
            with self.subTest(actor=actor, reason=expected["reason"]):
                self.assertEqual(value["reference"], expected)
                self.assertEqual(value["inspection"], {"ok": True, "eligibility": expected})
                self.assertEqual(numeric["pending"]["stage"], "offered")
                self.assertEqual(set(numeric), {"phase", "round", "cursor", "order", "pending", "teams", "scope"})
                for team in numeric["teams"].values():
                    for member in team:
                        self.assertEqual(set(member), {"identity", "stats", "hp", "mp", "fled", "alive"})

    # {
    #   責務: [test_seeded_eight_actor_rosters_match_strict_raw_contract: 同IDの両陣営八体で最新の死亡/逃走/消費MPを比較します]
    #   処理: [1: 固定seedの三十二編成を開始APIと資源APIで作り、全生存行動者の提示/取得前を照合します]
    #   引数: [self: 最大参加者と陣営分離の検証所有者]
    #   戻り値: [result: なし（None）]
    # }
    def test_seeded_eight_actor_rosters_match_strict_raw_contract(self):
        # 開始時は全員満資源にし、死亡/逃走はSessionの検証済み更新APIだけで作ります。
        rng = random.Random(116)
        cases = []
        for sample in range(32):
            teams = {side: [turn.member(str(index), speed=rng.randrange(1, 50)) for index in range(4)]
                     for side in ("allies", "enemies")}
            actions, living = [], []
            for side, members in teams.items():
                for member in members:
                    actor = turn.key(side, member["identity"]["id"])
                    condition = rng.randrange(4)
                    if condition == 0:
                        actions.append(session.action("damage", actor=actor, value=30))
                    elif condition == 1:
                        actions.append(session.action("flee", actor=actor))
                    else:
                        actions.append(session.action("pay", actor=actor, value=3))
                        living.append(actor)
            actions.append(session.action("begin", order=living))
            # 生存敵がいない場合は開始後stoppedであり、偽の行動許可を作りません。
            if any(key["side"] == "allies" for key in living) and any(key["side"] == "enemies" for key in living):
                for _ in living:
                    actions += [session.action("next"), session.action("eligibility_parity", mutate_result=True),
                                session.action("eligibility_parity"), session.action("claim"), session.action("finish")]
            cases.append(session.case(actions, turn.request(**teams)))
        results = self.invoke(cases)["cases"]
        for result in results:
            self.assert_parity(result)
            self.assertIn(result["session"]["phase"], ("stopped", "round_finished"))

    # {
    #   責務: [test_offered_ticket_observes_death_flee_recovery_and_latest_resources: 提示済み予約でも最新の死亡/逃走/HP回復・MP消費を反映します]
    #   処理: [1: 予約提示後の資源更新と失敗を挟み、同じ予約の検査/取得取消の結果を照合します]
    #   引数: [self: 生存情報をキャッシュしないことを確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_offered_ticket_observes_death_flee_recovery_and_latest_resources(self):
        actor, enemy = turn.key("allies", "ally"), turn.key("enemies", "enemy")
        start = [session.action("begin"), session.action("next"), session.action("eligibility_parity")]
        # 不正ダメージ/消費は保持し、死亡後のHP回復は同じ提示票の最新判定へ戻します。
        variants = [
            [session.action("damage", actor=actor, value=30)],
            [session.action("flee", actor=actor)],
            [session.action("damage", actor=enemy, value=30), session.action("damage", actor=actor, value=30)],
            [session.action("damage", actor=actor, value=30), session.action("heal", actor=actor, value=2),
             session.action("pay", actor=actor, value=3), session.action("damage", actor=enemy, value=4)],
            [session.action("damage", actor=actor, value=-1), session.action("pay", actor=actor, value=8)],
        ]
        cases = [session.case([*start, *changes, session.action("eligibility_parity", mutate_result=True),
                               session.action("eligibility_parity"), session.action("claim")]) for changes in variants]
        results = self.invoke(cases)["cases"]
        for result in results:
            self.assert_parity(result)
        reasons = [result["observations"][-2]["value"]["inspection"]["eligibility"]["reason"] for result in results]
        self.assertEqual(reasons, ["actor_not_alive", "actor_not_alive", "no_living_foes", "ready", "ready"])
        self.assertEqual(results[3]["observations"][-2]["value"]["inspection"]["eligibility"]["friends"][0]["mp"], 4)
        self.assertFalse(results[0]["observations"][-1]["value"]["can_execute"])
        self.assertTrue(results[3]["observations"][-1]["value"]["can_execute"])

    # {
    #   責務: [test_projection_priority_and_deep_independence: 投影の敵なし優先と、返却キー/生存者ネストの原本独立性を確認します]
    #   処理: [1: 生存者列の空/非空と行動者生存の四条件を実行し、返却編集後も入力保持を照合します]
    #   引数: [self: 共用投影の独立結果を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_projection_priority_and_deep_independence(self):
        # 投影は検証済みの最新値を受け、外部要求の検証やSession予約の代わりにはしません。
        cases = []
        for alive in (False, True):
            for foes in ([], [turn.member("enemy")]):
                actor = turn.key("allies", "ally")
                friends = [turn.member("ally")] if alive else []
                cases.append(session.case([session.action("projection", actor=actor, actor_alive=alive, friends=friends, foes=foes)]))
        for index, result in enumerate(self.invoke(cases)["cases"]):
            value = result["observations"][0]["value"]
            self.assertTrue(value["input_preserved"])
            projected = value["projection"]
            alive, has_foes = index >= 2, index % 2 == 1
            reason = "ready" if alive and has_foes else ("actor_not_alive" if has_foes else "no_living_foes")
            self.assertEqual(projected["reason"], reason)
            self.assertEqual(projected["can_act"], reason == "ready")
            self.assertEqual(projected["stop"], not has_foes)
