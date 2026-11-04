"""治療付き回復の実資源・最新一件治療を実GodotとPythonで比較します。利用者セーブは使用しません。"""
# {
#   責務: [test_gdscript_cure_heal_action: 専用開始/実適用・厳密拒否・取消・一回治療・正規習得・独立コピーを検証します]
#   フィールド: []
# }
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import itertools
import math
import unittest
from unittest import mock

import test_gdscript_combatant as combatant
import test_gdscript_cure_heal_context as context
import test_gdscript_normal_attack_action as normal
import test_gdscript_status_cure as fixture
import test_gdscript_turn_order as turn


# {
#   責務: [action_case: 術者・味方対象・敵と、全参加者の明示状態/正規定義を独立に用意します]
#   処理: [1: 満資源の固定参加者を作り、味方対象に解除不可・ネスト付き毒・眠りを配置します]
#   引数: [changes: 個別ケースの開始/明示操作条件を上書きする値]
#   戻り値: [result: 共用実Godotプローブの独立開始要求（dict）]
# }
def action_case(**changes):
    source = context.context_case()
    actor = normal.member("ally", speed=20, hp=200)
    actor["mp"], actor["stats"]["mp"] = 100, 100
    friend, enemy = normal.member("friend", speed=5, hp=1000), normal.member("enemy", speed=2, hp=2000)
    teams = {"allies": [{"snapshot": actor, "skill_ids": ["spirit_recover", "small_heal"], "equipment": {}},
                        {"snapshot": friend, "skill_ids": ["spirit_recover"], "equipment": {}}],
             "enemies": [{"snapshot": enemy, "skill_ids": ["spirit_recover"], "equipment": {}}]}
    return {"teams": teams, "skills": source["skills"], "initial_statuses": {
        "allies": {"ally": [], "friend": source["initial_statuses"]["allies"]["same"]}, "enemies": {"enemy": []}},
        "order": [normal.key("allies", "ally"), normal.key("allies", "friend"), normal.key("enemies", "enemy")],
        "steps": [{"operation": "next"}, {"operation": "action", "target": normal.key("allies", "friend"), "roll": 0}], **changes}


