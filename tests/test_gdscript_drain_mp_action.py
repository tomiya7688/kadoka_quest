"""吸MP魔法の実MP消費・敵HP/MP喪失・術者MP回復を実GodotとPython正本で比較します。"""
# {
#   責務: [test_gdscript_drain_mp_action: 一度だけの吸MP行動・厳密拒否・最新資源・数値回復・保存境界を検証します]
#   フィールド: []
# }
from __future__ import annotations

import copy
import itertools
import unittest
from unittest import mock

import test_gdscript_magic_action as magic
import test_gdscript_normal_attack_action as normal
import test_gdscript_roster as fixture
import test_gdscript_combatant as combatant
import test_gdscript_turn_order as turn
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.battle_data import BattleDataLoader


# {
#   責務: [drain_hit: 正規possessを敵へ要求する吸MP専用の試験操作を作ります]
#   処理: [1: 吸MP専用区分・敵対象・スキルIDとケース別設定をまとめます]
#   引数: [changes: 敵対象・揺らぎ・不正要求等のケース別設定（dict）]
#   戻り値: [result: 吸MP専用プローブ操作（dict）]
# }
def drain_hit(**changes):
    # 通常魔法入口へIDを偽装せず、吸MP専用入口を選びます。
    return {"kind": "drain_magic", "target": normal.key("enemies", "enemy"), "skill_id": "possess", **changes}


# {
#   責務: [drain_case: 満タンで開始する独立資源と、正規吸MP定義を使う専用ケースを作ります]
#   処理: [
#     1: 指定がなければ魔力100・術者MP100・敵MP80の新鮮な資源を作ります
#     2: 正規スキル一覧と習得情報を用意し、吸MP専用区分を選びます
#   ]
#   引数: [
#     source: 両陣営・装備・耐性の開始情報。Noneなら専用初期値（dictまたはNone）
#     steps: 明示操作列。Noneなら次行動取得と吸MP1回（listまたはNone）
#     changes: 初期化・コピー編集等のプローブ設定（dict）
#   ]
#   戻り値: [result: 開始情報の独立コピーを持つ専用ケース（dict）]
# }
def drain_case(*, source=None, steps=None, **changes):
    # 低い現在MPはSessionの開始検証を緩めず、開始後の数値減算で作ります。
    default_resources = source is None
    source = normal.parameters(hp=1000) if default_resources else copy.deepcopy(source)
    if "monster" not in source["allies"][0]:
        if default_resources:
            for side, maximum in (("allies", 100), ("enemies", 80)):
                source[side][0]["stats"].update(mp=maximum, magic=100)
                source[side][0]["mp"] = maximum
        source.setdefault("learned", {"allies": {"ally": ["possess", "weaken", "metal_burst"]},
                                      "enemies": {"enemy": ["possess"]}})
    return magic.magic_case(source=source, steps=[{"kind": "next"}, drain_hit()] if steps is None else steps,
                            drain_mp_magic=True, **changes)


