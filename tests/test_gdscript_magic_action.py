"""実Godotの単体魔法をPython正本と比較し、専用コピーの資源・保存境界を検証する。"""
# {
#   責務: [test_gdscript_magic_action: 単体魔法の実MP支払い・HP適用・吸収回復と拒否時の非破壊性を検証します]
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
#   責務: [magic_hit: 通常魔法の専用プローブへ敵対象・スキルIDとケース別設定を渡す操作を作ります]
#   処理: [1: 魔法用の敵対象とスキルIDを明示した操作を作ります]
#   引数: [
#     changes: 敵対象・スキルID・揺らぎ・不正要求等のケース別設定（dict）
#   ]
#   戻り値: [result: 通常魔法の専用操作種別と要求設定を持つ辞書（dict）]
# }
def magic_hit(**changes):
    return {"kind": "magic", "target": normal.key("enemies", "enemy"), "skill_id": "weaken", **changes}

# {
#   責務: [magic_case: 開始情報を独立コピーし、単体魔法用の専用ケースを作ります]
#   処理: [1: 開始情報を独立コピーし、単体魔法用の専用ケースを作ります]
#   引数: [
#     source: 開始時の両陣営・習得・装備・耐性。Noneなら専用初期値（dictまたはNone）
#     steps: 明示操作列。Noneなら次行動取得と通常魔法1回（listまたはNone）
#     changes: 初期化・コピー編集等のケース別プローブ設定（dict）
#   ]
#   戻り値: [result: 開始情報の独立コピーと明示操作列を持つ魔法試験ケース（dict）]
# }
def magic_case(*, source=None, steps=None, **changes):
    source = normal.parameters() if source is None else copy.deepcopy(source)
    source.setdefault("skills", json.loads((fixture.ROOT / "data/skills/skills.json").read_text(encoding="utf-8")))
    source.setdefault("learned", {"allies": {"ally": ["weaken", "metal_burst"]},
                                  "enemies": {"enemy": ["weaken"]}})
    source.setdefault("resistances", {"allies": {"ally": {}}, "enemies": {"enemy": {}}})
    for definitions in source.get("equipment", {}).values():
        for equipment in definitions.values():
            if equipment:
                equipment.setdefault("allowed_species_ids", ["slime"])
    return normal.case(source, [{"kind": "next"}, magic_hit()] if steps is None else steps,
                       magic_skill=True, **changes)

