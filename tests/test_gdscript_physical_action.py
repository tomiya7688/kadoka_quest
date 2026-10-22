"""実GodotのMP付き単体物理行動を正本Pythonと専用コピーで検証する。"""
# {
#   責務: [test_gdscript_physical_action: MP付き物理行動のPython比較と非破壊性検証]
#   フィールド: []
# }
from __future__ import annotations

import copy
import itertools
import json
import unittest
from unittest import mock

import test_gdscript_normal_attack_action as normal
import test_gdscript_roster as fixture
import test_gdscript_combatant as combatant
import test_gdscript_turn_order as turn
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.battle_data import BattleDataLoader
# {
#   責務: [physical_case: 独立した正規定義と習得・装備を持つ物理行動ケースを作る]
#   処理: [
#     1: 正規skillsと開始情報をコピーする
#     2: 物理行動のプローブ設定を返す
#   ]
#   引数: [
#     source: 両陣営の専用入力
#     steps: 明示操作列
#     changes: ケース別の設定
#   ]
#   戻り値: [result: 独立ケース（dict）]
# }

def physical_case(*, source=None, steps=None, **changes):
    # 各ケースで正規skillsと習得情報を独立させ、通常攻撃に偽装しない。
    source = normal.parameters() if source is None else copy.deepcopy(source)
    source.setdefault("skills", json.loads((fixture.ROOT / "data/skills/skills.json").read_text(encoding="utf-8")))
    source.setdefault("learned", {"allies": {"ally": ["body_bash", "roll", "poke"]},
                                  "enemies": {"enemy": ["body_bash", "roll", "poke"]}})
    for side, equipment in source.get("equipment", {}).items():
        for definition in equipment.values():
            if definition:
                definition.setdefault("allowed_species_ids", ["slime"])
    return normal.case(source, [{"kind": "next"}, physical_hit()] if steps is None else steps,
                       physical_skill=True, **changes)
# {
#   責務: [physical_hit: 通常攻撃と別の物理スキル要求を作る]
#   処理: [1: 対象・IDとケース別設定を結合する]
#   引数: [changes: ケース別要求]
#   戻り値: [result: 明示操作（dict）]
# }

def physical_hit(**changes):
    # IDと対象を明示し、数値上書きは乱数だけを基準にする。
    return {"kind": "physical", "target": normal.key("enemies", "enemy"), "skill_id": "body_bash", **changes}

# {
#   責務: [PhysicalActionBoundaryTests: 依存境界と開発用検査の分離を確認する]
#   フィールド: []
# }
class PhysicalActionBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_pure_resolver_and_developer_measurement_do_not_cross_runtime_layers: 純粋engine・routing・開発検査の依存境界を確認する]
    #   処理: [1: 禁止依存と専用API・性能検査の分離を確認する]
    #   引数: [self: 境界検証ケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_pure_resolver_and_developer_measurement_do_not_cross_runtime_layers(self):
        # engineにI/O・AI・乱数源・UIを足さず、applicationに実計算を持たせない。
        for name in ("physical_skill_action", "physical_skill_context"):
            source = (fixture.ROOT / f"gdscript/engine/{name}.gd").read_text(encoding="utf-8")
            for token in ("FileAccess", "DirAccess", "OS.", "res://data/", "res://application/",
                          "res://ui/", "randf(", "RandomNumberGenerator", ".learn(", "Numbers.normal_attack("):
                self.assertNotIn(token, source)
        application = (fixture.ROOT / "gdscript/application/battle_session_application.gd").read_text(encoding="utf-8")
        self.assertIn("_physical.resolve(request)", application)
        for token in (".pay_mp(", ".take_damage(", "Quote.quote_damage("):
            self.assertNotIn(token, application)
        tool = (fixture.ROOT / "tools/performance-check/script/check_gdscript_physical_action.py").read_text(encoding="utf-8")
        self.assertIn('result["microseconds"] <= 3000', tool)
        for path in (fixture.ROOT / "gdscript/application").glob("*.gd"):
            self.assertNotIn("check_gdscript_physical_action", path.read_text(encoding="utf-8"))

