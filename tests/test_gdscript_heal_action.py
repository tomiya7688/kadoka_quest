"""単体HP回復の実MP消費・最新HP適用を実GodotとPython正本で比較します。"""
# {
#   責務: [test_gdscript_heal_action: 明示回復の数値互換・予約保持・生存制約・独立コピーと保存境界を検証します]
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
import test_gdscript_turn_order as turn
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.battle_data import BattleDataLoader


# {
#   責務: [heal_step: 同陣営の指定個体へ回復スキルを要求する専用操作を作ります]
#   処理: [1: 回復専用種別と対象・スキルID・ケース別設定をまとめます]
#   引数: [changes: 対象・ID・不正要求等のケース別設定（dict）]
#   戻り値: [result: 単体HP回復プローブの明示操作（dict）]
# }
def heal_step(**changes):
    return {"kind": "heal_skill", "target": normal.key("allies", "friend"), "skill_id": "small_heal", **changes}


# {
#   責務: [heal_case: 満HP/MPの独立資源と正規回復定義で専用ケースを作ります]
#   処理: [1: 開始情報を複製し、スキル一覧・習得と明示操作列を用意します]
#   引数: [
#     source: 両陣営・装備・習得の開始情報。Noneなら術者と味方1体と敵1体（dictまたはNone）
#     steps: 明示操作列。Noneなら次行動取得と味方への回復1回（listまたはNone）
#     changes: 開始検証・入出力コピー編集などのプローブ設定（dict）
#   ]
#   戻り値: [result: 独立した入力と明示操作列を持つ回復専用ケース（dict）]
# }
def heal_case(*, source=None, steps=None, **changes):
    # 現在資源の減少は開始後に行い、満タン開始の既存制約を変えません。
    if source is None:
        source = normal.parameters()
        source["allies"][0].update(hp=200, mp=100)
        source["allies"][0]["stats"].update(hp=200, mp=100)
        source["allies"].append(normal.member("friend", speed=5, hp=1000))
        source["shuffle_order"].append(normal.key("allies", "friend"))
    source = copy.deepcopy(source)
    source.setdefault("skills", json.loads((fixture.ROOT / "data/skills/skills.json").read_text(encoding="utf-8")))
    if "monster" not in source["allies"][0]:
        source.setdefault("learned", {side: {member["identity"]["id"]: ["small_heal", "healy", "spirit_recover"]
                                          for member in source[side]} for side in ("allies", "enemies")})
    source.setdefault("equipment", {})
    return normal.case(source, [{"kind": "next"}, heal_step()] if steps is None else steps, heal_skill=True, **changes)