# {
#   責務: [CureHealActionTests: 専用要求/保存ダミーと実Godot/Python比較、正規JSON保持の検証を所有します]
#   フィールド: [
#     folder: 共用fixtureの専用要求と保存ダミー領域（Path）
#     saved_files: 要求ごとにbyte保持を確認する保存ダミー（list[Path]）
#     content: Python比較で正規dataを読取専用に参照するプロジェクトルート（Path）
#   ]
# }
@unittest.skipUnless(fixture.godot_fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real cure-heal actions")
class CureHealActionTests(unittest.TestCase):
    # {
    #   責務: [setUp: 専用要求/保存ダミーを用意し、正規JSONを検証前後のbyte保持対象にします]
    #   処理: [1: 共用fixtureを設定し、読取専用dataのハッシュと終了時比較を登録します]
    #   引数: [self: 検証領域と保持確認の所有者]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self):
        fixture.StatusCureQuoteTests.setUp(self)
        self.content = fixture.godot_fixture.ROOT
        originals = {path: hashlib.sha256(path.read_bytes()).digest() for path in (self.content / "data").rglob("*.json")}
        self.addCleanup(self.check_canonical_bytes, originals)

    # {
    #   責務: [check_canonical_bytes: 検証終了時に正規JSONの現在byteを取得し、開始前ハッシュと照合します]
    #   処理: [1: 登録済みJSONのハッシュを終了時に再計算し、書換がないかassertします]
    #   引数: [
    #     self: 正規データ保持を検証するテストケース
    #     originals: 検証開始前の正規JSONパスとSHA-256（dict）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def check_canonical_bytes(self, originals):
        self.assertEqual(originals, {path: hashlib.sha256(path.read_bytes()).digest() for path in originals})

    # {
    #   責務: [run_probe: 実治療区分で共用の実Godot起動・診断・要求/保存ダミーbyte検証へ委譲します]
    #   処理: [1: コピー要求へcure_action=trueを付け、共用fixtureの起動/保持検査を呼びます]
    #   引数: [
    #     self: 専用要求領域の所有者
    #     payload: 実行ケース一覧または反復条件（dict）
    #   ]
    #   戻り値: [result: 診断なしの実Godot観測結果（dict）]
    # }
    def run_probe(self, payload):
        return fixture.StatusCureQuoteTests.run_probe(self, {**copy.deepcopy(payload), "cure_action": True})

    # {
    #   責務: [python_action: 保存/学習せず実Pythonの回復・MP消費・一件治療を明示対象と固定判定値で実行します]
    #   処理: [1: 独立戦闘個体の選択だけを固定し、実更新と元個体/AI/入力の保持を確認します]
    #   引数: [
    #     self: 読取専用dataと専用保存先の所有者
    #     request: 比較時点のteams/状態/定義を持つ開始要求（dict）
    #     hp: 味方対象の比較前現在HP（int）
    #     roll: 0以上1未満の明示判定値（float）
    #   ]
    #   戻り値: [result: 実回復・残HP/MP・残存状態と乱数呼出し有無（dict）]
    # }
    def python_action(self, request, hp, roll):
        snapshots = {side: [entry["snapshot"] for entry in team] for side, team in request["teams"].items()}
        engine = turn.GDScriptTurnTests.engine(self, snapshots["allies"], snapshots["enemies"])
        actor, target = engine.allies
        definition = next(entry for entry in request["skills"]["skills"] if entry["id"] == "spirit_recover")
        actor.skills = [copy.deepcopy(definition)]
        target.hp, target.status_effects = hp, copy.deepcopy(request["initial_statuses"]["allies"]["friend"])
        original = copy.deepcopy([actor.record, target.record, request])
        engine.inference.choose = mock.Mock(return_value=definition)
        engine.learning.learn, engine.rng = mock.Mock(), mock.Mock()
        engine.rng.random.return_value = roll
        engine._take_action(actor, engine.enemies, [target])
        engine.learning.learn.assert_not_called()
        engine.rng.uniform.assert_not_called()
        self.assertEqual(original, [actor.record, target.record, request])
        return {"hp": target.hp, "mp": actor.mp, "healed": target.hp - hp,
                "effects": target.status_effects, "roll_required": engine.rng.random.called}

    # {
    #   責務: [test_current_resources_one_cure_and_finite_mods_match_python: 最新HPと確率境界・空/解除不可/未知状態の実更新をPythonへ照合します]
    #   処理: [1: HP/確率/判定/状態の組合せで実回復と一件解除、独立結果/原本を比較します]
    #   引数: [self: 回復と治療の数値互換を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_current_resources_one_cure_and_finite_mods_match_python(self):
        locked = {"id": "lock", "removable": False}
        effects = [[], [locked], [locked, {"id": "poison", "metadata": {"deck": [1, 2]}}, "sleep", "sleep"], ["mod_unknown"]]
        requests, expected = [], []
        for hp, chance, roll, deck in itertools.product((1, 1000), (-1, 0, 0.03, 1, 2), (0, 0.02, 0.03, 0.99), effects):
            request = action_case()
            request["initial_statuses"]["allies"]["friend"] = copy.deepcopy(deck)
            definition = next(entry for entry in request["skills"]["skills"] if entry["id"] == "spirit_recover")
            definition["status_cure_chance"] = chance
            request["steps"] = [{"operation": "next"}, {"operation": "damage", "target": normal.key("allies", "friend"), "value": 1000 - hp},
                                {"operation": "action", "target": normal.key("allies", "friend"), "roll": roll}]
            expected.append(self.python_action(request, hp, roll))
            requests.append(request)
        for request, reference, actual in zip(requests, expected, self.run_probe({"cases": requests})["results"]):
            with self.subTest(hp=reference["hp"], roll=request["steps"][-1]["roll"]):
                applied = actual["steps"][-1]["result"]
                self.assertTrue(applied["ok"] and applied["executed"], actual)
                self.assertEqual(applied["scope"], "explicit_cure_heal_skill_only")
                self.assertEqual(applied["healed"], reference["healed"])
                self.assertEqual(actual["numeric"]["teams"]["allies"][0]["mp"], reference["mp"])
                self.assertEqual(actual["numeric"]["teams"]["allies"][1]["hp"], reference["hp"])
                self.assertEqual(actual["statuses"]["teams"]["allies"]["friend"], reference["effects"])
                self.assertEqual(applied["numbers"]["roll_required"], reference["roll_required"])
                self.assertTrue(actual["input_preserved"])
                self.assertTrue(all(step["independent"] for step in actual["steps"]))

    # {
    #   責務: [test_invalid_requests_shortage_and_targets_preserve_offered_ticket: 不正要求/必要判定値・未習得・対象不正・MP不足で予約/HPMP/状態を保持するか確認します]
    #   処理: [1: 提示済み票へ型/未知キー/非JSON値/不足/死亡対象を渡し、直前の公開状態と照合します]
    #   引数: [self: 拒否時の非破壊性を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_invalid_requests_shortage_and_targets_preserve_offered_ticket(self):
        target = normal.key("allies", "friend")
        steps = [{"operation": "action", "target": target}, *[{"operation": "action", "target": target, "roll": value}
                 for value in (-1, 1, True, "0.02", None)], *[{"operation": "action", "target": target, "special": value} for value in ("nan", "inf", "object")]]
        steps += [{"operation": "action", "request": value} for value in (None, False, 0, [], {})]
        steps += [{"operation": "action", "target": target, "roll": 0, "extra": {field: value}}
                  for field, value in itertools.product(("status_effects", "remaining_status_effects", "mode", "mp_cost", "cure_chance"), (False, 0, []))]
        steps += [{"operation": "action", "target": key, "roll": 0} for key in (None, normal.key("enemies", "enemy"), normal.key("allies", "missing"))]
        cases = [action_case(steps=[{"operation": "next"}, step]) for step in steps]
        for operation in ("pay", "damage", "flee"):
            key = normal.key("allies", "ally" if operation == "pay" else "friend")
            cases.append(action_case(steps=[{"operation": "next"}, {"operation": operation, "target": key, "value": 100 if operation == "pay" else 1000},
                                            {"operation": "action", "target": target, "roll": 0}]))
        request = action_case()
        request["teams"]["allies"][0]["skill_ids"] = []
        cases.append(request)
        for actual in self.run_probe({"cases": cases})["results"]:
            self.assertFalse(actual["steps"][-1]["result"]["ok"], actual)
            self.assertEqual(actual["steps"][-1]["numeric"], actual["steps"][-2]["numeric"])
            self.assertEqual(actual["steps"][-1]["statuses"], actual["steps"][-2]["statuses"])

    # {
    #   責務: [test_one_cure_per_claim_and_duplicate_action: 取得前/不正治療を拒否し、同じ取得済み票の二度目治療と完了後行動を拒否するか確認します]
    #   処理: [1: 同一予約で失敗→正常治療→再治療→完了→再行動を実行し、一件だけ解除されたことを照合します]
    #   引数: [self: 一予約一回治療の制約を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_one_cure_per_claim_and_duplicate_action(self):
        target = normal.key("allies", "friend")
        treatment = {"operation": "apply_cure", "target": target, "request": {"cure_chance": 1, "roll": 0}}
        request = action_case(steps=[{"operation": "next"}, treatment, {"operation": "claim"},
                    {**treatment, "request": {"cure_chance": 1, "roll": True}}, treatment, treatment,
                    {"operation": "finish"}, {"operation": "action", "target": target, "roll": 0}])
        actual = self.run_probe({"cases": [request]})["results"][0]
        self.assertFalse(actual["steps"][1]["result"]["ok"])
        self.assertFalse(actual["steps"][3]["result"]["ok"])
        self.assertTrue(actual["steps"][4]["result"]["cured"])
        self.assertEqual(actual["steps"][5]["result"], {"ok": False, "reason": "status_cure_already_applied"})
        self.assertFalse(actual["steps"][7]["result"]["ok"])
        self.assertEqual(actual["statuses"]["teams"]["allies"]["friend"], [request["initial_statuses"]["allies"]["friend"][0], "sleep"])
        cases = []
        for empty in (False, True):
            item = action_case(steps=[{"operation": "next"}, {"operation": "claim"},
                               {**treatment, "request": {"cure_chance": 0 if not empty else 1, "roll": None if empty else 0}}, treatment])
            if empty:
                item["initial_statuses"]["allies"]["friend"] = []
            cases.append(item)
        for item, observation in zip(cases, self.run_probe({"cases": cases})["results"]):
            self.assertFalse(observation["steps"][2]["result"]["cured"])
            self.assertEqual(observation["steps"][3]["result"]["reason"], "status_cure_already_applied")
            self.assertEqual(observation["statuses"]["teams"], item["initial_statuses"])
        request = action_case()
        request["steps"] += [request["steps"][-1]]
        actual = self.run_probe({"cases": [request]})["results"][0]
        self.assertFalse(actual["steps"][-1]["result"]["ok"])
        self.assertEqual(actual["steps"][-1]["numeric"], actual["steps"][-2]["numeric"])

    # {
    #   責務: [test_cancellation_validates_roll_and_does_not_pay_or_cure: 術者死亡/逃走・敵なしの取消で資源と状態を保持し、不正判定要求は票を消費しないか確認します]
    #   処理: [1: 提示後に生存条件を変え、不正rollの拒否と正常rollの取消を順に照合します]
    #   引数: [self: 正常取消と不正要求の区別を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_cancellation_validates_roll_and_does_not_pay_or_cure(self):
        cases = []
        for operation, key in (("damage", normal.key("allies", "ally")), ("flee", normal.key("allies", "ally")), ("damage", normal.key("enemies", "enemy"))):
            cases.append(action_case(steps=[{"operation": "next"}, {"operation": operation, "target": key, "value": 2000},
                          {"operation": "action", "target": normal.key("allies", "friend"), "roll": True},
                          {"operation": "action", "target": normal.key("allies", "friend"), "roll": 0}]))
        for actual in self.run_probe({"cases": cases})["results"]:
            self.assertFalse(actual["steps"][2]["result"]["ok"])
            self.assertEqual(actual["steps"][2]["numeric"], actual["steps"][1]["numeric"])
            self.assertTrue(actual["steps"][3]["result"]["ok"])
            self.assertFalse(actual["steps"][3]["result"]["executed"])
            self.assertEqual(actual["steps"][3]["statuses"], actual["steps"][1]["statuses"])
            self.assertEqual(actual["numeric"]["teams"], actual["steps"][1]["numeric"]["teams"])

    # {
    #   責務: [test_modes_initial_status_mismatch_and_ordinary_rejection: 専用設定の区分/状態一致と通常回復による治療拒否を維持するか確認します]
    #   処理: [1: 従来Session・不一致初期状態・区分違いの設定/選択を渡し、拒否理由と状態を照合します]
    #   引数: [self: 専用入口の範囲を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_modes_initial_status_mismatch_and_ordinary_rejection(self):
        target = normal.key("allies", "friend")
        mismatch = action_case()
        mismatch["action_statuses"] = copy.deepcopy(mismatch["initial_statuses"])
        mismatch["action_statuses"]["allies"]["friend"] = []
        cases = [action_case(legacy=True), mismatch, action_case(steps=[{"operation": "ordinary_start_cure"}, {"operation": "cure_start_ordinary"},
                 {"operation": "configure"}, {"operation": "next"}, {"operation": "ordinary_action", "target": target},
                 {"operation": "action", "target": target, "skill_id": "small_heal", "roll": 0}])]
        actual = self.run_probe({"cases": cases})["results"]
        self.assertEqual(actual[0]["configured"]["reason"], "status_not_configured")
        self.assertEqual(actual[1]["configured"]["reason"], "heal_status_mismatch")
        self.assertEqual([step["result"]["reason"] for step in actual[2]["steps"][:3]], ["heal_mode_mismatch", "heal_mode_mismatch", "already_initialized"])
        self.assertTrue(all(not step["result"]["ok"] for step in actual[2]["steps"][-2:]))

    # {
    #   責務: [test_application_canonical_learning_atomic_failure_retry_and_legacy_start: 正規Heroの習得差と専用開始失敗後の再試行、従来入口の未接続を確認します]
    #   処理: [1: Lv59/60・不正明示状態・従来開始を同IDの両陣営で実行し、数値形式と保存保持を照合します]
    #   引数: [self: 読取専用Repositoryと開始調停の境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_application_canonical_learning_atomic_failure_retry_and_legacy_start(self):
        cases = []
        for level in (59, 60):
            cases.append(action_case(joined=True, project_root=str(self.content), records={side: [combatant.record("same", "hero", level=level)] for side in ("allies", "enemies")},
                         order=[normal.key(side, "same") for side in ("allies", "enemies")], initial_statuses={side: {"same": ["poison", "sleep"]} for side in ("allies", "enemies")},
                         steps=[{"operation": "next"}, {"operation": "action", "target": normal.key("allies", "same"), "roll": 0}]))
        valid = copy.deepcopy(cases[1])
        invalid = copy.deepcopy(valid)
        invalid["initial_statuses"] = {"allies": {}, "enemies": {}}
        invalid["steps"] = [{"operation": "statuses"}, {"operation": "start", "input": valid}, *valid["steps"]]
        cases.extend([invalid, {**valid, "legacy": True}])
        actual = self.run_probe({"cases": cases})["results"]
        self.assertFalse(actual[0]["steps"][-1]["result"]["ok"])
        self.assertEqual(actual[0]["steps"][-1]["result"]["reason"], "skill_not_learned")
        self.assertTrue(actual[1]["steps"][-1]["result"]["executed"])
        self.assertEqual(actual[1]["statuses"]["teams"]["allies"]["same"], ["sleep"])
        self.assertEqual(actual[1]["statuses"]["teams"]["enemies"]["same"], ["poison", "sleep"])
        self.assertFalse(actual[2]["started"]["ok"])
        self.assertEqual(actual[2]["steps"][0]["numeric"]["phase"], "not_started")
        self.assertTrue(actual[2]["steps"][1]["result"]["ok"])
        self.assertTrue(actual[2]["steps"][-1]["result"]["executed"])
        self.assertEqual(actual[3]["statuses"], {})
        self.assertFalse(actual[3]["steps"][-1]["result"]["ok"])
        self.assertTrue(all(item["input_preserved"] for item in actual))
        self.assertTrue(all(step["independent"] for item in actual for step in item["steps"]))
        self.assertEqual(set(actual[1]["numeric"]), {"phase", "round", "cursor", "order", "pending", "teams", "scope"})

    # {
    #   責務: [test_latest_statuses_eight_actors_two_rounds_and_input_edits: 同IDの両陣営八体で状態を二回順に解除し、三回目の候補なしと入力編集からの独立性を確認します]
    #   処理: [1: 二ラウンドの本人回復と第三ラウンドの候補なし回復を実行し、最新状態/資源を照合します]
    #   引数: [self: 連続行動と状態所有の寿命を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_latest_statuses_eight_actors_two_rounds_and_input_edits(self):
        request = action_case()
        request["teams"] = {"allies": [], "enemies": []}
        request["initial_statuses"] = {"allies": {}, "enemies": {}}
        order = []
        for side in ("allies", "enemies"):
            for index in range(4):
                identifier = str(index)
                member = normal.member(identifier, hp=1000)
                member["mp"], member["stats"]["mp"] = 100, 100
                request["teams"][side].append({"snapshot": member, "skill_ids": ["spirit_recover"], "equipment": {}})
                request["initial_statuses"][side][identifier] = [{"id": "lock", "removable": False}, "poison", "sleep"]
                order.append(normal.key(side, identifier))
        definition = next(entry for entry in request["skills"]["skills"] if entry["id"] == "spirit_recover")
        definition["status_cure_chance"], definition["heal_ratio"] = 1, 0.03
        cost = definition["mp_cost"]
        request["order"] = order
        request["steps"] = [{"operation": "damage", "target": key, "value": 500} for key in order]
        for round_number in range(2):
            if round_number:
                request["steps"].append({"operation": "begin", "order": order})
            for key in order:
                request["steps"] += [{"operation": "next"}, {"operation": "action", "target": key, "roll": 0}]
        request["steps"] += [{"operation": "begin", "order": order}, {"operation": "next"}, {"operation": "input_edit"},
                             {"operation": "action", "target": order[0]}]
        actual = self.run_probe({"cases": [request]})["results"][0]
        for side in ("allies", "enemies"):
            for index, member in enumerate(actual["numeric"]["teams"][side]):
                count = 3 if side == "allies" and index == 0 else 2
                self.assertEqual((member["hp"], member["mp"]), (500 + 30 * count, 100 - cost * count))
                self.assertEqual(actual["statuses"]["teams"][side][str(index)], [{"id": "lock", "removable": False}])
        self.assertFalse(actual["steps"][-1]["result"]["numbers"]["roll_required"])
        self.assertTrue(actual["input_preserved"])
        self.assertTrue(all(step["independent"] for step in actual["steps"]))

    # {
    #   責務: [test_unsupported_definitions_and_equipment_keep_state: 未対応/不正定義・装備効果を捨てて成功とせず、提示予約と状態を保持するか確認します]
    #   処理: [1: 選択定義の未知効果/型不正と選択装備補正を渡し、行動前後の不変を照合します]
    #   引数: [self: 正規/互換MOD選択の拒否境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_unsupported_definitions_and_equipment_keep_state(self):
        cases = []
        for field, value in itertools.product(("counter", "element", "remaining_status_effects"), (False, 0, [])):
            request = action_case()
            next(entry for entry in request["skills"]["skills"] if entry["id"] == "spirit_recover")[field] = value
            cases.append(request)
        for value in (None, True, {}, "nan"):
            request = action_case()
            next(entry for entry in request["skills"]["skills"] if entry["id"] == "spirit_recover")["status_cure_chance"] = value
            cases.append(request)
        request = action_case()
        request["teams"]["allies"][0]["equipment"] = {"skill_modifiers": {"spirit_recover": {"heal_ratio": False}}}
        cases.append(request)
        for actual in self.run_probe({"cases": cases})["results"]:
            self.assertFalse(actual["steps"][-1]["result"]["ok"], actual)
            self.assertEqual(actual["steps"][-1]["numeric"], actual["steps"][-2]["numeric"])
            self.assertEqual(actual["steps"][-1]["statuses"], actual["steps"][-2]["statuses"])

    # {
    #   責務: [test_real_action_benchmark_checks_outputs_not_only_time: 少量の実回復/治療計測と改変結果で、性能ガードの期待値拒否を確認します]
    #   処理: [1: 完全八行動バッチを実測し、失敗/資源/状態/原本/時間の改変を拒否させます]
    #   引数: [self: 計測結果の信頼境界を確認するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_real_action_benchmark_checks_outputs_not_only_time(self):
        path = self.content / "tools/performance-check/script/check_gdscript_status_cure.py"
        spec = importlib.util.spec_from_file_location("cure_action_performance", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        validator = module.StatusCureBenchmark("unused", argparse.Namespace(iterations=80, samples=3, warmup=80, cure_action=True))
        result = self.run_probe({"performance": True, "iterations": 80, "samples": 3, "warmup": 80})
        # 少数回の実測は機械の負荷で揺れるため、時間は有限の非負値だけを確かめ、3000us上限は標準の性能CLIで判定します。
        self.assertTrue(math.isfinite(result["microseconds"]) and result["microseconds"] >= 0, result)
        result = {**result, "microseconds": 1000}
        self.assertTrue(validator._valid_action_result(result), result)
        for field, value in (("completed", 0), ("actors", 0), ("last", {"ok": False}), ("statuses", {}), ("numeric", {}),
                             ("input_preserved", False), ("microseconds", -1), ("microseconds", 3001)):
            self.assertFalse(validator._valid_action_result({**result, field: value}), field)
        self.assertEqual(self.run_probe({"performance": True, "iterations": 1, "samples": 1, "warmup": 0}),
                         {"ok": False, "reason": "complete_rounds_required"})
