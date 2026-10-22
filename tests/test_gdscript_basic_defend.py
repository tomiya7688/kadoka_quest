# {
#   責務: [test_gdscript_basic_defend: 実Godotの基本防御と終端解除を実Python正本および非破壊境界と比較する]
#   フィールド: [ROOT: 正規リポジトリの読取・headless起動用root。実セーブの読書きには使わない]
# }
"""Explicit basic defend parity; private fixtures only, no AI selection or completed BattleScene."""
from __future__ import annotations

import copy
import itertools
import json
import random
import unittest
from unittest import mock

import test_gdscript_combatant as combatant
import test_gdscript_normal_attack_action as normal
import test_gdscript_roster as fixture
import test_gdscript_turn_order as turn

ROOT = fixture.ROOT
key = turn.key


# {
#   責務: [defend: 明示防御プローブ操作を作る]
#   処理: [1: kindと追加のテスト条件を組み合わせる]
#   引数: [changes: 上書き・不正要求等のテスト条件]
#   戻り値: [result: プローブ操作辞書]
# }
def defend(**changes):
    return {"kind": "defend", **changes}


# {
#   責務: [case: 通常攻撃と基本防御を同じSessionへ設定するケースを作る]
#   処理: [1: 既存private fixture条件に防御設定フラグを付ける]
#   引数: [
#     parameters: 両陣営snapshot・正規定義等
#     actions: 明示操作列
#     changes: 初期化・コピー試験条件
#   ]
#   戻り値: [result: plainなプローブケース]
# }
def case(parameters=None, actions=None, **changes):
    return normal.case(parameters, [{"kind": "next"}, defend()] if actions is None else actions,
                       basic_defend=True, **changes)


# {
#   責務: [skills: 基本防御MOD用の正規形式の定義を作る]
#   処理: [1: 通常攻撃と指定のdefendだけを組み合わせる]
#   引数: [definition: defendの変更部分]
#   戻り値: [result: schema_version=1の文書]
# }
def skills(**definition):
    return {
        "schema_version": 1,
        "skills": [{"id": "attack", "kind": "physical"},
                   {"id": "defend", "kind": "defend", **definition}],
    }


# {
#   責務: [DefendBoundaryTests: 純粋処理・routing・実セーブ非依存と性能ツール境界を静的に検証する]
#   フィールド: []
# }
class DefendBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_pure_guard_ownership_and_routing_boundaries: 防御計算をUIやapplicationへ置かない境界を確認する]
    #   処理: [1: ソースの依存と委譲経路を確認する]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）]
    # }
    def test_pure_guard_ownership_and_routing_boundaries(self):
        for name in ("basic_defend_contract", "basic_defend_action", "battle_session"):
            source = (ROOT / f"gdscript/engine/{name}.gd").read_text(encoding="utf-8")
            for forbidden in ("FileAccess", "DirAccess", "OS.", "randf(", "randi(", "RandomNumberGenerator",
                              "res://data/", "res://ui/", "res://application/", ".learn("):
                self.assertNotIn(forbidden, source)
        source = (ROOT / "gdscript/application/battle_session_application.gd").read_text(encoding="utf-8")
        for forbidden in ("Numbers.", ".apply_defend(", ".take_damage(", "damage_multiplier"):
            self.assertNotIn(forbidden, source)
        self.assertIn("_defend.resolve(request)", source)
        self.assertIn('_session.guard(target)', (ROOT / "gdscript/engine/normal_attack_action.gd").read_text(encoding="utf-8"))
        self.assertNotIn("basic_defend", (ROOT / "gdscript/application/field_application.gd").read_text(encoding="utf-8"))
        for directory in ("src/kadoka_quest", "gdscript/application", "gdscript/ui"):
            for path in (ROOT / directory).rglob("*"):
                if path.suffix in (".py", ".gd"):
                    self.assertNotIn("check_gdscript_basic_defend", path.read_text(encoding="utf-8"))