# {
#   責務: [HealActionTests: 専用コンテンツと保存先を所有し、回復行動の数値・更新・非破壊境界を実Godotで検証します]
#   フィールド: [
#     content: 正規data/assetsを複製した一時コンテンツ領域（Path）
#     repository: 専用コピーを読むPythonリポジトリ
#     profile: 個体・AI・items・partyの一時保存先（Path）
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real heal actions")
class HealActionTests(unittest.TestCase):
    setUp = normal.GDScriptNormalActionTests.setUp
    invoke = normal.GDScriptNormalActionTests.invoke
    byte_snapshot = normal.GDScriptNormalActionTests.byte_snapshot
    seed_state = normal.GDScriptNormalActionTests.seed_state
    seed_record = normal.GDScriptNormalActionTests.seed_record
    write = normal.GDScriptNormalActionTests.write

    # {
    #   責務: [python_action: 対象候補を1体に限定し、実Pythonの回復とMP支払いを比較用に実行します]
    #   処理: [1: 最新資源の独立個体で選択だけを固定し、保存レコードと学習の不変を確認します]
    #   引数: [
    #     self: 専用Python比較先の所有者
    #     source: 比較時点の両陣営資源・装備（dict）
    #     definition: 比較する回復定義（dict）
    #   ]
    #   戻り値: [result: 実回復量・残HP・術者の残MP（dict）]
    # }
    def python_action(self, source, definition):
        engine = turn.GDScriptTurnTests.engine(self, source["allies"], source["enemies"])
        actor, target = engine.allies
        actor.skills, actor.equipment = [definition], source["equipment"].get("allies", {}).get("ally", {})
        target.guard, target.resistances = 0.01, {"fire": "immune", "mental": "absorb"}
        previous_hp, records = target.hp, copy.deepcopy([actor.record, target.record])
        engine.inference.choose = mock.Mock(return_value=definition)
        engine.learning.learn, engine.rng = mock.Mock(), mock.Mock()
        # 数値と実支払いはmock化せず、AIの自動対象選択を移植したとも扱いません。
        engine._take_action(actor, engine.enemies, [target])
        engine.learning.learn.assert_not_called()
        engine.rng.random.assert_not_called()
        engine.rng.uniform.assert_not_called()
        self.assertEqual(records, [actor.record, target.record])
        return {"remaining_hp": target.hp, "remaining_mp": actor.mp, "healed": target.hp - previous_hp}

    # {
    #   責務: [test_canonical_and_finite_mods_match_python_latest_resources: 正規2スキルと有限MODを最新HP/MP・装備の組合せでPythonへ照合します]
    #   処理: [1: 開始後に資源を減らし、実回復・消費MP・返却コピーを比較します]
    #   引数: [self: 数値互換の組合せを検証するテストケース]
    #   戻り値: [result: なし（None）。不一致はassertionで報告します]
    # }
    def test_canonical_and_finite_mods_match_python_latest_resources(self):
        cases, expected = [], []
        for skill_id, hp, mp, bonus in itertools.product(("small_heal", "healy"), (1, 999, 1000), (6, 99), (0, 11)):
            item = heal_case()
            item["input"]["equipment"] = {"allies": {"ally": {"allowed_species_ids": ["slime"],
                "fixed_bonus_damage": bonus, "skill_modifiers": {skill_id: {"power_multiplier": 99}}}}}
            definition = next(entry for entry in item["input"]["skills"]["skills"] if entry["id"] == skill_id)
            item["actions"] = [{"kind": "next"}, {"kind": "mp", "actor": normal.key("allies", "ally"), "cost": 100 - mp},
                {"kind": "damage", "actor": normal.key("allies", "friend"), "amount": 1000 - hp},
                heal_step(skill_id=skill_id, mutate_result=True)]
            latest = copy.deepcopy(item["input"])
            latest["allies"][0]["mp"], latest["allies"][1]["hp"] = mp, hp
            expected.append(self.python_action(latest, definition))
            cases.append(item)
        for ratio, cost in itertools.product((None, -1, 0, "0.22", 2), ("3", 3.9)):
            item = heal_case()
            definition = next(entry for entry in item["input"]["skills"]["skills"] if entry["id"] == "small_heal")
            definition["mp_cost"] = cost
            if ratio is None:
                definition.pop("heal_ratio")
            else:
                definition["heal_ratio"] = ratio
            item["actions"] = [{"kind": "next"}, {"kind": "damage", "actor": normal.key("allies", "friend"), "amount": 999}, heal_step()]
            latest = copy.deepcopy(item["input"])
            latest["allies"][1]["hp"] = 1
            expected.append(self.python_action(latest, definition))
            cases.append(item)
        for reference, observed in zip(expected, self.invoke(cases)["cases"]):
            with self.subTest(reference=reference):
                result = observed["observations"][-1]["value"]
                self.assertTrue(result["executed"], observed)
                self.assertEqual(result["scope"], "explicit_heal_skill_only")
                for field, value in reference.items():
                    self.assertEqual(result["numbers"][field], value)
                self.assertEqual(result["healed"], reference["healed"])
                self.assertEqual(observed["session"]["teams"]["allies"][0]["mp"], reference["remaining_mp"])
                self.assertEqual(observed["session"]["teams"]["allies"][1]["hp"], reference["remaining_hp"])
                self.assertEqual(result["spent_mp"], result["numbers"]["mp_cost"])
                self.assertTrue(observed["input_preserved"])
                self.assertIsNone(observed["session"]["pending"])

    # {
    #   責務: [test_refusal_keeps_offered_ticket_and_resources_for_retry: 不正要求・不足MP・未対応定義と装備では予約とHP/MPを保持します]
    #   処理: [1: 拒否の前後を比較し、同じ予約で通常攻撃を実行できることを確認します]
    #   引数: [self: 拒否の非破壊性を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_refusal_keeps_offered_ticket_and_resources_for_retry(self):
        invalid = [heal_step(request=value) for value in (None, [], {}, False)]
        invalid += [heal_step(overrides={field: value}) for field, value in itertools.product(
            ("variance", "heal_ratio", "current_mp", "target_hp", "target_max_hp", "guard", "critical_roll"), (0, False, ""))]
        invalid += [heal_step(overrides={"ticket": value}) for value in (None, {}, {"round": 1, "slot": 1, "actor": normal.key("allies", "ally")})]
        invalid += [heal_step(target=value) for value in (None, {}, normal.key("enemies", "enemy"), normal.key("allies", "missing"))]
        invalid += [heal_step(skill_id=value) for value in (None, "", "attack", "defend", "unknown", "spirit_recover")]
        cases = [heal_case(steps=[{"kind": "next"}, action, normal.hit()]) for action in invalid]
        shortage = heal_case(steps=[{"kind": "next"}, {"kind": "mp", "actor": normal.key("allies", "ally"), "cost": 95},
                                   heal_step(), normal.hit()])
        cases.append(shortage)
        for field, value in itertools.product(("status_cure_chance", "self_damage_ratio", "target", "element", "extra"), (0, False, "")):
            item = heal_case(steps=[{"kind": "next"}, heal_step(), normal.hit()])
            next(entry for entry in item["input"]["skills"]["skills"] if entry["id"] == "small_heal")[field] = value
            cases.append(item)
        for modifier in ({"heal_ratio_multiplier": 0}, {"extra": False}, None, {"power_multiplier": True}):
            item = heal_case(steps=[{"kind": "next"}, heal_step(), normal.hit()])
            item["input"]["equipment"] = {"allies": {"ally": {"allowed_species_ids": ["slime"], "skill_modifiers": {"small_heal": modifier}}}}
            cases.append(item)
        for item in self.invoke(cases)["cases"]:
            with self.subTest(result=item):
                rejected, prior = item["observations"][-2], item["observations"][-3]
                self.assertFalse(rejected["value"]["ok"], item)
                self.assertEqual(rejected["session"], prior["session"])
                self.assertEqual(rejected["effects"], prior["effects"])
                self.assertTrue(item["observations"][-1]["value"]["executed"])
                self.assertTrue(item["input_preserved"])

    # {
    #   責務: [test_dead_fled_targets_and_changed_actor_are_not_revived: 死亡/逃走対象を拒否し、予約後の行動者死亡/逃走/敵なしでは無消費で取り消します]
    #   処理: [1: 予約後に生存状態を変え、HP/MP保持と予約の保持または取消を確認します]
    #   引数: [self: 生存制約の変更を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_dead_fled_targets_and_changed_actor_are_not_revived(self):
        cases = []
        for actor, kind, amount in (("friend", "damage", 1000), ("friend", "flee", 0),
                                    ("ally", "damage", 200), ("ally", "flee", 0), ("enemy", "damage", 1000)):
            side = "enemies" if actor == "enemy" else "allies"
            cases.append(heal_case(steps=[{"kind": "next"}, {"kind": kind, "actor": normal.key(side, actor), "amount": amount}, heal_step()]))
        for index, item in enumerate(self.invoke(cases)["cases"]):
            before, after = item["observations"][-2]["session"], item["session"]
            with self.subTest(index=index):
                self.assertEqual(before["teams"], after["teams"])
                result = item["observations"][-1]["value"]
                if index < 2:
                    self.assertEqual(result["reason"], "target_not_alive")
                    self.assertEqual(before, after)
                else:
                    self.assertTrue(result["ok"])
                    self.assertFalse(result["executed"])
                    self.assertIsNone(after["pending"])

    # {
    #   責務: [test_eight_actors_self_heal_multiple_rounds_and_repeated_ticket: 同IDを持つ両陣営8体の本人回復と複数ラウンド・予約再使用の拒否を検証します]
    #   処理: [1: 8体を独立に回復し、再使用・既取得票で追加消費しないか確認します]
    #   引数: [self: 予約と個体識別の境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_eight_actors_self_heal_multiple_rounds_and_repeated_ticket(self):
        source = turn.request([normal.member(str(i), speed=1, hp=1000) for i in range(4)],
                              [normal.member(str(i), speed=1, hp=1000) for i in range(4)])
        for side in ("allies", "enemies"):
            for member in source[side]:
                member["mp"], member["stats"]["mp"] = 100, 100
        keys = source["shuffle_order"]
        steps = [{"kind": "damage", "actor": key, "amount": 900} for key in keys]
        for round_index in range(2):
            if round_index:
                steps.append({"kind": "begin"})
            for key in keys:
                steps.extend([{"kind": "next"}, heal_step(target=key)])
        item = self.invoke([heal_case(source=source, steps=steps)])["cases"][0]
        for side in ("allies", "enemies"):
            for member in item["session"]["teams"][side]:
                self.assertEqual((member["hp"], member["mp"]), (540, 88))
                self.assertEqual(len(member), 6)
        duplicate = heal_case(steps=[{"kind": "next"}, heal_step(), heal_step()])
        claimed = heal_case(steps=[{"kind": "next"}, {"kind": "claim"}, heal_step()])
        for item in self.invoke([duplicate, claimed])["cases"]:
            self.assertFalse(item["observations"][-1]["value"]["ok"])
            self.assertEqual(item["observations"][-2]["session"], item["session"])

    # {
    #   責務: [test_start_validation_definition_uniqueness_and_copies: 開始情報不正と定義重複を拒否し、再設定と入出力編集が所有資源を変えないか確認します]
    #   処理: [1: 不正な開始情報・定義を試し、正常開始後の独立コピーを編集して回復を実行します]
    #   引数: [self: 開始情報とコピー独立性の検証ケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_start_validation_definition_uniqueness_and_copies(self):
        cases = [heal_case(heal_context=value, steps=[]) for value in (None, [], {}, {"allies": [], "enemies": []})]
        for version in (True, 2, "1"):
            item = heal_case(steps=[])
            item["input"]["skills"]["schema_version"] = version
            cases.append(item)
        for item in self.invoke(cases)["cases"]:
            self.assertFalse(item["initialized"]["ok"])
        duplicate = heal_case()
        duplicate["input"]["skills"]["skills"].append(copy.deepcopy(next(entry for entry in duplicate["input"]["skills"]["skills"] if entry["id"] == "small_heal")))
        missing = heal_case()
        missing["input"]["skills"]["skills"] = [entry for entry in missing["input"]["skills"]["skills"] if entry["id"] != "small_heal"]
        for item in self.invoke([duplicate, missing])["cases"]:
            self.assertFalse(item["observations"][-1]["value"]["ok"])
            self.assertEqual(item["observations"][0]["session"], item["session"])
        copied = heal_case(mutate_initial=True, steps=[{"kind": "input_mutation"}, {"kind": "configure_heal"}, {"kind": "next"}, heal_step(mutate_result=True)])
        item = self.invoke([copied])["cases"][0]
        self.assertEqual(item["observations"][1]["value"]["reason"], "already_initialized")
        self.assertTrue(item["observations"][-1]["value"]["executed"])
        self.assertEqual(item["session"]["teams"]["allies"][0]["mp"], 94)
        self.assertEqual(item["session"]["teams"]["allies"][1]["hp"], 1000)

    # {
    #   責務: [test_joined_level_learning_equipment_permission_and_saved_files: applicationのLv別習得・装備許可を再構築し、個体AI・items・party・コンテンツを保持します]
    #   処理: [1: 専用保存領域を用意し、Lv14の習得成功とLv13の拒否を実行して保存境界を比較します]
    #   引数: [self: 専用コピーの読み取りと保存境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_joined_level_learning_equipment_permission_and_saved_files(self):
        self.seed_state()
        self.seed_record("owned", "maru", name="所有AI保持", level=20)
        self.write("items/items.json", {"schema_version": 1, "items": {"potion": 2}})
        self.write("parties/private.json", {"members": ["owned"], "private": True})
        before, cases, references = self.byte_snapshot(), [], []
        for level in (14, 13):
            ally = MonsterRecord({"id": "ally", "species_id": "ball_slime", "name": "術者", "level": level,
                                  "plus_choices": [], "equipment_id": "slime_sword"}, {"keep": [12, 34]})
            friend = MonsterRecord({"id": "friend", "species_id": "maru", "name": "対象", "level": 20,
                                    "plus_choices": [], "equipment_id": "slime_sword"}, {"keep": [56, 78]})
            enemy = MonsterRecord({"id": "enemy", "species_id": "slime", "name": "敵", "level": 1, "plus_choices": []}, {})
            loader = BattleDataLoader(self.repository)
            built = [loader.build_combatant(record) for record in (ally, friend, enemy)]
            caster_stats, friend_stats, enemy_stats = [member.stats for member in built]
            self.assertIsNone(built[1].equipment)
            source = {"allies": [{"monster": ally.monster, "ai": ally.ai}, {"monster": friend.monster, "ai": friend.ai}],
                      "enemies": [{"monster": enemy.monster, "ai": enemy.ai}],
                      "shuffle_order": [normal.key("allies", "ally"), normal.key("allies", "friend"), normal.key("enemies", "enemy")]}
            # 先行する参加者は既存の基本ぼうぎょで1行動を完了し、術者の予約まで進めます。
            ordered = sorted(zip(source["shuffle_order"], (caster_stats, friend_stats, enemy_stats)), key=lambda pair: pair[1]["speed"], reverse=True)
            steps = []
            for key, _ in ordered:
                steps.append({"kind": "next"})
                if key == normal.key("allies", "ally"):
                    break
                steps.append({"kind": "defend"})
            # applicationには資源更新用APIを増やさず、満HPでMPを払う回復を観測します。
            steps.append(heal_step())
            cases.append(heal_case(source=source, steps=steps))
            references.append(caster_stats["mp"])
        for index, item in enumerate(self.invoke(joined=cases)["joined"]):
            self.assertTrue(item["initialized"]["ok"], item)
            result = item["observations"][-1]["value"]
            if index == 0:
                self.assertTrue(result["executed"], item)
                self.assertEqual((result["healed"], result["spent_mp"]), (0, 6))
                self.assertEqual(item["session"]["teams"]["allies"][0]["mp"], references[index] - 6)
            else:
                self.assertEqual(result["reason"], "skill_not_learned")
                self.assertEqual(item["observations"][-2]["session"], item["session"])
            self.assertTrue(item["input_preserved"])
        self.assertEqual(self.byte_snapshot(), before)

    # {
    #   責務: [test_numeric_precision_invalid_definitions_guard_and_retry: 不正数値・必要な積の精度超過を無消費で拒否し、防御無視とMP不足後の再選択を確認します]
    #   処理: [1: 選択定義の境界を試し、資源と予約の保持・許可装備・同予約での回復再選択を確認します]
    #   引数: [self: 数値・装備・防御と再選択の境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_numeric_precision_invalid_definitions_guard_and_retry(self):
        cases = []
        for field, values in (("heal_ratio", (True, None, "nan", "inf", "bad", 2**53)),
                              ("mp_cost", (0, -1, True, None, "nan", "inf", "3.9", 2**53))):
            for value in values:
                item = heal_case()
                next(entry for entry in item["input"]["skills"]["skills"] if entry["id"] == "small_heal")[field] = value
                cases.append(item)
        for field, special in itertools.product(("heal_ratio", "mp_cost"), ("inf", "nan")):
            cases.append(heal_case(definition_special={field: special}, special_skill_id="small_heal"))
        for bonus in (True, "bad", 2**53):
            item = heal_case()
            item["input"]["equipment"] = {"allies": {"ally": {"allowed_species_ids": ["slime"], "fixed_bonus_damage": bonus}}}
            cases.append(item)
        overflow = heal_case()
        next(entry for entry in overflow["input"]["skills"]["skills"] if entry["id"] == "small_heal")["heal_ratio"] = 2**53 - 1
        cases.append(overflow)
        for item in self.invoke(cases)["cases"]:
            with self.subTest(result=item):
                self.assertFalse(item["observations"][-1]["value"]["ok"])
                self.assertEqual(item["observations"][0]["session"], item["session"])
        precise = heal_case(steps=[{"kind": "next"}, {"kind": "damage", "actor": normal.key("allies", "friend"), "amount": 1}, heal_step()])
        precise["input"]["allies"][1]["stats"]["hp"] = 2**53 - 1
        precise["input"]["allies"][1]["hp"] = 2**53 - 1
        observed = self.invoke([precise])["cases"][0]
        self.assertEqual(observed["session"]["teams"]["allies"][1]["hp"], 2**53 - 1)
        self.assertEqual(observed["observations"][-1]["value"]["healed"], 1)
        retry = heal_case(steps=[{"kind": "next"}, {"kind": "mp", "actor": normal.key("allies", "ally"), "cost": 95}, heal_step(), heal_step(skill_id="healy")])
        observed = self.invoke([retry])["cases"][0]
        self.assertEqual(observed["observations"][2]["value"]["reason"], "insufficient_mp")
        self.assertEqual(observed["observations"][1]["session"], observed["observations"][2]["session"])
        self.assertEqual(observed["observations"][-1]["value"]["spent_mp"], 5)
        guarded = heal_case(basic_defend=True, steps=[{"kind": "next"}, {"kind": "defend"}, {"kind": "next"},
                           {"kind": "damage", "actor": normal.key("allies", "friend"), "amount": 900}, heal_step()])
        guarded["input"]["allies"][1]["stats"]["speed"] = 30
        observed = self.invoke([guarded])["cases"][0]
        self.assertEqual(observed["effects"]["teams"]["allies"]["friend"], 0.5)
        self.assertEqual(observed["observations"][-1]["value"]["healed"], 220)
        forbidden = heal_case(steps=[])
        forbidden["input"]["equipment"] = {"allies": {"ally": {"allowed_species_ids": ["maru"]}}}
        observed = self.invoke([forbidden])["cases"][0]
        self.assertEqual(observed["initialized"]["reason"], "equipment_not_allowed")


