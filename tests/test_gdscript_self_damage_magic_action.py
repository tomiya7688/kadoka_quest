"""自傷魔法の実MP/HP適用を実GodotとPythonの戦闘処理で照合し、専用保存コピーの不変を検証します。"""
# {
#   責務: [test_gdscript_self_damage_magic_action: 自傷魔法の一度だけの資源更新・厳密な拒否・保存境界を検証します]
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
#   責務: [self_hit: 敵へのメタルバーストを専用入口へ要求する試験操作を作ります]
#   処理: [1: 操作種別・敵target・skill_idとケース別の設定を辞書へまとめます]
#   引数: [changes: 敵対象・揺らぎ・不正要求などの試験操作の上書き（dict）]
#   戻り値: [result: 自傷魔法の専用プローブ操作（dict）]
# }
def self_hit(**changes):
    return {"kind": "self_magic", "target": normal.key("enemies", "enemy"), "skill_id": "metal_burst", **changes}

# {
#   責務: [self_case: 自傷魔法と通常魔法を同じ専用Sessionで比較する独立ケースを作ります]
#   処理: [
#     1: 指定がなければ自傷魔法を使える初期HP/MPを用意します
#     2: 共用の魔法fixtureに自傷魔法専用入口の初期化を追加します
#   ]
#   引数: [
#     source: 両陣営・習得・許可装備・耐性の開始情報。Noneなら専用初期値（dictまたはNone）
#     steps: 明示操作列。Noneなら次行動取得と自傷魔法1回（listまたはNone）
#     changes: プローブの初期化・コピー編集などの試験設定（dict）
#   ]
#   戻り値: [result: 開始情報の独立コピーを持つ試験ケース（dict）]
# }
def self_case(*, source=None, steps=None, **changes):
    if source is None:
        source = normal.parameters(hp=1000)
        actor = source["allies"][0]
        actor["stats"].update(hp=123, mp=100, magic=80)
        actor.update(hp=123, mp=100)
    return magic.magic_case(source=source, steps=[{"kind": "next"}, self_hit()] if steps is None else steps,
                            self_damage_magic=True, **changes)