# {
#   責務: [DrainMpActionTests: 専用保存/コンテンツと実Godot操作列を所有し、吸MP実適用をPythonへ照合します]
#   フィールド: [
#     content: 正規data/assetsを複製した一時コンテンツ領域（Path）
#     repository: 専用コピーを読むPythonリポジトリ
#     profile: 個体・AI・items・partyの一時保存先（Path）
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real drain-MP actions")
class DrainMpActionTests(unittest.TestCase):
    setUp = normal.GDScriptNormalActionTests.setUp
    invoke = normal.GDScriptNormalActionTests.invoke
    byte_snapshot = normal.GDScriptNormalActionTests.byte_snapshot
    seed_state = normal.GDScriptNormalActionTests.seed_state
    seed_record = normal.GDScriptNormalActionTests.seed_record
    write = normal.GDScriptNormalActionTests.write

    # {
    #   責務: [python_action: 選択と揺らぎだけを固定し、実_take_actionのMP支払いと吸MP効果を取得します]
    #   処理: [
    #     1: 独立した戦闘個体へ比較時点の最新資源・装備・耐性を設定します
    #     2: 学習せず実行し、敵HP/MP・術者MPと元個体の不変を確認します
    #   ]
    #   引数: [
    #     self: 専用Python比較先の所有者
    #     source: 比較時点の両陣営資源・装備・耐性（dict）
    #     definition: 有限値を持つ吸MP定義（dict）
    #     variance: Pythonへ明示する揺らぎ（float）
    #   ]
    #   戻り値: [result: 実攻撃後の敵HP/MP・術者MPと敵喪失/術者回復の別々の量（dict）]
    # }
    def python_action(self, source, definition, variance):
        # MPの支払い・攻撃計算・移転はmock化せず、実_take_actionを使います。
        engine = turn.GDScriptTurnTests.engine(self, source["allies"], source["enemies"])
        actor, target = engine.allies[0], engine.enemies[0]
        actor.skills, actor.equipment = [definition], source["equipment"]["allies"]["ally"]
        target.resistances = source["resistances"]["enemies"]["enemy"]
        target.guard = 0.5
        original = copy.deepcopy([actor.record, target.record])
        paid_mp, previous_target_mp = actor.mp - int(definition["mp_cost"]), target.mp
        engine.inference.choose = mock.Mock(return_value=definition)
        engine.learning.learn, engine.rng = mock.Mock(), mock.Mock()
        engine.rng.uniform.return_value = variance
        engine._take_action(actor, [target], [actor])
        engine.learning.learn.assert_not_called()
        engine.rng.random.assert_not_called()
        self.assertEqual(original, [actor.record, target.record])
        return {"remaining_hp": target.hp, "remaining_mp": actor.mp, "remaining_target_mp": target.mp,
                "drained_mp": previous_target_mp - target.mp, "recovered_mp": actor.mp - paid_mp}

    # {
    #   責務: [test_resistance_latest_resources_and_equipment_match_python: 耐性・最新HP/MP・揺らぎ・装備加算の実適用をPythonへ照合します]
    #   処理: [1: 満タン初期化後に資源を減らしたケースを実行し、予測・実資源・移転量を比較します]
    #   引数: [self: 最新資源の組合せを検証するテストケース]
    #   戻り値: [result: なし（None）。不一致はassertionで報告します]
    # }
    def test_resistance_latest_resources_and_equipment_match_python(self):
        # 術者満タン・敵MP0・最後の敵の撃破を含め、開始時の古いMPで吸収を決めません。
        cases, expected = [], []
        for resistance, current_mp, target_mp, hp, variance, bonus in itertools.product(
                ("weak", "normal", "strong", "immune", "absorb", "unknown", None),
                (5, 90, 100), (0, 7, 80), (1, 1000), (0.92, 1.08), (0, 11)):
            item = drain_case()
            source = item["input"]
            source["equipment"]["allies"]["ally"] = {"allowed_species_ids": ["slime"],
                "fixed_bonus_damage": bonus, "skill_modifiers": {"possess": {"power_multiplier": 99}}}
            if resistance is not None:
                source["resistances"]["enemies"]["enemy"]["mental"] = resistance
            item["actions"] = [{"kind": "next"},
                {"kind": "mp", "actor": normal.key("allies", "ally"), "cost": 100 - current_mp},
                {"kind": "mp", "actor": normal.key("enemies", "enemy"), "cost": 80 - target_mp},
                {"kind": "damage", "actor": normal.key("enemies", "enemy"), "amount": 1000 - hp},
                drain_hit(overrides={"variance": variance}, mutate_result=True)]
            latest = copy.deepcopy(source)
            latest["allies"][0]["mp"] = current_mp
            latest["enemies"][0].update(mp=target_mp, hp=hp)
            definition = next(entry for entry in source["skills"]["skills"] if entry["id"] == "possess")
            expected.append(self.python_action(latest, definition, variance))
            cases.append(item)
        for reference, observed in zip(expected, self.invoke(cases)["cases"]):
            with self.subTest(reference=reference):
                result = observed["observations"][-1]["value"]
                self.assertTrue(result.get("executed"), observed)
                self.assertEqual(result["scope"], "explicit_drain_mp_magic_only")
                self.assertEqual(result["spent_mp"], 5)
                for field, value in reference.items():
                    self.assertEqual(result["numbers"][field], value, field)
                for field in ("drained_mp", "recovered_mp"):
                    self.assertEqual(result[field], reference[field])
                actor, target = observed["session"]["teams"]["allies"][0], observed["session"]["teams"]["enemies"][0]
                self.assertEqual((target["hp"], target["mp"], actor["mp"]),
                                 (reference["remaining_hp"], reference["remaining_target_mp"], reference["remaining_mp"]))
                self.assertIsNone(observed["session"]["pending"])
                self.assertTrue(observed["input_preserved"])

    # {
    #   責務: [test_finite_mods_defaults_and_independent_copies: 有限MOD/既定値の実適用と、開始後のコピー編集が所有資源へ伝播しない契約を検証します]
    #   処理: [
    #     1: 文字列/負/0係数と既定値をPythonへ比較します
    #     2: 入出力コピーの編集が所有資源・定義・習得へ伝播しないか確認します
    #   ]
    #   引数: [self: MOD互換とコピー独立性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_finite_mods_defaults_and_independent_copies(self):
        cases, expected = [], []
        for rate, power, cost in itertools.product((None, -1, 0, "0", "0.2", 2), (-1.0, "0.25"), (3.9, "3")):
            item = drain_case()
            definition = next(entry for entry in item["input"]["skills"]["skills"] if entry["id"] == "possess")
            definition.update(power=power, mp_cost=cost)
            if rate is None:
                definition.pop("mp_power")
            else:
                definition["mp_power"] = rate
            expected.append(self.python_action(item["input"], definition, 1.0))
            cases.append(item)
        for reference, observed in zip(expected, self.invoke(cases)["cases"]):
            with self.subTest(reference=reference):
                result = observed["observations"][-1]["value"]
                self.assertTrue(result["executed"], observed)
                for field, value in reference.items():
                    self.assertEqual(result["numbers"][field], value)
        item = drain_case(steps=[{"kind": "configure_drain_magic"}, {"kind": "input_mutation"},
                                {"kind": "next"}, drain_hit(mutate_result=True)], mutate_initial=True)
        observed = self.invoke([item])["cases"][0]
        self.assertEqual(observed["observations"][0]["value"]["reason"], "already_initialized")
        self.assertTrue(observed["observations"][-1]["value"]["executed"], observed)
        self.assertEqual(observed["session"]["teams"]["enemies"][0]["mp"], 66)
        self.assertEqual(observed["session"]["teams"]["allies"][0]["mp"], 100)

    # {
    #   責務: [test_invalid_requests_effects_numbers_and_equipment_keep_offer: 不正要求・未知効果・非有限数値・未対応装備をclaim前に拒否するか確認します]
    #   処理: [1: 不正値を一箇所ずつ追加し、拒否後の予約と資源が保持されるか確認します]
    #   引数: [self: 吸MP対応範囲の境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_requests_effects_numbers_and_equipment_keep_offer(self):
        cases = []
        for field, value in (("target_mp", 999), ("actor_max_mp", 999), ("current_mp", 999),
                             ("drained_mp", 0), ("recovered_mp", False), ("guard", 0.5),
                             ("equipment", {}), ("mp_power", 0), ("critical_roll", 0),
                             ("variance", False), ("variance", 0.91), ("variance", 1.09),
                             ("skill_id", "attack"), ("skill_id", "missing"), ("target", None),
                             ("target", normal.key("allies", "ally")), ("target", normal.key("enemies", "missing"))):
            cases.append(drain_case(steps=[{"kind": "next"}, drain_hit(overrides={field: value})]))
        cases += [drain_case(steps=[{"kind": "next"}, drain_hit(request=[])]),
                  drain_case(steps=[{"kind": "next"}, drain_hit(skill_id="weaken")])]
        for field, value in itertools.product(("mp_power", "self_damage_ratio", "status", "target_all", "unknown"), (0, False, [])):
            item = drain_case()
            next(entry for entry in item["input"]["skills"]["skills"] if entry["id"] == "possess")[field] = value
            if field == "mp_power" and value is not False and value != []:
                continue
            cases.append(item)
        for value in (None, True, "NaN", "Inf", 2**53):
            item = drain_case()
            next(entry for entry in item["input"]["skills"]["skills"] if entry["id"] == "possess")["mp_power"] = value
            cases.append(item)
        cases += [drain_case(special_skill_id="possess", definition_special={"mp_power": value}) for value in ("nan", "inf")]
        cases += [drain_case(steps=[{"kind": "next"}, drain_hit(special={"variance": value})]) for value in ("nan", "inf")]
        for modifier in ({"unknown": 0}, {"power_multiplier": True}, []):
            item = drain_case()
            item["input"]["equipment"]["allies"]["ally"] = {"allowed_species_ids": ["slime"], "skill_modifiers": {"possess": modifier}}
            cases.append(item)
        duplicate = drain_case()
        duplicate["input"]["skills"]["skills"].append(copy.deepcopy(next(
            entry for entry in duplicate["input"]["skills"]["skills"] if entry["id"] == "possess")))
        cases.append(duplicate)
        unlearned = drain_case()
        unlearned["input"]["learned"]["allies"]["ally"] = ["weaken"]
        cases.append(unlearned)
        for observed in self.invoke(cases)["cases"]:
            with self.subTest(reason=observed["observations"][-1]["value"]):
                self.assertTrue(observed["initialized"]["ok"], observed)
                self.assertFalse(observed["observations"][-1]["value"]["ok"], observed)
                self.assertEqual(observed["observations"][0]["session"], observed["session"])
        # 通常/自傷入口では吸MPを黙って省略しません。複合モードも開始前に拒否します。
        item = drain_case(self_damage_magic=True, steps=[{"kind": "next"},
                          magic.magic_hit(skill_id="possess"), {"kind": "self_magic", "skill_id": "possess", "target": normal.key("enemies", "enemy")}])
        observed = self.invoke([item, drain_case(conflicting_magic=True, steps=[])])["cases"]
        self.assertTrue(all(not entry["value"]["ok"] for entry in observed[0]["observations"][1:]))
        self.assertEqual(observed[1]["initialized"]["reason"], "invalid_magic_mode")

    # {
    #   責務: [test_insufficiency_and_cancellation_do_not_consume_or_transfer_mp: 最新MP不足は予約を保持し、最新死亡/逃走/敵なしは不消費で取消すか確認します]
    #   処理: [
    #     1: 最新MP不足後に通常攻撃へ再選択できるか確認します
    #     2: 予約後の死亡・逃走・敵なしの取消でMPが変化しないか確認します
    #   ]
    #   引数: [self: 最新の実行可否を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_insufficiency_and_cancellation_do_not_consume_or_transfer_mp(self):
        item = drain_case(steps=[{"kind": "next"}, {"kind": "mp", "actor": normal.key("allies", "ally"), "cost": 96},
                                drain_hit(), normal.hit()])
        observations = self.invoke([item])["cases"][0]["observations"]
        self.assertEqual(observations[2]["value"]["reason"], "insufficient_mp")
        self.assertEqual(observations[1]["session"], observations[2]["session"])
        self.assertTrue(observations[3]["value"]["executed"])
        for changed in ({"kind": "damage", "actor": normal.key("allies", "ally"), "amount": 30},
                        {"kind": "flee", "actor": normal.key("allies", "ally")},
                        {"kind": "damage", "actor": normal.key("enemies", "enemy"), "amount": 1000}):
            observed = self.invoke([drain_case(steps=[{"kind": "next"}, changed, drain_hit()])])["cases"][0]
            self.assertTrue(observed["observations"][-1]["value"]["ok"], observed)
            self.assertFalse(observed["observations"][-1]["value"]["executed"])
            self.assertEqual(observed["observations"][-2]["session"]["teams"], observed["session"]["teams"])

    # {
    #   責務: [test_duplicate_claimed_forged_and_dead_target_keep_resources: 使用済み/取得済み/偽造予約と死亡敵への要求を拒否し、二度目の消費を防ぐか確認します]
    #   処理: [1: 各不正予約と死亡対象の要求前後でSessionが保持されるか確認します]
    #   引数: [self: 単一行動権と対象生存を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_duplicate_claimed_forged_and_dead_target_keep_resources(self):
        cases = [drain_case(steps=[{"kind": "next"}, drain_hit(), drain_hit()]),
                 drain_case(steps=[{"kind": "next"}, {"kind": "claim"}, drain_hit()]),
                 drain_case(steps=[{"kind": "next"}, drain_hit(overrides={"ticket": {"round": 999, "slot": 0,
                                                   "actor": normal.key("allies", "ally")}})])]
        dead = drain_case()
        dead["input"]["enemies"].append(normal.member("extra", speed=1, hp=1000))
        dead["input"]["shuffle_order"].append(normal.key("enemies", "extra"))
        dead["actions"] = [{"kind": "next"}, {"kind": "damage", "actor": normal.key("enemies", "enemy"), "amount": 1000}, drain_hit()]
        cases.append(dead)
        for observed in self.invoke(cases)["cases"]:
            self.assertFalse(observed["observations"][-1]["value"]["ok"], observed)
            self.assertEqual(observed["observations"][-2]["session"], observed["session"])

    # {
    #   責務: [test_restore_mp_caps_and_preserves_hp_flee_and_cursor: 数値MP回復の上限・不正入力・精度・未初期化と生死/逃走/予約の不変を確認します]
    #   処理: [1: 専用Sessionへ数値回復を要求し、MP以外の状態を変更しないか確認します]
    #   引数: [self: 新しい数値資源APIを検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_restore_mp_caps_and_preserves_hp_flee_and_cursor(self):
        target = normal.key("enemies", "enemy")
        steps = [{"kind": "next"}, {"kind": "mp", "actor": target, "cost": 70}]
        steps += [{"kind": "restore_mp", "actor": target, "amount": value} for value in (0, 5, 2**53 - 1, 1)]
        steps += [{"kind": "restore_mp", "actor": target, "amount": value} for value in (-1, 1.5, True, "1", None, 2**53)]
        steps += [{"kind": "restore_mp", "actor": target, "special": value} for value in ("nan", "inf")]
        steps += [{"kind": "restore_mp", "actor": normal.key("enemies", "missing"), "amount": 1},
                  {"kind": "damage", "actor": target, "amount": 1000}, {"kind": "flee", "actor": target},
                  {"kind": "mp", "actor": target, "cost": 10}, {"kind": "restore_mp", "actor": target, "amount": 10}]
        observed, unstarted = self.invoke([drain_case(steps=steps),
            drain_case(start_session=False, steps=[{"kind": "restore_mp", "actor": target, "amount": 1}])])["cases"]
        entries = observed["observations"]
        self.assertEqual([entries[index]["value"]["restored"] for index in (2, 3, 4, 5)], [0, 5, 65, 0])
        for index in range(6, 15):
            self.assertFalse(entries[index]["value"]["ok"])
            self.assertEqual(entries[index - 1]["session"], entries[index]["session"])
        final = observed["session"]["teams"]["enemies"][0]
        self.assertEqual((final["hp"], final["mp"], final["fled"], final["alive"]), (0, 80, True, False))
        self.assertEqual(observed["session"]["pending"], entries[0]["session"]["pending"])
        self.assertEqual(unstarted["observations"][0]["value"]["reason"], "not_initialized")

    # {
    #   責務: [test_eight_actors_same_ids_two_rounds_keep_cumulative_mp: 同速・両陣営同IDの8体が2ラウンドで累積するMPをPythonへ照合します]
    #   処理: [1: 8体の明示吸MP行動を2ラウンド実行し、各個体のHP/MPが初期化されないか確認します]
    #   引数: [self: ラウンド間保持と陣営識別を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_eight_actors_same_ids_two_rounds_keep_cumulative_mp(self):
        item = drain_case()
        source = item["input"]
        source.update(allies=[], enemies=[], learned={"allies": {}, "enemies": {}},
                      equipment={"allies": {}, "enemies": {}}, resistances={"allies": {}, "enemies": {}})
        order = []
        for side in ("allies", "enemies"):
            for index in range(4):
                entry = normal.member(str(index), speed=10, hp=10000)
                entry["stats"].update(mp=100, magic=100)
                entry["mp"] = 100
                source[side].append(entry)
                source["learned"][side][str(index)] = ["possess"]
                source["equipment"][side][str(index)] = {}
                source["resistances"][side][str(index)] = {}
                order.append(normal.key(side, str(index)))
        source["shuffle_order"] = list(reversed(order))
        steps = []
        for _ in range(2):
            for actor in source["shuffle_order"]:
                target = normal.key("enemies" if actor["side"] == "allies" else "allies", actor["id"])
                steps += [{"kind": "next"}, drain_hit(target=target)]
            steps.append({"kind": "begin"})
        item["actions"] = steps[:-1]
        observed = self.invoke([item])["cases"][0]
        states = {side: {entry["identity"]["id"]: copy.deepcopy(entry) for entry in source[side]} for side in ("allies", "enemies")}
        definition = next(entry for entry in source["skills"]["skills"] if entry["id"] == "possess")
        for _ in range(2):
            for actor_key in source["shuffle_order"]:
                side = actor_key["side"]
                opposing = "enemies" if side == "allies" else "allies"
                actor, target = states[side][actor_key["id"]], states[opposing][actor_key["id"]]
                comparison = {"allies": [actor], "enemies": [target], "equipment": {"allies": {"ally": {}}},
                              "resistances": {"enemies": {"enemy": {}}}}
                result = self.python_action(comparison, definition, 1.0)
                actor["mp"], target["mp"], target["hp"] = result["remaining_mp"], result["remaining_target_mp"], result["remaining_hp"]
        for side, entries in observed["session"]["teams"].items():
            for entry in entries:
                self.assertEqual((entry["hp"], entry["mp"]),
                                 (states[side][entry["identity"]["id"]]["hp"], states[side][entry["identity"]["id"]]["mp"]))
        self.assertEqual(observed["session"]["round"], 2)
        self.assertEqual(observed["session"]["phase"], "round_finished")

    # {
    #   責務: [test_application_uses_canonical_ghost_and_preserves_saved_files: 正規習得と許可装備で吸MPを実適用し、専用個体/AI/items/party/data/assetsを保持するか確認します]
    #   処理: [1: 正規個体の再構築とPython実行を照合し、専用保存コピーのbyte不変を確認します]
    #   引数: [self: 保存境界とapplication接続を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_application_uses_canonical_ghost_and_preserves_saved_files(self):
        self.seed_record("owned", level=50)
        self.seed_state(current_party=["owned", None, None, None])
        self.write("items/items.json", {"items": {"herb": 19}, "private": True})
        self.write("parties/private.json", {"members": ["owned"]})
        cases, references = [], []
        loader = BattleDataLoader(self.repository)
        for gear in (None, "wood_staff", "missing"):
            actor = combatant.record("ally", species_id="ghost", level=100, equipment_id=gear)
            target = combatant.record("enemy", species_id="slime", level=100)
            item = drain_case(source={"allies": [actor], "enemies": [target],
                "shuffle_order": [normal.key("allies", "ally"), normal.key("enemies", "enemy")]})
            built_actor, built_target = (loader.build_combatant(MonsterRecord(entry["monster"], entry["ai"])) for entry in (actor, target))
            source = {"allies": [{"identity": actor["monster"], "stats": built_actor.stats, "hp": built_actor.hp,
                                  "mp": built_actor.mp, "fled": False}],
                      "enemies": [{"identity": target["monster"], "stats": built_target.stats, "hp": built_target.hp,
                                   "mp": built_target.mp, "fled": False}],
                      "equipment": {"allies": {"ally": built_actor.equipment or {}}},
                      "resistances": {"enemies": {"enemy": built_target.resistances}}}
            definition = next(entry for entry in built_actor.skills if entry["id"] == "possess")
            references.append(self.python_action(source, definition, 1.0))
            cases.append(item)
        before = self.byte_snapshot()
        for reference, observed in zip(references, self.invoke(joined=cases)["joined"]):
            with self.subTest(reference=reference):
                self.assertTrue(observed["initialized"]["ok"], observed)
                resolved = observed["observations"][-1]["value"]
                self.assertTrue(resolved["executed"], observed)
                for field, value in reference.items():
                    self.assertEqual(resolved["numbers"][field], value)
                self.assertEqual(len(observed["session"]["teams"]["allies"][0]), 6)
        self.assertEqual(self.byte_snapshot(), before)

    # {
    #   責務: [test_guard_exact_mp_limit_and_unused_overflow: 基本防御の物理限定・整数精度上限でのMP移転・無効/吸収で未使用の積を計算しない契約を確認します]
    #   処理: [
    #     1: 基本防御中の敵への吸MPがHP軽減を受けず、防御倍率を解除しないか確認します
    #     2: 最大整数MPでの回復上限と、必要な積の精度超過による非破壊拒否を確認します
    #   ]
    #   引数: [self: 防御と数値精度の境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_guard_exact_mp_limit_and_unused_overflow(self):
        # 残る敵を配置して、非終端ラウンド中のguard保持を観測します。
        guarded = drain_case(basic_defend=True, steps=[{"kind": "next"}, {"kind": "defend"}, {"kind": "next"}, drain_hit()])
        guarded["input"]["enemies"][0]["stats"]["speed"] = 30
        guarded["input"]["enemies"].append(normal.member("extra", speed=1, hp=1000))
        guarded["input"]["shuffle_order"].append(normal.key("enemies", "extra"))
        observed = self.invoke([guarded])["cases"][0]
        self.assertEqual(observed["observations"][-1]["value"]["numbers"]["dealt"], 25)
        self.assertEqual(observed["effects"]["teams"]["enemies"]["enemy"], 0.5)
        maximum = 2**53 - 1
        precise = drain_case()
        for side in ("allies", "enemies"):
            precise["input"][side][0]["stats"]["mp"] = maximum
            precise["input"][side][0]["mp"] = maximum
        observed = self.invoke([precise])["cases"][0]
        self.assertTrue(observed["observations"][-1]["value"]["executed"], observed)
        self.assertEqual(observed["session"]["teams"]["allies"][0]["mp"], maximum)
        self.assertEqual(observed["session"]["teams"]["enemies"][0]["mp"], maximum - 14)
        cases = []
        for resistance in ("normal", "immune", "absorb"):
            item = drain_case()
            next(entry for entry in item["input"]["skills"]["skills"] if entry["id"] == "possess")["mp_power"] = maximum
            item["input"]["resistances"]["enemies"]["enemy"]["mental"] = resistance
            cases.append(item)
        observed = self.invoke(cases)["cases"]
        self.assertEqual(observed[0]["observations"][-1]["value"]["reason"], "invalid_drain_mp_numbers")
        self.assertEqual(observed[0]["observations"][0]["session"], observed[0]["session"])
        for item in observed[1:]:
            self.assertTrue(item["observations"][-1]["value"]["executed"], item)
            self.assertEqual(item["session"]["teams"]["allies"][0]["mp"], 95)
            self.assertEqual(item["session"]["teams"]["enemies"][0]["mp"], 80)


if __name__ == "__main__":
    unittest.main()