# {
#   責務: [HealBoundaryTests: 回復のI/O・AI・画面との責務境界と、純粋数値計算への委譲を静的に検証します]
#   フィールド: []
# }
class HealBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_pure_engine_and_application_delegate_without_extra_resource_fields: 純粋回復に禁止依存がなく、applicationが回復を委譲することを確認します]
    #   処理: [1: ソースの禁止依存・専用委譲と回復性能CLIの存在を照合します]
    #   引数: [self: 純粋依存とPlayer境界を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_pure_engine_and_application_delegate_without_extra_resource_fields(self):
        for name in ("heal_skill_action", "heal_skill_context"):
            source = (fixture.ROOT / f"gdscript/engine/{name}.gd").read_text(encoding="utf-8")
            for forbidden in ("FileAccess", "DirAccess", "OS.", "randf(", "randi(", "Input.", "res://data/", "res://ui/", "res://application/", ".learn(", "await "):
                self.assertNotIn(forbidden, source)
        source = (fixture.ROOT / "gdscript/application/battle_session_application.gd").read_text(encoding="utf-8")
        self.assertIn("_heal.resolve(request)", source)
        self.assertNotIn("Quote.quote_heal", source)
        self.assertNotIn("_session.heal(", source)
        tool = (fixture.ROOT / "tools/performance-check/script/check_gdscript_magic_action.py").read_text(encoding="utf-8")
        self.assertIn('result["microseconds"] <= 3000', tool)
        self.assertIn('"--heal"', tool)


if __name__ == "__main__":
    unittest.main()