# {
#   責務: [SelfDamageMagicActionTests: 専用data/assetsと保存コピーを所有し、自傷魔法の実適用を正本へ照合します]
#   フィールド: [
#     content: 正規data/assetsを複製した一時コンテンツ領域（Path）
#     repository: 専用コンテンツを読むPythonリポジトリ
#     profile: 個体・AI・items・partyを検証する一時保存先（Path）
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real self-damage magic actions")
class SelfDamageMagicActionTests(unittest.TestCase):
    setUp = normal.GDScriptNormalActionTests.setUp
    invoke = normal.GDScriptNormalActionTests.invoke
    byte_snapshot = normal.GDScriptNormalActionTests.byte_snapshot
    seed_state = normal.GDScriptNormalActionTests.seed_state
    seed_record = normal.GDScriptNormalActionTests.seed_record
    write = normal.GDScriptNormalActionTests.write

    # {
    #   責務: [_python_action: 自傷魔法の選択と揺らぎだけを固定し、実_take_actionの敵HP・術者HP・MPを取得します]
    #   処理: [
    #     1: 専用資源・装備・耐性からPythonの独立戦闘を作ります
    #     2: 学習せず実行し、保存個体レコードの不変も確認します
    #   ]
    #   引数: [
    #     self: 専用比較fixtureを所有するテストケース
    #     source: 比較時点の両陣営資源・装備・耐性（dict）
    #     definition: 選択した自傷魔法定義（dict）
    #     variance: 正本へ明示する揺らぎ（float）
    #   ]
    #   戻り値: [result: remaining_hp・remaining_actor_hp・remaining_mpの実適用値（dict）]
    # }
    def _python_action(self, source, definition, variance):
        # 攻撃計算や資源更新はmock化せず、AI選択と揺らぎだけを固定する。
        engine = turn.GDScriptTurnTests.engine(self, source["allies"], source["enemies"])
        actor, target = engine.allies[0], engine.enemies[0]
        actor.skills, actor.equipment = [definition], source["equipment"]["allies"]["ally"]
        target.resistances = source["resistances"]["enemies"]["enemy"]
        target.guard = 0.5
        records = copy.deepcopy([actor.record, target.record])
        engine.inference.choose = mock.Mock(return_value=definition)
        engine.learning.learn, engine.rng = mock.Mock(), mock.Mock()
        engine.rng.uniform.return_value = variance
        engine._take_action(actor, [target], [actor])
        engine.learning.learn.assert_not_called()
        engine.rng.random.assert_not_called()
        self.assertEqual(records, [actor.record, target.record])
        return {"remaining_hp": target.hp, "remaining_actor_hp": actor.hp, "remaining_mp": actor.mp}

    # {
    #   責務: [test_resistance_hp_variance_bonus_and_mod_cost_match_python: 耐性・低HP・揺らぎ・装備加算・MOD自傷率の実適用をPythonへ照合します]
    #   処理: [
    #     1: 最新資源を持つ各組合せの専用ケースと正本結果を用意します
    #     2: 実Godotの予測値と適用後資源・コピー不変を検証します
    #   ]
    #   引数: [self: 専用比較fixtureを所有するテストケース]
    #   戻り値: [result: なし（None）。不一致はassertionで報告します]
    # }
    def test_resistance_hp_variance_bonus_and_mod_cost_match_python(self):
        cases, expected = [], []
        for resistance, hp, variance, bonus, ratio in itertools.product(
                ("weak", "normal", "strong", "immune", "absorb", "unknown", None),
                (1, 5, 123), (0.92, 1.08), (0, 11), (0.1, 0, "0", -0.1, 2)):
            item = self_case()
            source = item["input"]
            source["equipment"]["allies"]["ally"] = {
                "allowed_species_ids": ["slime"], "fixed_bonus_damage": bonus,
                "skill_modifiers": {"metal_burst": {"power_multiplier": 99}}}
            if resistance is not None:
                source["resistances"]["enemies"]["enemy"]["metal"] = resistance
            definition = next(x for x in source["skills"]["skills"] if x["id"] == "metal_burst")
            definition["self_damage_ratio"] = ratio
            # Sessionは満タンで開始し、低HPは予約取得後の実ダメージで作る。
            item["actions"] = [{"kind": "next"},
                {"kind": "damage", "actor": normal.key("allies", "ally"), "amount": 123 - hp},
                {"kind": "damage", "actor": normal.key("enemies", "enemy"), "amount": 850},
                self_hit(overrides={"variance": variance}, mutate_result=True)]
            comparison = copy.deepcopy(source)
            comparison["allies"][0]["hp"], comparison["enemies"][0]["hp"] = hp, 150
            expected.append(self._python_action(comparison, definition, variance))
            cases.append(item)
        for reference, observed in zip(expected, self.invoke(cases)["cases"]):
            with self.subTest(reference=reference):
                resolved = observed["observations"][-1]["value"]
                self.assertTrue(resolved.get("executed"), observed)
                self.assertEqual(resolved["scope"], "explicit_self_damage_magic_only")
                self.assertEqual(resolved["spent_mp"], 18)
                for field, value in reference.items():
                    self.assertEqual(resolved["numbers"][field], value)
                actor, target = observed["session"]["teams"]["allies"][0], observed["session"]["teams"]["enemies"][0]
                self.assertEqual((target["hp"], actor["hp"], actor["mp"]),
                                 tuple(reference[x] for x in ("remaining_hp", "remaining_actor_hp", "remaining_mp")))
                self.assertGreaterEqual(actor["hp"], 1)
                self.assertTrue(observed["input_preserved"])

    # {
    #   責務: [test_latest_resources_enemy_defeat_and_duplicate_do_not_skip_or_repeat_cost: 予約後のHP/MP変更と最後の敵の撃破に対応し、代償の二重支払いを拒否します]
    #   処理: [1: 資源変更・自傷魔法・重複要求を実行し、HP下限と一度だけの支払いを確認します]
    #   引数: [self: 専用比較fixtureを所有するテストケース]
    #   戻り値: [result: なし（None）。不一致はassertionで報告します]
    # }
    def test_latest_resources_enemy_defeat_and_duplicate_do_not_skip_or_repeat_cost(self):
        item = self_case(steps=[{"kind": "next"},
            {"kind": "damage", "actor": normal.key("allies", "ally"), "amount": 120},
            {"kind": "mp", "actor": normal.key("allies", "ally"), "cost": 82},
            {"kind": "damage", "actor": normal.key("enemies", "enemy"), "amount": 999},
            self_hit(), self_hit()])
        observed = self.invoke([item])["cases"][0]
        resolved = observed["observations"][-2]["value"]
        self.assertTrue(resolved["executed"], observed)
        self.assertEqual((resolved["numbers"]["self_damage"], resolved["numbers"]["self_dealt"]), (12, 2))
        self.assertEqual((observed["session"]["teams"]["allies"][0]["hp"],
                          observed["session"]["teams"]["allies"][0]["mp"]), (1, 0))
        self.assertEqual(observed["session"]["teams"]["enemies"][0]["hp"], 0)
        self.assertFalse(observed["observations"][-1]["value"]["ok"])
        self.assertEqual(observed["observations"][-2]["session"], observed["session"])

    # {
    #   責務: [test_invalid_requests_definitions_and_equipment_keep_offer_and_resources: 厳密でない要求・未対応効果・不正数値・装備を拒否し、予約と資源を保持します]
    #   処理: [1: 不正入力を1箇所ずつ追加し、claim前の状態と拒否後の状態を比較します]
    #   引数: [self: 専用比較fixtureを所有するテストケース]
    #   戻り値: [result: なし（None）。不一致はassertionで報告します]
    # }
    def test_invalid_requests_definitions_and_equipment_keep_offer_and_resources(self):
        cases = []
        for field, value in (("actor_hp", 999), ("actor_max_hp", 999), ("self_damage_ratio", 0),
                             ("self_damage", False), ("critical_roll", 0.5), ("guard", 1),
                             ("current_mp", 999), ("target_resistances", {}), ("variance", False),
                             ("variance", 0.91), ("variance", 1.09), ("skill_id", "weaken"),
                             ("skill_id", "unknown"), ("target", normal.key("allies", "ally")),
                             ("target", normal.key("enemies", "missing")), ("target", None),
                             ("ticket", {"actor": normal.key("allies", "ally")})):
            cases.append(self_case(steps=[{"kind": "next"}, self_hit(overrides={field: value})]))
        cases.extend(self_case(steps=[{"kind": "next"}, self_hit(request=x)]) for x in (None, [], {}))
        for ratio in (None, True, False, "", "no", "NaN", "Infinity", [], {}, 2**53):
            item = self_case()
            next(x for x in item["input"]["skills"]["skills"] if x["id"] == "metal_burst")["self_damage_ratio"] = ratio
            cases.append(item)
        for extra in ({"status_effect": {}}, {"target_all": False}, {"mp_power": 0}, {"counter_ready": False}):
            item = self_case()
            next(x for x in item["input"]["skills"]["skills"] if x["id"] == "metal_burst").update(extra)
            cases.append(item)
        for field in ("power", "self_damage_ratio"):
            cases.extend(self_case(special_skill_id="metal_burst", definition_special={field: x}) for x in ("nan", "inf"))
        cases.extend(self_case(steps=[{"kind": "next"}, self_hit(special={"variance": x})]) for x in ("nan", "inf"))
        for modifier in ({"status": {}}, {"power_multiplier": False}, [], {"self_damage_ratio": 0}):
            item = self_case()
            item["input"]["equipment"]["allies"]["ally"] = {
                "allowed_species_ids": ["slime"], "skill_modifiers": {"metal_burst": modifier}}
            cases.append(item)
        # 一意性と演算精度も実行前に拒否し、未対応データを成功扱いしない。
        duplicate = self_case()
        duplicate["input"]["skills"]["skills"].append(copy.deepcopy(next(
            x for x in duplicate["input"]["skills"]["skills"] if x["id"] == "metal_burst")))
        cases.append(duplicate)
        overflow = self_case()
        overflow["input"]["allies"][0]["stats"]["hp"] = 2**52
        overflow["input"]["allies"][0]["hp"] = 2**52
        next(x for x in overflow["input"]["skills"]["skills"] if x["id"] == "metal_burst")["self_damage_ratio"] = 2
        cases.append(overflow)
        unlearned = self_case()
        unlearned["input"]["learned"]["allies"]["ally"] = ["weaken"]
        cases.append(unlearned)
        for observed in self.invoke(cases)["cases"]:
            with self.subTest(result=observed["observations"][-1]["value"]):
                self.assertTrue(observed["initialized"]["ok"], observed)
                self.assertFalse(observed["observations"][-1]["value"]["ok"], observed)
                self.assertEqual(observed["observations"][0]["session"], observed["session"])

    # {
    #   責務: [test_mp_shortage_and_entry_separation_allow_retry: MP不足や入口違いで資源を消費せず、同じ予約から通常魔法へ変更できます]
    #   処理: [1: 不足と未対応入口を順に要求し、最後の通常魔法だけが支払うことを確認します]
    #   引数: [self: 専用比較fixtureを所有するテストケース]
    #   戻り値: [result: なし（None）。不一致はassertionで報告します]
    # }
    def test_mp_shortage_and_entry_separation_allow_retry(self):
        item = self_case(steps=[{"kind": "next"},
            magic.magic_hit(skill_id="metal_burst"), self_hit(skill_id="weaken"),
            {"kind": "mp", "actor": normal.key("allies", "ally"), "cost": 83}, self_hit(),
            magic.magic_hit()])
        observed = self.invoke([item])["cases"][0]
        operations = observed["observations"]
        for index in (1, 2, 4):
            self.assertFalse(operations[index]["value"]["ok"])
            self.assertEqual(operations[index - 1]["session"], operations[index]["session"])
        self.assertEqual(operations[4]["value"]["reason"], "insufficient_mp")
        self.assertTrue(operations[5]["value"]["executed"], observed)
        self.assertEqual((observed["session"]["teams"]["allies"][0]["hp"],
                          observed["session"]["teams"]["allies"][0]["mp"]), (123, 12))

    # {
    #   責務: [test_cancellation_dead_target_and_claimed_ticket_never_pay_cost: 死亡・逃走・敵なしの取消と死亡対象・取得済み予約の拒否で追加消費しないことを確認します]
    #   処理: [1: 予約取得後に各停止条件を作り、操作直前と直後のHP/MPを照合します]
    #   引数: [self: 専用比較fixtureを所有するテストケース]
    #   戻り値: [result: なし（None）。不一致はassertionで報告します]
    # }
    def test_cancellation_dead_target_and_claimed_ticket_never_pay_cost(self):
        cases = []
        for operation in ({"kind": "damage", "actor": normal.key("allies", "ally"), "amount": 123},
                          {"kind": "flee", "actor": normal.key("allies", "ally")},
                          {"kind": "damage", "actor": normal.key("enemies", "enemy"), "amount": 1000},
                          {"kind": "claim"}):
            cases.append(self_case(steps=[{"kind": "next"}, operation, self_hit()]))
        dead_target = self_case()
        dead_target["input"]["enemies"].append(normal.member("extra", speed=1, hp=1000))
        dead_target["input"]["shuffle_order"].append(normal.key("enemies", "extra"))
        dead_target["actions"] = [{"kind": "next"},
            {"kind": "damage", "actor": normal.key("enemies", "enemy"), "amount": 1000}, self_hit()]
        cases.append(dead_target)
        for index, observed in enumerate(self.invoke(cases)["cases"]):
            value = observed["observations"][-1]["value"]
            if index < 3:
                self.assertTrue(value["ok"], observed)
                self.assertFalse(value["executed"], observed)
            else:
                self.assertFalse(value["ok"], observed)
            self.assertEqual(observed["observations"][-2]["session"]["teams"], observed["session"]["teams"])

    # {
    #   責務: [test_context_and_result_copies_are_independent_and_initialization_is_once: 開始情報・返却値のコピー編集と再初期化が行動資源や定義を変更しないことを確認します]
    #   処理: [1: コピーを編集して実行し、MP・HPと再設定拒否時の状態を検証します]
    #   引数: [self: 専用比較fixtureを所有するテストケース]
    #   戻り値: [result: なし（None）。不一致はassertionで報告します]
    # }
    def test_context_and_result_copies_are_independent_and_initialization_is_once(self):
        item = self_case(mutate_initial=True, steps=[{"kind": "input_mutation"}, {"kind": "next"},
            self_hit(mutate_result=True), {"kind": "configure_self_magic"}])
        observed = self.invoke([item])["cases"][0]
        self.assertTrue(observed["observations"][-2]["value"]["executed"], observed)
        self.assertEqual(observed["observations"][-1]["value"]["reason"], "already_initialized")
        self.assertEqual(observed["observations"][-2]["session"], observed["session"])
        self.assertEqual((observed["session"]["teams"]["allies"][0]["hp"],
                          observed["session"]["teams"]["allies"][0]["mp"]), (111, 82))
        invalid = self_case(steps=[])
        invalid["input"]["resistances"]["enemies"]["enemy"] = {"metal": False}
        mismatch = self_case(steps=[])
        source = mismatch["input"]
        context = {side: [{"snapshot": copy.deepcopy(x), "skill_ids": ["metal_burst"],
                          "equipment": {}, "resistances": {}} for x in source[side]] for side in ("allies", "enemies")}
        context["allies"][0]["snapshot"]["stats"]["magic"] += 1
        mismatch["magic_context"] = context
        for result in self.invoke([invalid, mismatch])["cases"]:
            self.assertFalse(result["initialized"]["ok"], result)
            self.assertEqual(result["session"]["round"], 0)

    # {
    #   責務: [test_eight_same_id_actors_keep_hp_floor_and_mp_across_rounds: 両陣営同IDの8体で、HP1の生存とラウンド間の累積MP消費を確認します]
    #   処理: [1: 全対象を無効にした2ラウンド16回の自傷魔法を実行し、各個体の最終資源を検証します]
    #   引数: [self: 専用比較fixtureを所有するテストケース]
    #   戻り値: [result: なし（None）。不一致はassertionで報告します]
    # }
    def test_eight_same_id_actors_keep_hp_floor_and_mp_across_rounds(self):
        source = self_case()["input"]
        source.update(allies=[], enemies=[], learned={"allies": {}, "enemies": {}},
                      resistances={"allies": {}, "enemies": {}}, equipment={}, shuffle_order=[])
        steps = []
        for side in ("allies", "enemies"):
            for index in range(4):
                identifier = str(index)
                member = normal.member(identifier, hp=1000)
                member["stats"]["mp"], member["mp"] = 100, 100
                source[side].append(member)
                source["learned"][side][identifier] = ["metal_burst"]
                source["resistances"][side][identifier] = {"metal": "immune"}
                source["shuffle_order"].append(normal.key(side, identifier))
                target = normal.key("enemies" if side == "allies" else "allies", identifier)
                steps.extend([{"kind": "next"}, self_hit(target=target)])
        next(x for x in source["skills"]["skills"] if x["id"] == "metal_burst")["self_damage_ratio"] = 1
        observed = self.invoke([self_case(source=source, steps=steps + [{"kind": "begin"}] + steps)])["cases"][0]
        for members in observed["session"]["teams"].values():
            self.assertTrue(all(x["hp"] == 1 and x["mp"] == 64 and x["alive"] for x in members), observed)
        self.assertTrue(all(x["value"].get("executed") for x in observed["observations"] if "spent_mp" in x["value"]))

    # {
    #   責務: [test_application_uses_canonical_individuals_without_changing_save_files: 正規のメタルスライムから専用入口を実行し、個体・AI・items・party・dataのbyte不変を確認します]
    #   処理: [
    #     1: 許可装備付きの正規個体をPythonとapplicationで再構築します
    #     2: 実行資源を照合し、専用保存コピーへの書き込みがないことを確認します
    #   ]
    #   引数: [self: 専用比較fixtureを所有するテストケース]
    #   戻り値: [result: なし（None）。不一致はassertionで報告します]
    # }
    def test_application_uses_canonical_individuals_without_changing_save_files(self):
        self.seed_record("owned", level=50)
        self.seed_state(current_party=["owned", None, None, None])
        self.write("items/items.json", {"items": {"herb": 19}, "private": True})
        self.write("parties/private.json", {"members": ["owned"]})
        loader = BattleDataLoader(self.repository)
        cases, expected = [], []
        for gear in (None, "metal_claw", "wood_staff", "missing"):
            actor = combatant.record("ally", species_id="metal_slime", level=100, equipment_id=gear)
            target = combatant.record("enemy", species_id="slime", level=100)
            source = {"allies": [actor], "enemies": [target],
                      "shuffle_order": [normal.key("allies", "ally"), normal.key("enemies", "enemy")]}
            item = self_case(source=source)
            built_actor = loader.build_combatant(MonsterRecord(actor["monster"], actor["ai"]))
            built_target = loader.build_combatant(MonsterRecord(target["monster"], target["ai"]))
            # 正規速度で術者が先に行動することを確認し、行動順をfixture側で偽装しない。
            self.assertGreaterEqual(built_actor.stats["speed"], built_target.stats["speed"])
            cases.append(item)
            expected.append(built_actor)
        before = self.byte_snapshot()
        for actor, observed in zip(expected, self.invoke(joined=cases)["joined"]):
            self.assertTrue(observed["initialized"]["ok"], observed)
            result = observed["observations"][-1]["value"]
            self.assertTrue(result.get("executed"), observed)
            self.assertEqual(result["spent_mp"], 18)
            resource = observed["session"]["teams"]["allies"][0]
            self.assertEqual(resource["mp"], actor.stats["mp"] - 18)
            self.assertEqual(resource["hp"], max(1, actor.stats["hp"] - max(1, int(actor.stats["hp"] * 0.1))))
        self.assertEqual(before, self.byte_snapshot())

    # {
    #   責務: [test_shared_performance_probe_applies_self_cost: 共用の性能プローブが次行動・敵効果・術者代償・MPを実適用することを確認します]
    #   処理: [1: 少数反復の専用CLIを起動し、正常な性能と資源検証の成功を確認します]
    #   引数: [self: 専用比較fixtureを所有するテストケース]
    #   戻り値: [result: なし（None）。不一致はassertionで報告します]
    # }
    def test_shared_performance_probe_applies_self_cost(self):
        import subprocess
        import sys
        # CLIは一時要求だけを使う。利用者dataや保存フォルダを計測に使わない。
        process = subprocess.run([sys.executable, str(fixture.ROOT / "tools/performance-check/script/check_gdscript_magic_action.py"),
                                  "--self-damage", "--iterations", "80", "--samples", "3", "--warmup", "8"],
                                 capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        self.assertIn("OK Godot next+self-magic", process.stdout)

# {
#   責務: [SelfDamageMagicActionBoundaryTests: 自傷魔法の計算・更新・委譲の責務と、画面・開発ツールからの分離を静的検証します]
#   フィールド: []
# }
class SelfDamageMagicActionBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_application_only_delegates_and_field_is_unconnected: applicationにHP更新を重複させず、フィールドや画面から未接続であることを確認します]
    #   処理: [1: 専用委譲と共用行動処理を照合し、禁止依存を検査します]
    #   引数: [self: ソース責務境界を検証するテストケース]
    #   戻り値: [result: なし（None）。不一致はassertionで報告します]
    # }
    def test_application_only_delegates_and_field_is_unconnected(self):
        application = (fixture.ROOT / "gdscript/application/battle_session_application.gd").read_text(encoding="utf-8")
        self.assertIn("_self_magic.resolve(request)", application)
        for forbidden in (".take_damage(", ".pay_mp(", ".heal(", "quote_damage(", "self_dealt"):
            self.assertNotIn(forbidden, application)
        for name in ("magic_skill_action", "magic_skill_context", "self_damage_magic_contract"):
            source = (fixture.ROOT / f"gdscript/engine/{name}.gd").read_text(encoding="utf-8")
            for forbidden in ("FileAccess", "DirAccess", "OS.", "randf(", "RandomNumberGenerator", ".learn(", "res://ui/"):
                self.assertNotIn(forbidden, source)
        self.assertNotIn("resolve_self_damage_magic_skill",
                         (fixture.ROOT / "gdscript/application/field_application.gd").read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