# {
#   責務: [MagicActionTests: 実Godotの操作列とPython比較用の独立個体を使い、単体魔法と保存境界を検証します]
#   フィールド: [
#     content: 正規data/assetsの専用コピー
#     repository: 専用コピーを読むPythonデータ取得先
#     profile: 専用個体・AI・items・partyの保存先
#     engine: 学習せず数値比較だけに使うPython戦闘
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real magic actions")
class MagicActionTests(unittest.TestCase):
    setUp = normal.GDScriptNormalActionTests.setUp
    invoke = normal.GDScriptNormalActionTests.invoke
    byte_snapshot = normal.GDScriptNormalActionTests.byte_snapshot
    seed_state = normal.GDScriptNormalActionTests.seed_state
    seed_record = normal.GDScriptNormalActionTests.seed_record
    write = normal.GDScriptNormalActionTests.write

    # {
    #   責務: [_python_action: AI選択と揺らぎを固定し、実_take_actionのMP支払いと魔法のHP変化を取得します]
    #   処理: [1: 独立戦闘個体へ資源・装備・耐性を設定し、学習せず実Pythonの魔法行動を実行します]
    #   引数: [
    #     self: 専用コンテンツとPython比較先の所有者
    #     source: 比較する両陣営資源・装備・耐性（dict）
    #     definition: 選択した単体魔法定義（dict）
    #     variance: Pythonへ明示するダメージ揺らぎ（float）
    #     target_hp: 敵の比較時点HP。Noneなら開始情報のHP（intまたはNone）
    #     guard: 敵の基本防御倍率。魔法では軽減に使用しません（float）
    #   ]
    #   戻り値: [result: 実攻撃後の敵HP remaining_hpと術者MP remaining_mp（dict）]
    # }
    def _python_action(self, source, definition, variance, target_hp=None, guard=1.0):
        # AI選択だけを固定し、数値計算・支払い・適用は実_take_actionを使う。
        engine = turn.GDScriptTurnTests.engine(self, source["allies"], source["enemies"])
        actor, target = engine.allies[0], engine.enemies[0]
        actor.skills, actor.equipment = [definition], source["equipment"]["allies"]["ally"]
        target.resistances = source["resistances"]["enemies"]["enemy"]
        target.guard = guard
        if target_hp is not None:
            target.hp = target_hp
        records = copy.deepcopy([actor.record, target.record])
        engine.inference.choose = mock.Mock(return_value=definition)
        engine.learning.learn, engine.rng = mock.Mock(), mock.Mock()
        engine.rng.uniform.return_value = variance
        engine._take_action(actor, [target], [actor])
        engine.learning.learn.assert_not_called()
        engine.rng.random.assert_not_called()
        self.assertEqual(records, [actor.record, target.record])
        return {"remaining_hp": target.hp, "remaining_mp": actor.mp}

    # {
    #   責務: [test_real_damage_mp_immunity_and_absorption_match_python: 耐性・揺らぎ・装備固定加算・残HPを組み合わせ、実HPとMPをPythonへ照合します]
    #   処理: [1: 耐性・揺らぎ・装備固定加算・残HPを組み合わせ、実HPとMPをPythonへ照合します]
    #   引数: [
    #     self: 専用fixtureの所有者
    #   ]
    #   戻り値: [result: 検証失敗時は例外を返し、成功時はなし（None）]
    # }
    def test_real_damage_mp_immunity_and_absorption_match_python(self):
        cases, expected = [], []
        for resistance, variance, bonus, injured in itertools.product(
                ("weak", "normal", "strong", "immune", "absorb", "mod_unknown", None),
                (0.92, 1.08), (0, 11), (False, True)):
            source = normal.parameters(hp=100, equipment={"fixed_bonus_damage": bonus,
                "skill_modifiers": {"weaken": {"power_multiplier": 99}}})
            source["allies"][0]["stats"]["magic"] = 80
            item = magic_case(source=source)
            if resistance is not None:
                item["input"]["resistances"]["enemies"]["enemy"]["mental"] = resistance
            hp = 30 if injured else 100
            steps = [{"kind": "next"}]
            if injured:
                steps.append({"kind": "damage", "actor": normal.key("enemies", "enemy"), "amount": 70})
            steps.append(magic_hit(overrides={"variance": variance}, mutate_result=True))
            item["actions"] = steps
            definition = next(x for x in item["input"]["skills"]["skills"] if x["id"] == "weaken")
            expected.append(self._python_action(item["input"], definition, variance, hp))
            cases.append(item)
        for reference, observed in zip(expected, self.invoke(cases)["cases"]):
            with self.subTest(reference=reference):
                resolved = observed["observations"][-1]["value"]
                self.assertTrue(resolved["executed"], observed)
                self.assertEqual(resolved["spent_mp"], 5)
                for field, value in reference.items():
                    self.assertEqual(resolved["numbers"][field], value)
                self.assertEqual(observed["session"]["teams"]["enemies"][0]["hp"], reference["remaining_hp"])
                self.assertTrue(observed["input_preserved"])

    # {
    #   責務: [test_magic_ignores_basic_guard_but_retains_it_during_round: 基本ぼうぎょが単体魔法を軽減せず、非終端ラウンドの防御倍率は保持されることを確認します]
    #   処理: [1: 基本ぼうぎょが単体魔法を軽減せず、非終端ラウンドの防御倍率は保持されることを確認します]
    #   引数: [
    #     self: 専用fixtureの所有者
    #   ]
    #   戻り値: [result: 検証失敗時は例外を返し、成功時はなし（None）]
    # }
    def test_magic_ignores_basic_guard_but_retains_it_during_round(self):
        item = magic_case()
        source = item["input"]
        source["allies"][0]["stats"]["speed"], source["enemies"][0]["stats"]["speed"] = 10, 20
        extra = normal.member("extra", speed=1, hp=1000)
        source["enemies"].append(extra)
        source["shuffle_order"].append(normal.key("enemies", "extra"))
        item["basic_defend"] = True
        item["actions"] = [{"kind": "next"}, {"kind": "defend"}, {"kind": "next"}, magic_hit()]
        result = self.invoke([item])["cases"][0]
        resolved = result["observations"][-1]["value"]
        self.assertTrue(resolved["executed"], result)
        self.assertEqual(resolved["numbers"]["applied_guard"], 1)
        self.assertEqual(result["effects"]["teams"]["enemies"]["enemy"], 0.5)
        self.assertEqual(resolved["numbers"]["damage"], 5)

    # {
    #   責務: [test_invalid_requests_and_unsupported_effects_preserve_offered_resources: 不正要求・未習得・未対応定義や装備効果を拒否し、予約と資源の保持を確認します]
    #   処理: [1: 不正要求・未習得・未対応定義や装備効果を拒否し、予約と資源の保持を確認します]
    #   引数: [
    #     self: 専用fixtureの所有者
    #   ]
    #   戻り値: [result: 検証失敗時は例外を返し、成功時はなし（None）]
    # }
    def test_invalid_requests_and_unsupported_effects_preserve_offered_resources(self):
        cases = []
        for field, value in (("critical_roll", 0.5), ("guard", 0.5), ("current_mp", 999),
                             ("target_resistances", {}), ("variance", False),
                             ("variance", 0.91), ("variance", 1.09), ("skill_id", "attack"),
                             ("skill_id", "not_learned"), ("target", None),
                             ("target", normal.key("allies", "ally")),
                             ("target", normal.key("enemies", "missing"))):
            cases.append(magic_case(steps=[{"kind": "next"}, magic_hit(overrides={field: value})]))
        cases.extend(magic_case(steps=[{"kind": "next"}, magic_hit(special={"variance": value})])
                     for value in ("nan", "inf"))
        cases.append(magic_case(steps=[{"kind": "next"}, magic_hit(request=[])]))
        cases.append(magic_case(steps=[{"kind": "next"}, magic_hit(skill_id="metal_burst")]))
        for extra in ({"status": {}}, {"self_damage_ratio": 0}, {"target_all": False}):
            item = magic_case()
            next(x for x in item["input"]["skills"]["skills"] if x["id"] == "weaken").update(extra)
            cases.append(item)
        duplicate = magic_case()
        duplicate["input"]["skills"]["skills"].append(copy.deepcopy(next(
            x for x in duplicate["input"]["skills"]["skills"] if x["id"] == "weaken")))
        cases.append(duplicate)
        for modifier in ({"status": {}}, {"power_multiplier": False}, [], {"fixed_bonus_damage": 0}):
            cases.append(magic_case(source=normal.parameters(
                equipment={"skill_modifiers": {"weaken": modifier}})))
        cases.extend(magic_case(special_skill_id="weaken", definition_special={"power": special})
                     for special in ("nan", "inf"))
        for observed in self.invoke(cases)["cases"]:
            with self.subTest(reason=observed["observations"][-1]["value"]):
                self.assertTrue(observed["initialized"]["ok"], observed)
                self.assertFalse(observed["observations"][-1]["value"]["ok"], observed)
                self.assertEqual(observed["observations"][0]["session"], observed["session"])

    # {
    #   責務: [test_mp_insufficiency_keeps_offer_for_normal_attack_retry: 最新MP不足で魔法を拒否して予約を保持し、通常攻撃への変更を許可することを確認します]
    #   処理: [1: 最新MP不足で魔法を拒否して予約を保持し、通常攻撃への変更を許可することを確認します]
    #   引数: [
    #     self: 専用fixtureの所有者
    #   ]
    #   戻り値: [result: 検証失敗時は例外を返し、成功時はなし（None）]
    # }
    def test_mp_insufficiency_keeps_offer_for_normal_attack_retry(self):
        item = magic_case(steps=[{"kind": "next"},
            {"kind": "mp", "actor": normal.key("allies", "ally"), "cost": 3},
            magic_hit(), normal.hit()])
        observed = self.invoke([item])["cases"][0]["observations"]
        self.assertEqual(observed[2]["value"]["reason"], "insufficient_mp")
        self.assertEqual(observed[1]["session"], observed[2]["session"])
        self.assertTrue(observed[3]["value"]["executed"])
        self.assertEqual(observed[3]["session"]["teams"]["allies"][0]["mp"], 4)

    # {
    #   責務: [test_cancelled_dead_fled_or_no_foes_never_pay_mp: 予約後の死亡・逃走・敵不在で魔法を取り消し、MPを消費しないことを確認します]
    #   処理: [1: 予約後の死亡・逃走・敵不在で魔法を取り消し、MPを消費しないことを確認します]
    #   引数: [
    #     self: 専用fixtureの所有者
    #   ]
    #   戻り値: [result: 検証失敗時は例外を返し、成功時はなし（None）]
    # }
    def test_cancelled_dead_fled_or_no_foes_never_pay_mp(self):
        cases = []
        for action in ({"kind": "damage", "actor": normal.key("allies", "ally"), "amount": 30},
                       {"kind": "flee", "actor": normal.key("allies", "ally")},
                       {"kind": "damage", "actor": normal.key("enemies", "enemy"), "amount": 1000}):
            cases.append(magic_case(steps=[{"kind": "next"}, action, magic_hit()]))
        for observed in self.invoke(cases)["cases"]:
            self.assertTrue(observed["observations"][-1]["value"]["ok"], observed)
            self.assertFalse(observed["observations"][-1]["value"]["executed"])
            self.assertEqual(observed["session"]["teams"]["allies"][0]["mp"], 7)
            self.assertIsNone(observed["session"]["pending"])

    # {
    #   責務: [test_double_claim_and_dead_target_reject_without_partial_updates: 使用済み予約・取得済み予約・他の敵が生存中の死亡対象を拒否することを確認します]
    #   処理: [1: 使用済み予約・取得済み予約・他の敵が生存中の死亡対象を拒否することを確認します]
    #   引数: [
    #     self: 専用fixtureの所有者
    #   ]
    #   戻り値: [result: 検証失敗時は例外を返し、成功時はなし（None）]
    # }
    def test_double_claim_and_dead_target_reject_without_partial_updates(self):
        reused = magic_case(steps=[{"kind": "next"}, magic_hit(), magic_hit()])
        claimed = magic_case(steps=[{"kind": "next"}, {"kind": "claim"}, magic_hit()])
        dead_target = magic_case()
        dead_target["input"]["enemies"].append(normal.member("extra", speed=1, hp=1000))
        dead_target["input"]["shuffle_order"].append(normal.key("enemies", "extra"))
        dead_target["input"]["resistances"]["enemies"]["enemy"] = {"mental": "absorb"}
        dead_target["actions"] = [{"kind": "next"},
            {"kind": "damage", "actor": normal.key("enemies", "enemy"), "amount": 1000}, magic_hit()]
        for observed in self.invoke([reused, claimed, dead_target])["cases"]:
            self.assertFalse(observed["observations"][-1]["value"]["ok"], observed)
            self.assertEqual(observed["observations"][-2]["session"], observed["session"])

    # {
    #   責務: [test_finite_mod_numbers_and_independent_context_copies: 有限MOD変換と開始後の入力・出力コピー編集が、実行中の定義へ影響しないことを確認します]
    #   処理: [1: 有限MOD変換と開始後の入力・出力コピー編集が、実行中の定義へ影響しないことを確認します]
    #   引数: [
    #     self: 専用fixtureの所有者
    #   ]
    #   戻り値: [result: 検証失敗時は例外を返し、成功時はなし（None）]
    # }
    def test_finite_mod_numbers_and_independent_context_copies(self):
        cases, expected = [], []
        for power, cost, variance in itertools.product((-1.5, "1.3"), (3.9, "3"), (0.92, "1.08")):
            item = magic_case(steps=[{"kind": "next"}, magic_hit(overrides={"variance": variance})])
            definition = next(x for x in item["input"]["skills"]["skills"] if x["id"] == "weaken")
            definition.update(power=power, mp_cost=cost)
            expected.append(self._python_action(item["input"], definition, float(variance)))
            cases.append(item)
        for reference, observed in zip(expected, self.invoke(cases)["cases"]):
            self.assertTrue(observed["observations"][-1]["value"]["executed"], observed)
            for field, value in reference.items():
                self.assertEqual(observed["observations"][-1]["value"]["numbers"][field], value)
        item = magic_case(steps=[{"kind": "configure_magic"}, {"kind": "input_mutation"},
            {"kind": "next"}, magic_hit(mutate_result=True)], mutate_initial=True)
        item["input"]["resistances"]["enemies"]["enemy"] = {"mental": "normal"}
        observed = self.invoke([item])["cases"][0]
        self.assertEqual(observed["observations"][0]["value"]["reason"], "already_initialized")
        self.assertTrue(observed["observations"][-1]["value"]["executed"], observed)
        self.assertEqual(observed["session"]["teams"]["allies"][0]["mp"], 2)
        self.assertEqual(observed["observations"][-1]["value"]["numbers"]["damage"], 5)

    # {
    #   責務: [test_healing_caps_hp_and_rejects_invalid_values_without_unfleeing: 資源回復の最大HP・ゼロ量・不正値・逃走維持・未初期化を確認します]
    #   処理: [1: 資源回復の最大HP・ゼロ量・不正値・逃走維持・未初期化を確認します]
    #   引数: [
    #     self: 専用fixtureの所有者
    #   ]
    #   戻り値: [result: 検証失敗時は例外を返し、成功時はなし（None）]
    # }
    def test_healing_caps_hp_and_rejects_invalid_values_without_unfleeing(self):
        target = normal.key("enemies", "enemy")
        invalid = [-1, 1.2, True, "1", None, 9007199254740992]
        steps = [{"kind": "damage", "actor": target, "amount": 70},
                 {"kind": "heal", "actor": target, "amount": 0},
                 {"kind": "heal", "actor": target, "amount": 5},
                 {"kind": "heal", "actor": target, "amount": 9007199254740991},
                 {"kind": "heal", "actor": target, "amount": 1}]
        steps += [{"kind": "heal", "actor": target, "amount": value} for value in invalid]
        steps += [{"kind": "heal", "actor": target, "special": value} for value in ("nan", "inf")]
        steps += [{"kind": "heal", "actor": normal.key("enemies", "missing"), "amount": 1},
                  {"kind": "flee", "actor": target}, {"kind": "heal", "actor": target, "amount": 1}]
        observed = self.invoke([magic_case(source=normal.parameters(hp=100), steps=steps),
            magic_case(start_session=False, steps=[{"kind": "heal", "actor": target, "amount": 1}])])["cases"]
        operations = observed[0]["observations"]
        self.assertEqual([operations[i]["value"]["healed"] for i in (1, 2, 3, 4)], [0, 5, 65, 0])
        for index in range(5, 14):
            self.assertFalse(operations[index]["value"]["ok"])
            self.assertEqual(operations[index - 1]["session"], operations[index]["session"])
        self.assertFalse(operations[-1]["value"]["alive"])
        self.assertTrue(observed[0]["session"]["teams"]["enemies"][0]["fled"])
        self.assertEqual(observed[1]["observations"][0]["value"]["reason"], "not_initialized")

    # {
    #   責務: [test_resistance_steps_clamp_and_unknown_names_match_canonical_scale: 耐性段階の端点・未知名・省略と不正MODの拒否を検証します]
    #   処理: [1: 耐性段階の端点・未知名・省略と不正MODの拒否を検証します]
    #   引数: [
    #     self: 専用fixtureの所有者
    #   ]
    #   戻り値: [result: 検証失敗時は例外を返し、成功時はなし（None）]
    # }
    def test_resistance_steps_clamp_and_unknown_names_match_canonical_scale(self):
        scale = ["weak", "normal", "strong", "immune", "absorb"]
        cases, expected = [], []
        for base, delta in itertools.product(scale + ["unknown", None], (-10, -1, 0, 1, 10, "2", 1.9)):
            species = {"resistances": {} if base is None else {"fire": base}}
            cases.append(magic_case(steps=[{"kind": "resistance", "species": species,
                "equipment": {"resistance_steps": {"fire": delta}}}]))
            index = scale.index(base) if base in scale else 1
            expected.append(scale[max(0, min(4, index + int(delta)))])
        for value, observed in zip(expected, self.invoke(cases)["cases"]):
            self.assertEqual(observed["observations"][0]["value"]["resistances"], {"fire": value})
        bad = [({"resistances": []}, {}), ({"resistances": {"fire": False}}, {}),
               ({}, {"resistance_steps": []}), ({}, {"resistance_steps": {"fire": True}})]
        for observed in self.invoke([magic_case(steps=[{"kind": "resistance", "species": a, "equipment": b}])
                                     for a, b in bad])["cases"]:
            self.assertFalse(observed["observations"][0]["value"]["ok"])

    # {
    #   責務: [test_application_reconstructs_all_species_resistances_and_preserves_files: 7種族のレベル・許可装備の耐性をPythonへ照合し、専用個体やAIを変更しないことを確認します]
    #   処理: [1: 7種族のレベル・許可装備の耐性をPythonへ照合し、専用個体やAIを変更しないことを確認します]
    #   引数: [
    #     self: 専用fixtureの所有者
    #   ]
    #   戻り値: [result: 検証失敗時は例外を返し、成功時はなし（None）]
    # }
    def test_application_reconstructs_all_species_resistances_and_preserves_files(self):
        self.seed_record("owned", level=50)
        self.seed_state(current_party=["owned", None, None, None])
        self.write("items/items.json", {"items": {"herb": 19}, "private": True})
        self.write("parties/private.json", {"members": ["owned"]})
        loader = BattleDataLoader(self.repository)
        cases, references = [], []
        for species, level, gear in itertools.product(
                ("slime", "ball_slime", "metal_slime", "ghost", "maru", "kadoka", "dice_slime"),
                (1, 50, 100), (None, "wood_staff", "missing")):
            record = combatant.record("enemy", species_id=species, level=level, equipment_id=gear)
            source = {"allies": [combatant.record("ally", species_id="ghost", level=100)],
                      "enemies": [record], "shuffle_order": [normal.key("allies", "ally"), normal.key("enemies", "enemy")]}
            cases.append(magic_case(source=source, steps=[]))
            references.append(loader.build_combatant(MonsterRecord(record["monster"], record["ai"])))
        before = self.byte_snapshot()
        for target, observed in zip(references, self.invoke(joined=cases)["joined"]):
            with self.subTest(species=target.record.species_id, level=target.record.level):
                self.assertTrue(observed["initialized"]["ok"], observed)
                prepared = observed["initialized"]["preparation"]["teams"]["enemies"][0]
                self.assertEqual(prepared["resistances"], target.resistances)
                self.assertEqual(len(prepared["snapshot"]), 6)
        # 正規JSONでweakenを習得するボールスライムから、Lv1のまるへ魔法を実行する。
        item = magic_case(source={"allies": [combatant.record("ally", species_id="ball_slime", level=100)],
            "enemies": [combatant.record("enemy", species_id="maru", level=1)],
            "shuffle_order": [normal.key("allies", "ally"), normal.key("enemies", "enemy")]})
        observed = self.invoke(joined=[item])["joined"][0]
        self.assertTrue(observed["observations"][-1]["value"].get("executed"), observed)
        self.assertEqual(observed["observations"][-1]["value"]["spent_mp"], 5)
        self.assertEqual(self.byte_snapshot(), before)

    # {
    #   責務: [test_invalid_start_context_is_rejected_before_round: 未開始・資源不一致・不正耐性の開始情報を拒否します]
    #   処理: [1: 専用の不正開始ケースで初期化失敗と資源保持を確認します]
    #   引数: [self: 専用fixtureの所有者]
    #   戻り値: [result: 検証失敗時は例外、成功時はなし（None）]
    # }
    def test_invalid_start_context_is_rejected_before_round(self):
        cases = [magic_case(start_session=False, steps=[])]
        for invalid in (None, [], {"mental": False}, {"": "normal"}):
            item = magic_case(steps=[])
            item["input"]["resistances"]["enemies"]["enemy"] = invalid
            cases.append(item)
        mismatch = magic_case(steps=[])
        teams = {side: [{"snapshot": copy.deepcopy(member),
                        "skill_ids": ["weaken"], "equipment": {}, "resistances": {}}
                       for member in mismatch["input"][side]] for side in ("allies", "enemies")}
        teams["allies"][0]["snapshot"]["stats"]["magic"] += 1
        mismatch["magic_context"] = teams
        cases.append(mismatch)
        results = self.invoke(cases)["cases"]
        self.assertEqual(results[0]["initialized"]["reason"], "session_not_fresh")
        for observed in results[1:-1]:
            self.assertEqual(observed["initialized"]["reason"], "invalid_resistances")
        self.assertEqual(results[-1]["initialized"]["reason"], "magic_context_mismatch")
        self.assertTrue(all(x["session"]["round"] == 0 for x in results))

    # {
    #   責務: [test_eight_actors_with_same_ids_retain_mp_between_rounds: 両陣営同IDの8体が魔法を実行し、次ラウンドでも消費MPを保持することを確認します]
    #   処理: [1: 8行動と次ラウンドのMP不足を実行し、side/idごとの資源を照合します]
    #   引数: [self: 専用fixtureの所有者]
    #   戻り値: [result: 検証失敗時は例外、成功時はなし（None）]
    # }
    def test_eight_actors_with_same_ids_retain_mp_between_rounds(self):
        source = {"allies": [], "enemies": [], "equipment": {}, "learned": {"allies": {}, "enemies": {}},
                  "resistances": {"allies": {}, "enemies": {}}, "shuffle_order": []}
        steps = []
        for side in ("allies", "enemies"):
            for index in range(4):
                identifier = str(index)
                source[side].append(normal.member(identifier, speed=10, hp=1000))
                source["learned"][side][identifier] = ["weaken"]
                source["resistances"][side][identifier] = {}
                source["shuffle_order"].append(normal.key(side, identifier))
                target = normal.key("enemies" if side == "allies" else "allies", identifier)
                steps.extend([{"kind": "next"}, magic_hit(target=target)])
        steps.extend([{"kind": "begin"}, {"kind": "next"}, magic_hit(target=normal.key("enemies", "0"))])
        observed = self.invoke([magic_case(source=source, steps=steps)])["cases"][0]
        for members in observed["session"]["teams"].values():
            self.assertTrue(all(x["mp"] == 2 and x["hp"] == 995 for x in members))
        self.assertEqual(observed["observations"][-1]["value"]["reason"], "insufficient_mp")
        self.assertEqual(observed["observations"][-2]["session"], observed["session"])

    # {
    #   責務: [test_magic_dependencies_do_not_leak_io_ai_ui_or_developer_tools: 魔法engineと呼び出し層の責務境界を確認します]
    #   処理: [1: 禁止依存・委譲API・Playerと開発性能検査の分離を静的に照合します]
    #   引数: [self: 専用fixtureの所有者]
    #   戻り値: [result: 検証失敗時は例外、成功時はなし（None）]
    # }
    def test_magic_dependencies_do_not_leak_io_ai_ui_or_developer_tools(self):
        for name in ("magic_skill_context", "magic_skill_action", "elemental_resistance"):
            source = (fixture.ROOT / f"gdscript/engine/{name}.gd").read_text(encoding="utf-8")
            for token in ("FileAccess", "DirAccess", "OS.", "res://data/", "res://application/",
                          "res://ui/", "randf(", "RandomNumberGenerator", ".learn("):
                self.assertNotIn(token, source)
        application = (fixture.ROOT / "gdscript/application/battle_session_application.gd").read_text(encoding="utf-8")
        self.assertIn("_magic.resolve(request)", application)
        for token in (".pay_mp(", ".heal(", ".take_damage(", "Quote.quote_damage("):
            self.assertNotIn(token, application)
        for path in (fixture.ROOT / "gdscript/application").glob("*.gd"):
            self.assertNotIn("run_magic_action_performance", path.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