# {
#   責務: [PhysicalActionTests: 専用fixture・Python比較・実Godot観測を所有する]
#   フィールド: [
#     content: 元data/assetsの専用コピー
#     repository: 専用コピーのPython読込先
#     engine: 学習しないPython比較用戦闘
#     profile: 専用個体・AI・items・partyの保存先
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real physical actions")
class PhysicalActionTests(unittest.TestCase):
    setUp = normal.GDScriptNormalActionTests.setUp
    invoke = normal.GDScriptNormalActionTests.invoke
    byte_snapshot = normal.GDScriptNormalActionTests.byte_snapshot
    seed_state = normal.GDScriptNormalActionTests.seed_state
    seed_record = normal.GDScriptNormalActionTests.seed_record
    write = normal.GDScriptNormalActionTests.write
    # {
    #   責務: [_python_action: 選択だけを固定し実PythonのMP支払いと物理行動を比較する]
    #   処理: [
    #     1: 独立した戦闘個体と乱数を用意する
    #     2: 実_take_actionを呼ぶ
    #     3: 個体とAIの不変を確認する
    #   ]
    #   引数: [
    #     self: 専用fixtureの所有者
    #     source: 両陣営・装備の入力
    #     definition: 選択スキル
    #     roll: 会心乱数
    #     variance: 揺らぎ
    #     guard: 対象の物理防御倍率
    #   ]
    #   戻り値: [result: HP/MP/会心の期待値（dict）]
    # }

    def _python_action(self, source, definition, roll, variance, guard=1.0):
        # AI選択だけを固定する。MP支払いと物理行動は実_take_actionを呼ぶ。
        engine = turn.GDScriptTurnTests.engine(self, source["allies"], source["enemies"])
        actor, target = engine.allies[0], engine.enemies[0]
        actor.skills = [definition]
        actor.equipment = source["equipment"]["allies"]["ally"]
        target.guard = guard
        records = copy.deepcopy([actor.record, target.record])
        engine.inference.choose = mock.Mock(return_value=definition)
        engine.learning.learn = mock.Mock()
        engine.rng = mock.Mock()
        engine.rng.random.return_value = roll
        engine.rng.uniform.return_value = variance
        engine._take_action(actor, [target], [actor])
        # 個体/AIの保存や学習は比較の対象外であり、呼ばれていないことを確認する。
        engine.learning.learn.assert_not_called()
        self.assertEqual([actor.record, target.record], records)
        return {"remaining_hp": target.hp, "remaining_mp": actor.mp,
                "critical": any("会心" in message for message in engine.log)}
    # {
    #   責務: [test_canonical_skills_apply_real_mp_and_hp_like_python: 正規3スキルの実MP消費とHP適用をPythonと比較する]
    #   処理: [1: 専用fixtureで明示操作を実行し期待値と不変条件を確認する]
    #   引数: [self: 専用fixtureの所有者]
    #   戻り値: [result: なし（None）]
    # }

    def test_canonical_skills_apply_real_mp_and_hp_like_python(self):
        # 正規3スキル・会心境界・guard・揺らぎ・装備ID別補正・HP上限を比較する。
        cases, expectations = [], []
        for skill_id, roll, variance, hp, gear, guard in itertools.product(
                ("body_bash", "roll", "poke"), (0.0, 1 / 16, 0.999), (0.92, 1.08),
                (1, 1000), (False, True), (False, True)):
            equipment = ({"fixed_bonus_damage": 3, "skill_modifiers": {
                "attack": {"power_multiplier": 99}, skill_id: {"power_multiplier": 1.5}}} if gear else {})
            source = normal.parameters(defense=50, hp=hp, equipment=equipment)
            source["enemies"][0]["stats"]["speed"] = 100 if guard else 10
            steps = ([{"kind": "next"}, {"kind": "defend"}, {"kind": "next"}] if guard else [{"kind": "next"}])
            steps.append(physical_hit(skill_id=skill_id, overrides={"critical_roll": roll, "variance": variance}))
            case = physical_case(source=source, steps=steps, basic_defend=True)
            definition = next(entry for entry in case["input"]["skills"]["skills"] if entry["id"] == skill_id)
            expectations.append(self._python_action(case["input"], definition, roll, variance, 0.5 if guard else 1.0))
            cases.append(case)
        for item, expected, observed in zip(cases, expectations, self.invoke(cases)["cases"]):
            with self.subTest(skill=item["actions"][-1]["skill_id"], expected=expected):
                result = observed["observations"][-1]["value"]
                self.assertTrue(result["executed"], observed)
                for key, value in expected.items():
                    self.assertEqual(result["numbers"][key], value)
                self.assertEqual(result["spent_mp"], result["numbers"]["mp_cost"])
                self.assertEqual(observed["session"]["teams"]["allies"][0]["mp"], expected["remaining_mp"])
                self.assertEqual(observed["session"]["teams"]["enemies"][0]["hp"], expected["remaining_hp"])
                self.assertIsNone(observed["session"]["pending"])
                self.assertTrue(observed["input_preserved"])
    # {
    #   責務: [test_invalid_requests_leave_resources_and_offered_ticket_available: 不正要求で資源とofferedを消費しないことを確認する]
    #   処理: [1: 専用fixtureで明示操作を実行し期待値と不変条件を確認する]
    #   引数: [self: 専用fixtureの所有者]
    #   戻り値: [result: なし（None）]
    # }

    def test_invalid_requests_leave_resources_and_offered_ticket_available(self):
        # 許されない上書き・乱数・対象を拒否しても同じticketで通常攻撃へ戻れる。
        bad = [physical_hit(request=value) for value in (None, [], {}, True)]
        for field in ("power", "guard", "current_mp", "equipment", "skill_ids", "attack_multiplier"):
            bad.append(physical_hit(overrides={field: 999}))
        for field, values in {"critical_roll": [-1, 1, True, None],
                              "variance": [0.91, 1.09, True, None],
                              "skill_id": ["attack", "defend", "small_heal", "not_learned", True, []],
                              "target": [normal.key("allies", "ally"), normal.key("enemies", "missing"), {}, True],
                              "ticket": [{}, {"round": 0}, True]}.items():
            bad.extend(physical_hit(overrides={field: value}) for value in values)
        bad.extend(physical_hit(special={field: value}) for field, value in itertools.product(
            ("critical_roll", "variance"), ("inf", "nan")))
        cases = [physical_case(steps=[{"kind": "next"}, operation, normal.hit()]) for operation in bad]
        for result in self.invoke(cases)["cases"]:
            with self.subTest(result=result["observations"][1]["value"]):
                offered, rejected, retried = result["observations"]
                self.assertFalse(rejected["value"]["ok"])
                self.assertEqual(rejected["session"], offered["session"])
                self.assertEqual(rejected["effects"], offered["effects"])
                self.assertTrue(retried["value"]["executed"])
    # {
    #   責務: [test_definition_and_equipment_effect_failures_do_not_consume_claim: 未知スキル効果と同ID装備効果をclaim前に拒否する]
    #   処理: [1: 専用fixtureで明示操作を実行し期待値と不変条件を確認する]
    #   引数: [self: 専用fixtureの所有者]
    #   戻り値: [result: なし（None）]
    # }

    def test_definition_and_equipment_effect_failures_do_not_consume_claim(self):
        # 選択スキルと同ID装備効果だけを検証し、未知効果を黙って無視しない。
        cases = []
        for changes in ({"mp_cost": 0}, {"mp_cost": -1}, {"kind": "magic"}, {"element": None},
                        {"status_effect": {}}, {"self_damage_ratio": 0}, {"target": "single"},
                        {"power": "nan"}, {"critical_multiplier": "inf"}):
            case = physical_case()
            definition = next(entry for entry in case["input"]["skills"]["skills"] if entry["id"] == "body_bash")
            definition.update(changes)
            cases.append(case)
        for definition in ({"damage_multiplier": 1}, {"status_effect": {}}, {"power_multiplier": "nan"}, False):
            source = normal.parameters(equipment={"skill_modifiers": {"body_bash": definition}})
            cases.append(physical_case(source=source))
        duplicate = physical_case()
        duplicate["input"]["skills"]["skills"].append(copy.deepcopy(duplicate["input"]["skills"]["skills"][2]))
        cases.append(duplicate)
        for result in self.invoke(cases)["cases"]:
            with self.subTest(result=result):
                self.assertTrue(result["initialized"]["ok"])
                self.assertFalse(result["observations"][1]["value"]["ok"])
                self.assertEqual(result["observations"][0]["session"], result["session"])
    # {
    #   責務: [test_current_mp_exact_cost_insufficiency_and_replay_are_non_destructive: 最新MP・ちょうど支払い・不足・重複の境界を確認する]
    #   処理: [1: 専用fixtureで明示操作を実行し期待値と不変条件を確認する]
    #   引数: [self: 専用fixtureの所有者]
    #   戻り値: [result: なし（None）]
    # }

    def test_current_mp_exact_cost_insufficiency_and_replay_are_non_destructive(self):
        # 最大MPでなく行動直前のMPを使う。成功・不足・既消費ticketの違いを確認する。
        actor = normal.key("allies", "ally")
        cases = [
            physical_case(steps=[{"kind": "next"}, {"kind": "mp", "actor": actor, "cost": 4},
                                 physical_hit(), physical_hit(), {"kind": "next"}, physical_hit()]),
            physical_case(steps=[{"kind": "next"}, {"kind": "mp", "actor": actor, "cost": 5},
                                 physical_hit(), normal.hit()]),
        ]
        exact, short = self.invoke(cases)["cases"]
        self.assertEqual(exact["observations"][2]["value"]["spent_mp"], 3)
        self.assertEqual(exact["observations"][2]["session"]["teams"]["allies"][0]["mp"], 0)
        for index in (3, 5):
            self.assertFalse(exact["observations"][index]["value"]["ok"])
            self.assertEqual(exact["observations"][index - 1]["session"], exact["observations"][index]["session"])
        self.assertEqual(short["observations"][2]["value"]["reason"], "insufficient_mp")
        self.assertEqual(short["observations"][1]["session"], short["observations"][2]["session"])
        self.assertTrue(short["observations"][3]["value"]["executed"])
    # {
    #   責務: [test_latest_death_flee_and_no_foes_cancel_without_mp_payment: 最新死亡・逃走・敵なしでMPを払わず取消する]
    #   処理: [1: 専用fixtureで明示操作を実行し期待値と不変条件を確認する]
    #   引数: [self: 専用fixtureの所有者]
    #   戻り値: [result: なし（None）]
    # }

    def test_latest_death_flee_and_no_foes_cancel_without_mp_payment(self):
        # offered後の生死を確認する。死亡対象でも敵が残る場合は取消でなく再選択の拒否になる。
        actor, enemy = normal.key("allies", "ally"), normal.key("enemies", "enemy")
        cases = []
        for change in ({"kind": "damage", "actor": actor, "amount": 999},
                       {"kind": "flee", "actor": actor}, {"kind": "damage", "actor": enemy, "amount": 9999},
                       {"kind": "flee", "actor": enemy}):
            cases.append(physical_case(steps=[{"kind": "next"}, change, physical_hit()]))
        for result in self.invoke(cases)["cases"]:
            with self.subTest(result=result):
                cancelled = result["observations"][-1]["value"]
                self.assertTrue(cancelled["ok"])
                self.assertFalse(cancelled["executed"])
                self.assertEqual(result["observations"][1]["session"]["teams"], result["session"]["teams"])
                self.assertIsNone(result["session"]["pending"])
        source = normal.parameters()
        source["enemies"].append(normal.member("other", hp=1000))
        source["shuffle_order"].append(normal.key("enemies", "other"))
        result = self.invoke([physical_case(source=source, steps=[{"kind": "next"},
                              {"kind": "damage", "actor": enemy, "amount": 9999}, physical_hit()])])["cases"][0]
        self.assertEqual(result["observations"][-1]["value"]["reason"], "target_not_alive")
        self.assertEqual(result["observations"][1]["session"], result["session"])
    # {
    #   責務: [test_context_permissions_freshness_and_copies_are_owned_once: 初期化時点・種族許可・コピー独立性を確認する]
    #   処理: [1: 専用fixtureで明示操作を実行し期待値と不変条件を確認する]
    #   引数: [self: 専用fixtureの所有者]
    #   戻り値: [result: なし（None）]
    # }

    def test_context_permissions_freshness_and_copies_are_owned_once(self):
        # 不正開始・二度目の開始・初期結果/原本/返却値の編集が資源を変えないことを確認する。
        not_started = physical_case(start_session=False)
        mismatch = physical_case(physical_context={"allies": [], "enemies": []})
        denied = physical_case(source=normal.parameters(equipment={"allowed_species_ids": ["ghost"]}))
        missing = physical_case()
        missing["input"]["learned"] = {}
        copied = physical_case(steps=[{"kind": "configure_physical"}, {"kind": "input_mutation"},
                                     {"kind": "next"}, physical_hit(mutate_result=True)], mutate_initial=True)
        results = self.invoke([not_started, mismatch, denied, missing, copied])["cases"]
        self.assertEqual(results[0]["initialized"]["reason"], "session_not_fresh")
        self.assertEqual(results[1]["initialized"]["reason"], "physical_context_mismatch")
        self.assertEqual(results[2]["initialized"]["reason"], "equipment_not_allowed")
        self.assertEqual(results[3]["observations"][-1]["value"]["reason"], "skill_not_learned")
        self.assertEqual(results[4]["observations"][0]["value"]["reason"], "already_initialized")
        self.assertEqual(results[4]["session"]["teams"]["allies"][0]["mp"], 4)
        self.assertTrue(results[4]["observations"][-1]["value"]["executed"])
    # {
    #   責務: [test_application_uses_level_plus_and_equipment_and_preserves_private_files: 正規レベル再構築と許可装備を使い専用ファイルの不変を確認する]
    #   処理: [1: 専用fixtureで明示操作を実行し期待値と不変条件を確認する]
    #   引数: [self: 専用fixtureの所有者]
    #   戻り値: [result: なし（None）]
    # }

    def test_application_uses_level_plus_and_equipment_and_preserves_private_files(self):
        # 正規JSON再構築・習得・装備不許可の経路を専用個体/AI/items/partyのbyte不変と比較する。
        owned = self.seed_record("owned", level=50, plus_choices=[], equipment_id="ken")
        self.seed_state(current_party=["owned", None, None, None])
        self.write("items/items.json", {"items": {"herb": 19}, "private": True})
        self.write("parties/private.json", {"members": ["owned"]})
        self.write("monsters/owned/ai.json", {"schema_version": 1, "battles": 123, "private": [9]})
        loader = BattleDataLoader(self.repository)
        cases, expected = [], []
        for level, equipment in itertools.product((1, 50, 100), (None, "ken", "wood_staff", "missing")):
            source = {"allies": [combatant.record("ally", level=level, equipment_id=equipment)],
                      "enemies": [combatant.record("enemy")],
                      "shuffle_order": [normal.key("allies", "ally"), normal.key("enemies", "enemy")]}
            actor = loader.build_combatant(MonsterRecord(source["allies"][0]["monster"], source["allies"][0]["ai"]))
            cases.append(physical_case(source=source, mutate_initial=True))
            # 正規再構築の装備・能力値を実Python行動へ渡し、MPだけでなくHPも比較する。
            target = loader.build_combatant(MonsterRecord(source["enemies"][0]["monster"], source["enemies"][0]["ai"]))
            numeric_source = normal.parameters(equipment=actor.equipment)
            for snapshot, member in zip((numeric_source["allies"][0], numeric_source["enemies"][0]), (actor, target)):
                snapshot["stats"] = copy.deepcopy(member.stats)
                snapshot["hp"], snapshot["mp"] = member.hp, member.mp
            reference = (self._python_action(numeric_source, self.repository.get_skills()["body_bash"], 0.5, 1.0)
                         if level >= 7 else None)
            expected.append((actor, reference))
        before = self.byte_snapshot()
        for (actor, reference), result in zip(expected, self.invoke(joined=cases)["joined"]):
            with self.subTest(level=actor.record.level, equipment=actor.equipment):
                self.assertTrue(result["initialized"]["ok"], result)
                resolved = result["observations"][-1]["value"]
                if actor.record.level < 7:
                    self.assertEqual(resolved["reason"], "skill_not_learned")
                    self.assertEqual(result["observations"][0]["session"], result["session"])
                else:
                    self.assertTrue(resolved["executed"], result)
                    self.assertEqual(result["session"]["teams"]["allies"][0]["mp"], actor.mp - 3)
                    self.assertEqual(resolved["numbers"]["skill_id"], "body_bash")
                    for key, value in reference.items():
                        self.assertEqual(resolved["numbers"][key], value)
                self.assertTrue(result["input_preserved"])
                self.assertNotIn("ai", result["session"]["teams"]["allies"][0])
        self.assertEqual(self.byte_snapshot(), before)

    # {
    #   責務: [test_finite_mod_conversion_and_plus_learned_skill_are_preserved: 有限MOD数値と＋からの習得を正本どおり扱う]
    #   処理: [
    #     1: 有限MODの威力・会心・MP変換を実Pythonと比較する
    #     2: 低レベル個体の正規＋選択で習得したスキルを実Godotで使う
    #   ]
    #   引数: [self: 専用fixtureの所有者]
    #   戻り値: [result: なし（None）]
    # }
    def test_finite_mod_conversion_and_plus_learned_skill_are_preserved(self):
        # 数値文字列は既存数値契約の許容入力。不正と混同して拒否しない。
        cases, references = [], []
        for power, critical, cost in itertools.product((-1.5, "1.3"), (-2.0, "2.0"), (3.9, "3")):
            item = physical_case(steps=[{"kind": "next"}, physical_hit(overrides={"critical_roll": "0.5", "variance": "1.0"})])
            definition = next(entry for entry in item["input"]["skills"]["skills"] if entry["id"] == "body_bash")
            definition.update(power=power, critical_multiplier=critical, mp_cost=cost)
            references.append(self._python_action(item["input"], definition, 0.5, 1.0))
            cases.append(item)
        for reference, result in zip(references, self.invoke(cases)["cases"]):
            with self.subTest(reference=reference):
                resolved = result["observations"][-1]["value"]
                self.assertTrue(resolved["executed"])
                for key, value in reference.items():
                    self.assertEqual(resolved["numbers"][key], value)
        # 正規の＋選択でLv1の未習得を補う。フィールドや保存を変更しない。
        source = {"allies": [combatant.record("ally", level=1, plus_choices=[
            "slime_plus_1_special", "slime_plus_2_special", "slime_plus_3_special", "slime_plus_4_special"])],
                  "enemies": [combatant.record("enemy")],
                  "shuffle_order": [normal.key("allies", "ally"), normal.key("enemies", "enemy")]}
        result = self.invoke(joined=[physical_case(source=source)])["joined"][0]
        self.assertTrue(result["initialized"]["ok"], result)
        self.assertIn("body_bash", result["initialized"]["preparation"]["teams"]["allies"][0]["skill_ids"])
        self.assertTrue(result["observations"][-1]["value"]["executed"], result)

    # {
    #   責務: [test_eight_actors_same_ids_keep_mp_between_rounds_and_insufficiency_can_retry: 両陣営同IDとラウンド間MP保持を確認する]
    #   処理: [
    #     1: 同速8体へ二ラウンドの物理行動を適用する
    #     2: 三ラウンド目のMP不足と通常攻撃への変更を確認する
    #   ]
    #   引数: [self: 専用fixtureの所有者]
    #   戻り値: [result: なし（None）]
    # }
    def test_eight_actors_same_ids_keep_mp_between_rounds_and_insufficiency_can_retry(self):
        # sideとidを組にする。同じIDを持つ相手のMPへ誤適用しない。
        source = {"allies": [], "enemies": [], "equipment": {}, "learned": {"allies": {}, "enemies": {}},
                  "shuffle_order": []}
        for side in ("allies", "enemies"):
            for index in range(4):
                identifier = str(index)
                source[side].append(normal.member(identifier, speed=10, hp=1000))
                source["learned"][side][identifier] = ["body_bash"]
                source["shuffle_order"].append(normal.key(side, identifier))
        steps = []
        for round_index in range(2):
            if round_index:
                steps.append({"kind": "begin"})
            for actor in source["shuffle_order"]:
                target = normal.key("enemies" if actor["side"] == "allies" else "allies", "0")
                steps.extend([{"kind": "next"}, physical_hit(target=target)])
        steps.extend([{"kind": "begin"}, {"kind": "next"}, physical_hit(target=normal.key("enemies", "0")),
                      normal.hit(normal.key("enemies", "0"))])
        observed = self.invoke([physical_case(source=source, steps=steps)])["cases"][0]
        for side in ("allies", "enemies"):
            self.assertTrue(all(member["mp"] == 1 for member in observed["session"]["teams"][side]))
        self.assertEqual(observed["observations"][-2]["value"]["reason"], "insufficient_mp")
        self.assertEqual(observed["observations"][-3]["session"], observed["observations"][-2]["session"])
        self.assertTrue(observed["observations"][-1]["value"]["executed"])

if __name__ == "__main__":
    unittest.main()