# {
#   責務: [GDScriptDefendTests: 専用コピー上で実GodotとPythonの限定防御契約を比較する]
#   フィールド: [
#     content: コピーしたdata/assetsとprivateセーブのroot
#     repository: privateデータのみを読むPython参照
#     engine: AI学習を無効にした参照戦闘
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real basic-defend probes")
class GDScriptDefendTests(unittest.TestCase):
    setUp = normal.GDScriptNormalActionTests.setUp
    invoke = normal.GDScriptNormalActionTests.invoke
    byte_snapshot = normal.GDScriptNormalActionTests.byte_snapshot
    seed_state = fixture.GDScriptRosterTests.seed_state
    seed_record = fixture.GDScriptRosterTests.seed_record
    write = fixture.GDScriptRosterTests.write

    # {
    #   責務: [test_default_self_guard_and_resource_contract: 既定自己防御と資源6キー・本人だけの変更を確認する]
    #   処理: [1: 防御後と最後の行動後を比較する]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）]
    # }
    def test_default_self_guard_and_resource_contract(self):
        result = self.invoke([case(actions=[{"kind": "next"}, defend(), {"kind": "next"}, defend()])])["cases"][0]
        first = result["observations"][1]
        self.assertTrue(first["value"]["executed"])
        self.assertEqual(first["effects"]["teams"], {"allies": {"ally": 0.5}, "enemies": {"enemy": 1}})
        self.assertEqual(first["session"]["teams"], result["initialized"]["session"]["teams"])
        for members in first["session"]["teams"].values():
            self.assertEqual(set(members[0]), {"identity", "stats", "hp", "mp", "fled", "alive"})
        self.assertEqual(result["session"]["phase"], "round_finished")
        self.assertEqual(result["effects"]["teams"], {"allies": {"ally": 1}, "enemies": {"enemy": 1}})
        self.assertEqual(result["observations"][3]["value"]["applied_guard"], 0.5)

    # {
    #   責務: [_reference: 実_take_actionの防御後に実_attackを呼びHPと倍率を参照する]
    #   処理: [
    #     1: private snapshotからPython戦闘を構築する
    #     2: 選択だけを固定し実防御を実行する
    #     3: 明示乱数で実通常攻撃し個体AI不変を照合する
    #   ]
    #   引数: [
    #     self: テストインスタンス
    #     parameters: 両陣営・装備・倍率・乱数
    #   ]
    #   戻り値: [result: 期待dealt/remaining_hp/guard]
    # }
    def _reference(self, parameters):
        engine = turn.GDScriptTurnTests.engine(self, parameters["allies"], parameters["enemies"])
        actor, target = engine.allies[0], engine.enemies[0]
        records = copy.deepcopy([actor.record, target.record])
        rule = {"id": "defend", "kind": "defend", "display_name": "ぼうぎょ", "mp_cost": 0,
                "damage_multiplier": parameters["multiplier"]}
        target.skills = [rule]
        engine.inference.choose = mock.Mock(return_value=rule)  # Only selection, not the actual defend effect.
        engine.learning.learn = mock.Mock()
        engine._take_action(target, [actor], [target])
        self.assertEqual((target.hp, target.mp), (parameters["enemies"][0]["hp"], 7))
        self.assertEqual(target.guard, float(parameters["multiplier"]))
        actor.equipment = parameters["equipment"]["allies"]["ally"]
        engine.rng = mock.Mock()
        engine.rng.random.return_value, engine.rng.uniform.return_value = parameters["roll"], parameters["variance"]
        before = target.hp
        engine._attack(actor, target, self.repository.get_skills()["attack"], allow_counter=False)
        engine.learning.learn.assert_not_called()
        self.assertEqual([actor.record, target.record], records)
        return {"dealt": before - target.hp, "remaining_hp": target.hp, "applied_guard": target.guard}

    # {
    #   責務: [test_guarded_normal_critical_equipment_minimum_and_hp_cap_match_actual_python: 防御後の物理通常・会心数値を正本と比較する]
    #   処理: [1: 倍率・防御・会心・装備・揺らぎ・HPの組合せを比較する]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）]
    # }
    def test_guarded_normal_critical_equipment_minimum_and_hp_cap_match_actual_python(self):
        cases, inputs = [], []
        for atk, defense, roll, variance, hp, gear, multiplier in itertools.product(
                (0, 100), (0, 13, 100_000), (0, 1 / 16), (0.92, 1.08), (1, 1000),
                ({}, {"fixed_bonus_damage": 3}, {"skill_modifiers": {"attack": {"power_multiplier": 1.5}}}),
                (0.5, 0.3)):
            parameters = normal.parameters(attack=atk, defense=defense, hp=hp, equipment=gear,
                                           skills=skills(damage_multiplier=multiplier))
            parameters["enemies"][0]["stats"]["speed"] = 100
            cases.append(case(parameters, [{"kind": "next"}, defend(), {"kind": "next"},
                                           normal.hit(overrides={"critical_roll": roll, "variance": variance})]))
            inputs.append({**parameters, "roll": roll, "variance": variance, "multiplier": multiplier})
        for parameters, result in zip(inputs, self.invoke(cases)["cases"]):
            with self.subTest(parameters=parameters):
                resolved = result["observations"][3]["value"]
                self.assertTrue(resolved["executed"])
                for field, value in self._reference(parameters).items():
                    self.assertEqual(resolved["numbers"][field], value)
                self.assertTrue(all(value == 1 for team in result["effects"]["teams"].values() for value in team.values()))
                self.assertTrue(result["input_preserved"])

    # {
    #   責務: [test_before_defend_after_defend_next_round_and_physical_only: 防御の時点と次round解除および非物理数値境界を確認する]
    #   処理: [1: 防御前攻撃と防御後の物理/魔法/MP数値を比較して次roundへ進む]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）。魔法行動実装の証明ではない]
    # }
    def test_before_defend_after_defend_next_round_and_physical_only(self):
        parameters = normal.parameters()
        parameters["enemies"].append(normal.member("late", speed=1, hp=1000))
        parameters["shuffle_order"].append(key("enemies", "late"))
        steps = [{"kind": "next"}, normal.hit(), {"kind": "next"}, defend()]
        steps += [{"kind": "final_numbers", "target": key("enemies", "enemy"), "damage_kind": kind, "damage": 100}
                  for kind in ("physical", "magic", "drain_mp")]
        steps += [{"kind": "next"}, defend(), {"kind": "begin"}, {"kind": "next"}, normal.hit()]
        actual = self.invoke([case(parameters, steps)])["cases"][0]
        self.assertEqual(actual["observations"][1]["value"]["numbers"]["applied_guard"], 1)
        self.assertEqual([step["value"]["damage"] for step in actual["observations"][4:7]], [50, 100, 100])
        self.assertEqual(actual["observations"][8]["session"]["phase"], "round_finished")
        self.assertEqual(actual["observations"][11]["value"]["numbers"]["applied_guard"], 1)
        self.assertEqual(actual["session"]["teams"]["enemies"][0]["hp"], 810)

    # {
    #   責務: [test_invalid_requests_tickets_duplicates_stale_and_claimed_preserve_all_state: 不正要求で資源・guard・pendingを消費しないことを確認する]
    #   処理: [1: 拒否前後を比較し正しい要求での再試行と古いticket拒否を確認する]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_requests_tickets_duplicates_stale_and_claimed_preserve_all_state(self):
        overrides = [{"ticket": ticket} for ticket in (None, {}, {"round": 1, "slot": 0},
                     {"round": True, "slot": 0, "actor": key("allies", "ally")},
                     {"round": 1, "slot": 0.5, "actor": key("allies", "ally")},
                     {"round": "1", "slot": 0, "actor": key("allies", "ally")},
                     {"round": 1, "slot": 0, "actor": key("enemies", "enemy")},
                     {"round": 1, "slot": 0, "actor": key("allies", "ally"), "guard": 0.2})]
        overrides += [{field: value} for field, value in (("guard", 0.1), ("target", key("allies", "ally")),
                      ("damage_multiplier", 0.1), ("status", {}), ("skill_id", "counter"),
                      ("skill_id", None), ("skill_id", True), ("skill_id", 1), ("mp_cost", 0))]
        cases = [case(actions=[{"kind": "next"}, defend(overrides=value), defend()]) for value in overrides]
        cases += [case(actions=[{"kind": "next"}, defend(request=value), defend()]) for value in (None, [], {}, "defend")]
        for result in self.invoke(cases)["cases"]:
            with self.subTest(result=result):
                a, b, c = result["observations"]
                self.assertFalse(b["value"]["ok"])
                self.assertEqual((a["session"], a["effects"]), (b["session"], b["effects"]))
                self.assertTrue(c["value"]["executed"])
        steps = [{"kind": "next"}, defend(), defend(), {"kind": "next"}, defend(),
                 {"kind": "begin"}, {"kind": "next"},
                 defend(overrides={"ticket": {"round": 1, "slot": 0, "actor": key("allies", "ally")}}), defend()]
        cases = [case(actions=steps), case(actions=[{"kind": "next"}, {"kind": "claim"}, defend()]),
                 case(actions=[defend()])]
        stale, claimed, missing = self.invoke(cases)["cases"]
        self.assertFalse(stale["observations"][2]["value"]["ok"])
        self.assertEqual(stale["observations"][6]["effects"], stale["observations"][7]["effects"])
        self.assertEqual(stale["observations"][6]["session"], stale["observations"][7]["session"])
        self.assertTrue(stale["observations"][8]["value"]["executed"])
        self.assertFalse(claimed["observations"][2]["value"]["ok"])
        self.assertEqual(claimed["effects"]["teams"]["allies"]["ally"], 1)
        self.assertFalse(missing["observations"][0]["value"]["ok"])

    # {
    #   責務: [test_invalid_definitions_and_unknown_resource_fields_fail_closed: 未対応MOD・不正定義・資源拡張を黙って落とさないことを確認する]
    #   処理: [1: 初期化失敗でも倍率と資源を保持するか比較する]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_definitions_and_unknown_resource_fields_fail_closed(self):
        definitions = [{field: value} for field, value in (("kind", "magic"), ("kind", True),
                       ("mp_cost", 1), ("mp_cost", 0.5), ("mp_cost", True), ("mp_cost", "inf"),
                       ("damage_multiplier", True), ("damage_multiplier", None), ("damage_multiplier", []),
                       ("damage_multiplier", "nan"), ("damage_multiplier", "inf"), ("counter", False),
                       ("counter", True), ("protect_ally", True), ("status_effect", {}), ("power", 1),
                       ("display_name", 12), ("target", "self"))]
        documents = [skills(**definition) for definition in definitions]
        documents += [{}, None, [], {"schema_version": True, "skills": []},
                      {"schema_version": [], "skills": []}, {"schema_version": "1", "skills": []},
                      {"schema_version": 1, "skills": [skills()["skills"][0]]},
                      {"schema_version": 1, "skills": skills()["skills"] + [skills()["skills"][1]]},
                      {**skills(), "extra": True}]
        for result in self.invoke([case(normal.parameters(skills=document), []) for document in documents])["cases"]:
            self.assertFalse(result["initialized"]["ok"], result)
            self.assertEqual(result["session"]["phase"], "between_rounds")
            self.assertTrue(all(value == 1 for team in result["effects"]["teams"].values() for value in team.values()))
        specials = [case(normal.parameters(skills=skills()), [], definition_special={field: value})
                    for field in ("damage_multiplier", "mp_cost") for value in ("nan", "inf")]
        for result in self.invoke(specials)["cases"]:
            self.assertFalse(result["initialized"]["ok"])
            self.assertEqual(result["session"]["phase"], "between_rounds")
        invalid = normal.parameters()
        invalid["allies"][0]["guard"] = 0.5
        result = self.invoke([case(invalid, [])])["cases"][0]
        self.assertFalse(result["initialized"]["ok"])
        self.assertEqual(result["session"]["phase"], "not_started")
        self.assertEqual(result["effects"]["teams"], {"allies": {}, "enemies": {}})

    # {
    #   責務: [test_finite_mod_multipliers_and_overflow_keep_python_rules: 有限MOD倍率を勝手に修復せず演算超過時にclaimを消費しないことを確認する]
    #   処理: [1: ゼロ・負・1超・巨大倍率の攻撃結果を比較する]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）]
    # }
    def test_finite_mod_multipliers_and_overflow_keep_python_rules(self):
        cases = []
        for value in (0, -0.5, 1, 1.5, 1e308):
            parameters = normal.parameters(skills=skills(damage_multiplier=value))
            parameters["enemies"][0]["stats"]["speed"] = 100
            cases.append(case(parameters, [{"kind": "next"}, defend(), {"kind": "next"}, normal.hit()]))
        results = self.invoke(cases)["cases"]
        self.assertEqual([entry["observations"][3]["value"]["numbers"]["dealt"] for entry in results[:-1]], [1, 1, 95, 142])
        huge = results[-1]["observations"]
        self.assertFalse(huge[3]["value"]["ok"])
        self.assertEqual((huge[2]["session"], huge[2]["effects"]), (huge[3]["session"], huge[3]["effects"]))

    # {
    #   責務: [test_round_operation_failures_do_not_clear_active_guard_and_resources_survive: 不正進行ではguardを解除しない]
    #   処理: [1: guard保持中の拒否と正常末尾後のHP/MP保持を比較する]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）]
    # }
    def test_round_operation_failures_do_not_clear_active_guard_and_resources_survive(self):
        steps = [{"kind": "next"}, defend(), {"kind": "begin"}, {"kind": "finish"}, {"kind": "configure_defend"},
                 {"kind": "damage", "actor": key("allies", "ally"), "amount": 3},
                 {"kind": "mp", "actor": key("allies", "ally"), "cost": 2}, {"kind": "next"},
                 {"kind": "finish"}, {"kind": "begin", "order": []}, defend(),
                 {"kind": "begin", "order": []}, {"kind": "begin"}]
        actual = self.invoke([case(actions=steps)])["cases"][0]
        for index in (2, 3, 4, 8, 9):
            self.assertFalse(actual["observations"][index]["value"]["ok"])
            self.assertEqual(actual["observations"][index]["effects"]["teams"]["allies"]["ally"], 0.5)
        self.assertFalse(actual["observations"][11]["value"]["ok"])
        self.assertEqual(actual["session"]["round"], 2)
        ally = actual["session"]["teams"]["allies"][0]
        self.assertEqual((ally["hp"], ally["mp"]), (27, 5))
        self.assertEqual(actual["effects"]["teams"]["allies"]["ally"], 1)

    # {
    #   責務: [test_dead_fled_no_foes_and_skipped_tail_clear_at_terminal_only: 最新死亡・逃走・敵なしとskip末尾で倍率解除のタイミングを確認する]
    #   処理: [1: 資源変更直後は効果を保持し取消・next・finishで終端解除するか比較する]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）]
    # }
    def test_dead_fled_no_foes_and_skipped_tail_clear_at_terminal_only(self):
        cases = []
        for effect in ({"kind": "damage", "actor": key("allies", "ally"), "amount": 30},
                       {"kind": "flee", "actor": key("allies", "ally")},
                       {"kind": "damage", "actor": key("enemies", "enemy"), "amount": 1000}):
            cases.append(case(actions=[{"kind": "next"}, effect, defend()]))
        for result in self.invoke(cases)["cases"]:
            self.assertFalse(result["observations"][2]["value"]["executed"])
            self.assertEqual(result["session"]["phase"], "stopped")
            self.assertTrue(all(value == 1 for team in result["effects"]["teams"].values() for value in team.values()))
        steps = [{"kind": "next"}, defend(), {"kind": "next"},
                 {"kind": "flee", "actor": key("enemies", "enemy")}, defend()]
        result = self.invoke([case(actions=steps)])["cases"][0]
        self.assertEqual(result["observations"][3]["effects"]["teams"]["allies"]["ally"], 0.5)
        self.assertFalse(result["observations"][4]["value"]["executed"])
        self.assertEqual(result["effects"]["teams"]["allies"]["ally"], 1)
        parameters = normal.parameters()
        parameters["enemies"].append(normal.member("tail", speed=1))
        parameters["shuffle_order"].append(key("enemies", "tail"))
        steps = [{"kind": "next"}, defend(), {"kind": "damage", "actor": key("enemies", "tail"), "amount": 30},
                 {"kind": "next"}, defend(), {"kind": "next"}]
        result = self.invoke([case(parameters, steps)])["cases"][0]
        self.assertEqual(result["observations"][4]["effects"]["teams"]["allies"]["ally"], 0.5)
        self.assertEqual(result["session"]["phase"], "round_finished")
        self.assertEqual(result["effects"]["teams"]["allies"]["ally"], 1)
        for dead in (True, False):
            parameters = normal.parameters()
            parameters["allies"].append(normal.member("other", speed=15))
            parameters["shuffle_order"].append(key("allies", "other"))
            effect = ({"kind": "damage", "actor": key("allies", "ally"), "amount": 30} if dead else
                      {"kind": "flee", "actor": key("allies", "ally")})
            steps = [{"kind": "next"}, defend(), effect, {"kind": "next"}, defend(), {"kind": "next"}, defend()]
            result = self.invoke([case(parameters, steps)])["cases"][0]
            self.assertEqual(result["observations"][2]["effects"]["teams"]["allies"]["ally"], 0.5)
            engine = turn.GDScriptTurnTests.engine(self, parameters["allies"], parameters["enemies"])
            rule = self.repository.get_skills()["defend"]
            for actor in engine.allies + engine.enemies:
                actor.skills = [rule]
            engine.inference.choose = mock.Mock(return_value=rule)
            engine.learning.learn, engine._check_end, engine.rng = mock.Mock(), mock.Mock(), mock.Mock()
            original = engine._take_action

            # {
            #   責務: [perform_defend: 正本の防御直後に明示死亡/逃走を設定し末尾解除を比較する]
            #   処理: [1: 実_take_action後に本人の死亡/逃走フラグだけを変更する]
            #   引数: [
            #     actor: 実行個体
            #     foes: 最新生存敵
            #     friends: 最新生存味方
            #   ]
            #   戻り値: [result: なし（None）]
            # }
            def perform_defend(actor, foes, friends):
                original(actor, foes, friends)
                if actor is engine.allies[0]:
                    if dead:
                        actor.hp = 0
                    else:
                        actor.fled = True

            engine._take_action = mock.Mock(side_effect=perform_defend)
            engine.run_round()
            expected = [(actor.hp, actor.mp, actor.fled, actor.guard) for actor in engine.allies + engine.enemies]
            actual = [(actor["hp"], actor["mp"], actor["fled"], result["effects"]["teams"][side][actor["identity"]["id"]])
                      for side in ("allies", "enemies") for actor in result["session"]["teams"][side]]
            self.assertEqual(actual, expected)
            engine.learning.learn.assert_not_called()
        steps = [{"kind": "next"}, defend(), {"kind": "flee", "actor": key("enemies", "enemy")}, {"kind": "next"}]
        result = self.invoke([case(actions=steps)])["cases"][0]
        self.assertEqual(result["session"]["phase"], "stopped")
        self.assertEqual(result["effects"]["teams"]["allies"]["ally"], 1)

    # {
    #   責務: [test_direct_effect_contract_requires_claim_and_finite_multiplier: 所有者APIにも不正ticketと非有限guardの非破壊性を求める]
    #   処理: [1: 未claim・既claim・死亡および未知keyを直接試験する]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）]
    # }
    def test_direct_effect_contract_requires_claim_and_finite_multiplier(self):
        steps = [{"kind": "next"}, {"kind": "apply_defend"}, {"kind": "claim"}]
        steps += [{"kind": "apply_defend", "guard": value} for value in (True, None, [], "nan", "inf")]
        steps += [{"kind": "apply_defend", "special": value} for value in ("nan", "inf")]
        steps += [{"kind": "guard", "actor": value} for value in (None, {}, key("allies", "missing"))]
        steps += [{"kind": "apply_defend", "guard": 0.4}, {"kind": "finish"}]
        result = self.invoke([case(actions=steps)])["cases"][0]
        for index in [1, *range(3, 13)]:
            self.assertFalse(result["observations"][index]["value"]["ok"])
        self.assertEqual(result["observations"][13]["effects"]["teams"]["allies"]["ally"], 0.4)
        dead_steps = [{"kind": "next"}, {"kind": "claim"}, {"kind": "flee", "actor": key("allies", "ally")},
                      {"kind": "apply_defend"}]
        actual = self.invoke([case(actions=dead_steps)])["cases"][0]
        self.assertFalse(actual["observations"][3]["value"]["ok"])
        self.assertEqual(actual["effects"]["teams"]["allies"]["ally"], 1)

    # {
    #   責務: [test_context_and_plain_copies_are_independent_across_individuals_and_rounds: 同IDの別陣営・入力・出力コピーの独立性を確認する]
    #   処理: [1: コピー編集とMOD定義変更後にも開始時の倍率だけを使うか照合する]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）]
    # }
    def test_context_and_plain_copies_are_independent_across_individuals_and_rounds(self):
        parameters = normal.parameters(skills=skills(damage_multiplier="0.25"))
        for side in ("allies", "enemies"):
            parameters[side][0]["identity"]["id"] = "shared"
        parameters["shuffle_order"] = [key("allies", "shared"), key("enemies", "shared")]
        steps = [{"kind": "input_mutation"}, {"kind": "next", "mutate_result": True},
                 defend(mutate_result=True, mutate_effects=True), {"kind": "next"}, defend(),
                 {"kind": "begin", "order": [key("allies", "shared"), key("enemies", "shared")]},
                 {"kind": "next"}, defend()]
        actual = self.invoke([case(parameters, steps, mutate_initial=True), case(start_session=False)])["cases"]
        self.assertEqual(actual[0]["observations"][2]["effects"]["teams"],
                         {"allies": {"shared": 0.25}, "enemies": {"shared": 1}})
        self.assertEqual(actual[0]["observations"][4]["effects"]["teams"], {"allies": {"shared": 1}, "enemies": {"shared": 1}})
        self.assertEqual(actual[0]["effects"]["teams"]["allies"]["shared"], 0.25)
        self.assertEqual(actual[1]["session"]["phase"], "not_started")

    # {
    #   責務: [test_eight_actors_ties_three_rounds_deaths_and_terminal_match_actual_python: 実run_round内の基本防御・攻撃・終端解除を8体で比較する]
    #   処理: [1: 選択と終了保存だけを固定し複数roundの資源と効果を比較する]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）。AI推論・勝敗保存は比較対象外]
    # }
    def test_eight_actors_ties_three_rounds_deaths_and_terminal_match_actual_python(self):
        cases, expectations = [], []
        for seed in range(16):
            generator = random.Random(seed)
            teams = [[normal.member(str(index), speed=generator.choice((0, 1, 5)), hp=200 if seed % 2 else 3)
                      for index in range(4)] for _ in range(2)]
            parameters = turn.request(*teams)
            engine = turn.GDScriptTurnTests.engine(self, *teams)
            engine.rng = mock.Mock()
            engine.rng.random.return_value, engine.rng.uniform.return_value = (0 if seed % 3 else 0.5), 1.0
            engine.learning.learn, engine._check_end = mock.Mock(), mock.Mock()
            steps, events, rounds = [], [], [0]
            original = engine._take_action

            # {
            #   責務: [shuffled: Pythonの実shuffle入力をGodotへ明示する]
            #   処理: [1: sideをobject identityで区別し順列を記録する]
            #   引数: [actors: 実run_roundが渡す行動候補]
            #   戻り値: [result: なし（None）]
            # }
            def shuffled(actors):
                generator.shuffle(actors)
                order = [key("allies" if any(entry is actor for entry in engine.allies) else "enemies",
                             actor.record.monster_id) for actor, _, _ in actors]
                if rounds[0] == 0:
                    parameters["shuffle_order"] = order
                else:
                    steps.append({"kind": "begin", "order": order})
                rounds[0] += 1

            # {
            #   責務: [perform: 明示選択の下で正本の防御または通常攻撃を実行する]
            #   処理: [1: 実処理を呼び直後のguardとHPをGodot比較用に記録する]
            #   引数: [
            #     actor: 最新生存が確認された実行個体
            #     foes: 最新生存敵
            #     friends: 最新生存味方
            #   ]
            #   戻り値: [result: なし（None）]
            # }
            def perform(actor, foes, friends):
                side = "allies" if any(entry is actor for entry in engine.allies) else "enemies"
                steps.append({"kind": "next"})
                if (int(actor.record.monster_id) + rounds[0]) % 3 == 0:
                    rule = self.repository.get_skills()["defend"]
                    actor.skills = [rule]
                    engine.inference.choose = mock.Mock(return_value=rule)
                    original(actor, foes, friends)
                    steps.append(defend())
                else:
                    target = foes[0]
                    engine._attack(actor, target, self.repository.get_skills()["attack"], allow_counter=False)
                    steps.append(normal.hit(key("enemies" if side == "allies" else "allies", target.record.monster_id),
                                            overrides={"critical_roll": engine.rng.random.return_value}))
                events.append((key(side, actor.record.monster_id),
                               [[member.hp for member in team] for team in (engine.allies, engine.enemies)]))

            engine.rng.shuffle.side_effect = shuffled
            engine._take_action = mock.Mock(side_effect=perform)
            for _ in range(3):
                engine.run_round()
                self.assertTrue(all(actor.guard == 1 for actor in engine.allies + engine.enemies))
                steps.append({"kind": "next"})
                if not engine._living(engine.allies) or not engine._living(engine.enemies):
                    break
            engine.learning.learn.assert_not_called()
            cases.append(case(parameters, steps))
            expectations.append((events, [[actor.hp for actor in team] for team in (engine.allies, engine.enemies)]))
        for actual, (events, hp) in zip(self.invoke(cases)["cases"], expectations):
            resolved = [entry for entry in actual["observations"] if entry["value"].get("executed")]
            self.assertEqual([(entry["value"]["ticket"]["actor"],
                               [[member["hp"] for member in entry["session"]["teams"][side]]
                                for side in ("allies", "enemies")])
                              for entry in resolved], events)
            self.assertEqual([[member["hp"] for member in actual["session"]["teams"][side]]
                              for side in ("allies", "enemies")], hp)
            self.assertTrue(all(value == 1 for team in actual["effects"]["teams"].values() for value in team.values()))

    # {
    #   責務: [test_readonly_application_preserves_individual_ai_parties_items_and_originals: 正規データ経路と失敗時の未初期化・byte不変を確認する]
    #   処理: [1: private保存コピーで防御と攻撃を実行しMOD未対応時の非破壊拒否も確認する]
    #   引数: [self: テストインスタンス]
    #   戻り値: [result: なし（None）]
    # }
    def test_readonly_application_preserves_individual_ai_parties_items_and_originals(self):
        self.seed_state(current_party=["owned", None, None, None], private={"keep": True})
        owned = self.seed_record("owned", level=100)
        ai = {"schema_version": 1, "battles": 12, "action_preferences": {"defend": 0.7}, "private": [1, 2]}
        self.write("monsters/owned/ai.json", ai)
        self.write("items/items.json", {"herb": 99, "private": True})
        self.write("parties/private.json", {"members": ["owned"]})
        parameters = {"allies": [{"monster": owned, "ai": ai}], "enemies": [combatant.record("enemy", level=100)],
                      "shuffle_order": [key("allies", "owned"), key("enemies", "enemy")]}
        before = self.byte_snapshot()
        steps = [{"kind": "next"}, defend(), {"kind": "next"}, normal.hit(key("allies", "owned"))]
        actual = self.invoke(joined=[case(parameters, steps)])["joined"][0]
        self.assertTrue(actual["initialized"]["ok"], actual)
        self.assertEqual(actual["observations"][1]["effects"]["teams"]["allies"]["owned"], 0.5)
        self.assertEqual(actual["observations"][3]["value"]["numbers"]["applied_guard"], 0.5)
        self.assertEqual(self.byte_snapshot(), before)
        document = skills(counter=True)
        path = self.content / "data/skills/skills.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        before = self.byte_snapshot()
        rejected = self.invoke(joined=[case(parameters, [])])["joined"][0]
        self.assertFalse(rejected["initialized"]["ok"])
        self.assertEqual(rejected["session"]["phase"], "not_started")
        self.assertEqual(rejected["effects"]["teams"], {"allies": {}, "enemies": {}})
        self.assertEqual(self.byte_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
