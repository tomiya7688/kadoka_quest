"""Real Godot resource/cursor protocol; limited Python run_round parity, not attack/AI/outcome parity."""
# {
#   責務: [test_gdscript_battle_session: Real Godot resource/cursor protocol; limited Python run_round parity, not attack/AI/outcome parity.]
#   フィールド: []
# }
from __future__ import annotations

import base64
import copy
import json
import os
import random
import subprocess
import unittest
from unittest import mock

import test_gdscript_combatant as combatant
import test_gdscript_roster as fixture
import test_gdscript_turn_order as turn
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.battle_data import BattleDataLoader
from kadoka_quest.data.repository import GameRepository

ROOT = fixture.ROOT
key, member, request = turn.key, turn.member, turn.request


# {
#   責務: [action: test・gdscript・戦闘・セッションのactionを求める]
#   処理: [1: test・gdscript・戦闘・セッションのactionを求める]
#   引数: [
#     kind: 種別
#     values: 値一覧
#   ]
#   戻り値: [result: test・gdscript・戦闘・セッションのactionを求めるための結果（型注釈なし）]
# }
def action(kind, **values):
    return {"kind": kind, **values}


# {
#   責務: [case: test・gdscript・戦闘・セッションのcaseを求める]
#   処理: [1: test・gdscript・戦闘・セッションのcaseを求める]
#   引数: [
#     actions: actions
#     parameters: parameters
#     values: 値一覧
#   ]
#   戻り値: [result: test・gdscript・戦闘・セッションのcaseを求めるための結果（型注釈なし）]
# }
def case(actions=(), parameters=None, **values):
    return {"input": request() if parameters is None else parameters, "actions": list(actions), **values}


# {
#   責務: [cycle: test・gdscript・戦闘・セッションを順に切り替える]
#   処理: [1: test・gdscript・戦闘・セッションを順に切り替える]
#   引数: [values: 値一覧]
#   戻り値: [result: test・gdscript・戦闘・セッションを順に切り替えるための結果（型注釈なし）]
# }
def cycle(**values):
    return [action("next", **values), action("claim", **values), action("finish", **values)]


# {
#   責務: [ticket: test・gdscript・戦闘・セッションの行動権チケットを求める]
#   処理: [1: test・gdscript・戦闘・セッションの行動権チケットを求める]
#   引数: [
#     round_number: ラウンド・数値
#     slot: 編成枠
#     actor: 行動個体
#   ]
#   戻り値: [result: test・gdscript・戦闘・セッションの行動権チケットを求めるための結果（型注釈なし）]
# }
def ticket(round_number=1, slot=0, actor=None):
    return {"round": round_number, "slot": slot, "actor": key("allies", "ally") if actor is None else actor}


# {
#   責務: [SessionBoundaryTests: セッション・boundary・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class SessionBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_pure_session_and_start_application_keep_responsibilities_separate: 検証: pure session and start application keep responsibilities separate]
    #   処理: [1: 検証: pure session and start application keep responsibilities separate]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_pure_session_and_start_application_keep_responsibilities_separate(self):
        source = (ROOT / "gdscript/engine/battle_session.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "OS.", "randf(", "randi(", "RandomNumberGenerator", "Input.",
                          "res://data/", "res://ui/", "res://application/", ".learn(", "normal_attack(", "sort_custom("):
            self.assertNotIn(forbidden, source)
        for delegated in ("Order.plan(", "Order.check_actor(", ".take_damage(", ".pay_mp(", ".flee("):
            self.assertIn(delegated, source)
        source = (ROOT / "gdscript/application/battle_session_application.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "write_atomic", "save(", "Label", ".learn(", ".take_damage("):
            self.assertNotIn(forbidden, source)
        field = (ROOT / "gdscript/application/field_application.gd").read_text(encoding="utf-8")
        self.assertNotIn("battle_session", field)  # No pretend field/scene battle connection.

    # {
    #   責務: [test_stage_performance_guard_is_developer_only: 検証: stage performance guard is developer only]
    #   処理: [1: 検証: stage performance guard is developer only]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_stage_performance_guard_is_developer_only(self):
        source = (ROOT / "tools/performance-check/script/check_gdscript_battle_session.py").read_text(encoding="utf-8")
        self.assertIn('result["microseconds"] <= 2000', source)
        probe = (ROOT / "gdscript/tests/run_battle_session_probe.gd").read_text(encoding="utf-8")
        for operation in ("session.next_actor()", "session.claim(ticket)", "session.finish(ticket)"):
            self.assertIn(operation, probe)
        for directory in (ROOT / "src/kadoka_quest", ROOT / "gdscript/application", ROOT / "gdscript/ui"):
            for path in directory.rglob("*"):
                if path.suffix in (".py", ".gd"):
                    self.assertNotIn("check_gdscript_battle_session", path.read_text(encoding="utf-8"))


# {
#   責務: [GDScriptSessionTests: gdscript・セッション・testsの状態と振る舞いを担当する]
#   フィールド: [
#     setUp: set・up
#     seed_state: seed・状態
#     seed_record: seed・個体レコード
#     write: write
#     byte_snapshot: byte・独立した状態の写し
#     engine: ルール処理
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real battle-session probes")
class GDScriptSessionTests(unittest.TestCase):
    setUp = fixture.GDScriptRosterTests.setUp
    seed_state = fixture.GDScriptRosterTests.seed_state
    seed_record = fixture.GDScriptRosterTests.seed_record
    write = fixture.GDScriptRosterTests.write
    byte_snapshot = combatant.GDScriptCombatantTests.byte_snapshot
    engine = turn.GDScriptTurnTests.engine

    # {
    #   責務: [invoke: gdscript・セッション・testsのinvokeを求める]
    #   処理: [1: gdscript・セッション・testsのinvokeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     cases: cases
    #     joined: joined
    #   ]
    #   戻り値: [result: gdscript・セッション・testsのinvokeを求めるための結果（型注釈なし）]
    # }
    def invoke(self, cases=(), joined=()):
        path = self.content / "session-probe.json"
        path.write_text(json.dumps({"cases": list(cases), "joined": list(joined)}, ensure_ascii=False), encoding="utf-8")
        environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content), KADOKA_SAVE_DIR=str(self.legacy),
                           KADOKA_GDSCRIPT_SAVE_ROOT=str(self.saves), KADOKA_GDSCRIPT_SAVE_NAME="default")
        process = subprocess.run(
            [str(fixture.GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
             "res://tests/run_battle_session_probe.gd", "--", str(path)],
            cwd=self.content, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout[-1600:])
        self.assertNotIn("SCRIPT ERROR", process.stderr)
        self.assertNotIn("ERROR:", process.stderr)
        for line in process.stdout.splitlines():
            if line.startswith("KADOKA_SESSION_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(process.stderr + process.stdout[-1600:])

    # {
    #   責務: [test_offer_claim_finish_are_single_use_and_keep_the_cursor_still_until_finish: 検証: offer claim finish are single use and keep the cursor still until finish]
    #   処理: [1: 検証: offer claim finish are single use and keep the cursor still until finish]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_offer_claim_finish_are_single_use_and_keep_the_cursor_still_until_finish(self):
        steps = [action("next"), action("begin"), action("next"), action("next"), action("finish"),
                 action("claim"), action("claim"), action("next"), action("begin"), action("finish"),
                 action("finish", ticket=ticket()), *cycle(), action("next")]
        result = self.invoke([case(steps)])["cases"][0]
        observations = result["observations"]
        self.assertEqual(observations[0]["value"]["status"], "between_rounds")
        self.assertEqual(observations[2]["value"]["status"], "offered")
        self.assertEqual(observations[3]["value"]["pending"], observations[2]["value"]["pending"])
        self.assertEqual(observations[4]["value"]["reason"], "pending_not_claimed")
        self.assertTrue(observations[5]["value"]["can_execute"])
        self.assertEqual(observations[6]["value"]["reason"], "already_claimed")
        self.assertEqual(observations[7]["value"]["pending"]["stage"], "claimed")
        self.assertEqual(observations[8]["value"]["reason"], "round_not_available")
        self.assertEqual([entry["session"]["cursor"] for entry in observations[2:9]], [0] * 7)
        self.assertEqual(observations[10]["value"]["reason"], "ticket_not_pending")
        self.assertEqual(observations[-1]["value"]["status"], "round_finished")
        self.assertIsNone(result["session"]["pending"])
        self.assertEqual(result["session"]["cursor"], 2)
        self.assertTrue(result["input_preserved"])

    # {
    #   責務: [test_resources_are_retained_for_three_rounds_and_reinitialization_never_heals: 検証: resources are retained for three rounds and reinitialization never heals]
    #   処理: [1: 検証: resources are retained for three rounds and reinitialization never heals]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_resources_are_retained_for_three_rounds_and_reinitialization_never_heals(self):
        actor, foe = key("allies", "ally"), key("enemies", "enemy")
        steps = []
        for index in range(3):
            steps += [action("begin"), action("damage", actor=actor, value=3), action("pay", actor=actor, value=2),
                      action("pay", actor=foe, value=1), action("drain"), action("start")]
        result = self.invoke([case(steps)])["cases"][0]
        for index in range(3):
            status = result["observations"][index * 6 + 4]["session"]
            self.assertEqual(status["round"], index + 1)
            self.assertEqual(status["phase"], "round_finished")
            self.assertEqual((status["teams"]["allies"][0]["hp"], status["teams"]["allies"][0]["mp"]),
                             (30 - (index + 1) * 3, 7 - (index + 1) * 2))
            self.assertEqual(status["teams"]["enemies"][0]["mp"], 7 - (index + 1))
            self.assertEqual(result["observations"][index * 6 + 5]["value"]["reason"], "already_initialized")

    # {
    #   責務: [test_actual_python_run_round_parity_with_scripted_resource_changes_across_three_rounds: 検証: actual python run round parity with scripted resource changes across three rounds]
    #   処理: [1: 検証: actual python run round parity with scripted resource changes across three rounds]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_actual_python_run_round_parity_with_scripted_resource_changes_across_three_rounds(self):
        generator = random.Random(229)
        cases, references = [], []
        for index in range(60):
            teams = [[member(f"shared_{slot}", generator.choice((0, 1, 9, 9, 100))) for slot in range(4)] for _ in range(2)]
            parameters = request(*teams)
            engine = self.engine(*teams)
            steps, rounds = [], []
            for round_number in range(1, 4):
                if not engine._living(engine.allies) or not engine._living(engine.enemies):
                    break
                keys = [key(side, entry.record.monster_id) for side, team in
                        (("allies", engine.allies), ("enemies", engine.enemies)) for entry in engine._living(team)]
                generator.shuffle(keys)
                effects = []
                for identifier in keys:
                    target = generator.choice(keys)
                    effects.append({"kind": generator.choice(("damage", "damage", "pay", "flee")),
                                    "after": identifier, "actor": target, "value": generator.choice((0, 1, 4, 30))})
                steps += [action("begin", order=keys), action("drain", effects=effects)]
                rounds.append(self.reference_round(engine, keys, effects))
            cases.append(case(steps, parameters))
            references.append(rounds)
        results = self.invoke(cases)["cases"]
        for index, (actual, expected) in enumerate(zip(results, references)):
            for round_index, comparison in enumerate(expected):
                with self.subTest(case=index, round=round_index + 1):
                    self.assertTrue(actual["input_preserved"])
                    planned = actual["observations"][round_index * 2]["value"]["plan"]
                    drained = actual["observations"][round_index * 2 + 1]["value"]
                    self.assertEqual(planned["order"], comparison["order"])
                    self.assertEqual(drained["entries"], comparison["entries"])
                    self.assertEqual(drained["session"]["teams"], comparison["teams"])
                    self.assertEqual(drained["session"]["phase"], comparison["phase"])

    # {
    #   責務: [reference_round: gdscript・セッション・testsのreference・ラウンドを求める]
    #   処理: [1: gdscript・セッション・testsのreference・ラウンドを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     engine: ルール処理
    #     shuffle_order: 並べ替え・順序
    #     effects: effects
    #   ]
    #   戻り値: [result: gdscript・セッション・testsのreference・ラウンドを求めるための結果（型注釈なし）]
    # }
    def reference_round(self, engine, shuffle_order, effects):
        captured, entries = {}, []

        # {
        #   責務: [actor_key: gdscript・セッション・testsの行動個体・キーを求める]
        #   処理: [1: gdscript・セッション・testsの行動個体・キーを求める]
        #   引数: [actor: 行動個体]
        #   戻り値: [result: gdscript・セッション・testsの行動個体・キーを求めるための結果（型注釈なし）]
        # }
        def actor_key(actor):
            return key("allies" if any(entry is actor for entry in engine.allies) else "enemies", actor.record.monster_id)

        # {
        #   責務: [snapshot: gdscript・セッション・testsを状態を複製する]
        #   処理: [1: gdscript・セッション・testsを状態を複製する]
        #   引数: [actor: 行動個体]
        #   戻り値: [result: gdscript・セッション・testsを状態を複製するための結果（型注釈なし）]
        # }
        def snapshot(actor):
            return {"identity": copy.deepcopy(actor.record.monster), "stats": copy.deepcopy(actor.stats),
                    "hp": actor.hp, "mp": actor.mp, "fled": actor.fled, "alive": actor.alive}

        # {
        #   責務: [shuffle: gdscript・セッション・testsの並べ替えを求める]
        #   処理: [1: gdscript・セッション・testsの並べ替えを求める]
        #   引数: [actors: actors]
        #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
        # }
        def shuffle(actors):
            mapping = {(actor_key(actor)["side"], actor_key(actor)["id"]): entry
                       for entry in actors for actor in [entry[0]]}
            actors[:] = [mapping[(entry["side"], entry["id"])] for entry in shuffle_order]
            captured["actors"] = actors

        # {
        #   責務: [take_action: actionを反映する]
        #   処理: [1: actionを反映する]
        #   引数: [
        #     actor: 行動個体
        #     foes: foes
        #     friends: friends
        #   ]
        #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
        # }
        def take_action(actor, foes, friends):
            identifier = actor_key(actor)
            eligibility = {"ok": True, "can_act": True, "stop": False, "reason": "ready", "actor": identifier,
                           "friends": [snapshot(entry) for entry in friends], "foes": [snapshot(entry) for entry in foes]}
            applied = []
            for effect in effects:
                if effect["after"] != identifier:
                    continue
                team = engine.allies if effect["actor"]["side"] == "allies" else engine.enemies
                target = next(entry for entry in team if entry.record.monster_id == effect["actor"]["id"])
                value = effect["value"]
                if effect["kind"] == "damage":
                    before = target.hp
                    dealt = min(target.hp, value)
                    target.hp -= dealt
                    applied.append({"ok": True, "requested": value, "previous_hp": before,
                                    "dealt": dealt, "hp": target.hp, "alive": target.alive})
                elif effect["kind"] == "pay":
                    affordable = value <= target.mp
                    target.mp -= value if affordable else 0
                    applied.append({"ok": affordable, "cost": value, "affordable": affordable,
                                    "spent": value if affordable else 0, "mp": target.mp,
                                    **({} if affordable else {"reason": "insufficient_mp"})})
                else:
                    changed = not target.fled
                    target.fled = True
                    applied.append({"ok": True, "changed": changed, "alive": False, "hp": target.hp, "mp": target.mp})
            entries.append({"actor": identifier, "eligibility": eligibility, "applied": applied})

        engine.rng = mock.Mock()
        engine.rng.shuffle.side_effect = shuffle
        engine._take_action = mock.Mock(side_effect=take_action)
        engine._check_end = mock.Mock()  # No attack, AI, reward or outcome port is asserted.
        engine.learning.learn = mock.Mock()
        engine.run_round()
        engine.rng.shuffle.assert_called_once()
        engine.learning.learn.assert_not_called()
        return {"order": [actor_key(entry[0]) for entry in captured["actors"]], "entries": entries,
                "teams": {"allies": [snapshot(entry) for entry in engine.allies],
                          "enemies": [snapshot(entry) for entry in engine.enemies]},
                "phase": "round_finished" if engine._living(engine.allies) and engine._living(engine.enemies) else "stopped"}

    # {
    #   責務: [test_latest_death_flee_and_no_foes_cancel_offered_permission: 検証: latest death flee and no foes cancel offered permission]
    #   処理: [1: 検証: latest death flee and no foes cancel offered permission]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_latest_death_flee_and_no_foes_cancel_offered_permission(self):
        cases = []
        for kind, actor in (("damage", key("allies", "ally")), ("flee", key("allies", "ally")),
                            ("damage", key("enemies", "enemy")), ("flee", key("enemies", "enemy"))):
            cases.append(case([action("begin"), action("next"), action(kind, actor=actor, value=30),
                               action("next"), action("claim"), action("claim", ticket=ticket()), action("next")]))
        for actual in self.invoke(cases)["cases"]:
            observations = actual["observations"]
            self.assertFalse(observations[4]["value"]["can_execute"])
            self.assertIn(observations[4]["value"]["reason"], ("actor_not_alive", "no_living_foes"))
            self.assertEqual(observations[5]["value"]["reason"], "ticket_not_pending")
            self.assertEqual(actual["session"]["phase"], "stopped")
            self.assertIsNone(actual["session"]["pending"])

    # {
    #   責務: [test_cursor_skips_dead_and_fled_actors_without_reordering_or_resurrection: 検証: cursor skips dead and fled actors without reordering or resurrection]
    #   処理: [1: 検証: cursor skips dead and fled actors without reordering or resurrection]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_cursor_skips_dead_and_fled_actors_without_reordering_or_resurrection(self):
        parameters = request([member("a", 20), member("b", 10), member("c", 5)], [member("e", 1)])
        steps = [action("begin"), *cycle(), action("damage", actor=key("allies", "b"), value=30),
                 action("flee", actor=key("allies", "c")), action("next"), action("claim"), action("finish"),
                 action("begin", order=[key("enemies", "e"), key("allies", "a")]), action("drain")]
        actual = self.invoke([case(steps, parameters, mutate_initial=True)])["cases"][0]
        self.assertEqual(actual["observations"][6]["value"]["skipped"], [key("allies", "b"), key("allies", "c")])
        self.assertEqual(actual["observations"][6]["value"]["pending"]["ticket"]["actor"], key("enemies", "e"))
        self.assertEqual(actual["session"]["order"], [key("allies", "a"), key("enemies", "e")])
        self.assertEqual(actual["session"]["teams"]["allies"][1]["hp"], 0)
        self.assertTrue(actual["session"]["teams"]["allies"][2]["fled"])

    # {
    #   責務: [test_invalid_tickets_cannot_consume_or_advance_an_offered_actor: 検証: invalid tickets cannot consume or advance an offered actor]
    #   処理: [1: 検証: invalid tickets cannot consume or advance an offered actor]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_tickets_cannot_consume_or_advance_an_offered_actor(self):
        invalid = [None, {}, [], ticket(2), ticket(slot=1), ticket(actor=key("enemies", "ally")),
                   {**ticket(), "extra": True}, {**ticket(), "round": True}, {**ticket(), "slot": 0.5},
                   ticket(-1), ticket(2**53), {**ticket(), "round": "1"}, {**ticket(), "actor": None}]
        for kind in ("claim", "finish"):
            steps = [action("begin"), action("next")]
            steps += [action(kind, ticket=value) for value in invalid]
            steps += cycle()
            actual = self.invoke([case(steps)])["cases"][0]
            for observation in actual["observations"][2:-3]:
                self.assertFalse(observation["value"]["ok"])
                self.assertEqual(observation["session"]["cursor"], 0)
                self.assertEqual(observation["session"]["pending"]["stage"], "offered")
            self.assertEqual(actual["session"]["cursor"], 1)

    # {
    #   責務: [test_stale_tickets_cannot_claim_same_actor_in_another_round: 検証: stale tickets cannot claim same actor in another round]
    #   処理: [1: 検証: stale tickets cannot claim same actor in another round]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_stale_tickets_cannot_claim_same_actor_in_another_round(self):
        steps = [action("begin"), action("drain"), action("begin"), action("next"),
                 action("claim", ticket=ticket()), action("finish", ticket=ticket()), action("claim"), action("finish")]
        actual = self.invoke([case(steps)])["cases"][0]
        for observation in actual["observations"][4:6]:
            self.assertEqual(observation["value"]["reason"], "ticket_not_pending")
            self.assertEqual(observation["session"]["round"], 2)
            self.assertEqual(observation["session"]["cursor"], 0)
        self.assertTrue(actual["observations"][6]["value"]["can_execute"])

    # {
    #   責務: [test_invalid_start_is_atomic_retryable_and_does_not_restore_runtime_snapshot: 検証: invalid start is atomic retryable and does not restore runtime snapshot]
    #   処理: [1: 検証: invalid start is atomic retryable and does not restore runtime snapshot]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_start_is_atomic_retryable_and_does_not_restore_runtime_snapshot(self):
        invalid = [None, {}, [None], [member("a"), member("a")], [member(str(index)) for index in range(5)],
                   [member("dead", hp=0)], [member("fled", fled=True)], [{**member("spent"), "mp": 0}],
                   [{**member("bad"), "alive": False}], [{**member("bad"), "hp": 31}],
                   [{**member("bad"), "status_effects": []}], [{**member("bad"), "speed_multiplier": 1}]]
        invalid += [[{**member("bad"), "stats": {**combatant.stats(), "hp": value}}]
                    for value in (0, -1, True, None, "30", 1.5, 2**53)]
        cases = [case([action("start", allies=[member("ally")], enemies=[member("enemy")])],
                      {**request(), side: value}) for side in ("allies", "enemies") for value in invalid]
        for actual in self.invoke(cases)["cases"]:
            self.assertFalse(actual["initialized"]["ok"])
            self.assertTrue(actual["observations"][0]["value"]["ok"])
            self.assertEqual(actual["session"]["phase"], "between_rounds")
            self.assertTrue(actual["input_preserved"])

    # {
    #   責務: [test_uninitialized_operations_and_bad_shuffle_never_change_state: 検証: uninitialized operations and bad shuffle never change state]
    #   処理: [1: 検証: uninitialized operations and bad shuffle never change state]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_uninitialized_operations_and_bad_shuffle_never_change_state(self):
        actor = key("allies", "ally")
        steps = [action(kind, actor=actor, value=1)
                 for kind in ("begin", "next", "claim", "finish", "damage", "cost", "pay", "flee")]
        actual = self.invoke([case(steps, start=False)])["cases"][0]
        for observation in actual["observations"]:
            self.assertEqual(observation["value"]["reason"], "not_initialized")
            self.assertEqual(observation["session"]["phase"], "not_started")
        invalid = [None, {}, [], [actor], [actor, actor], [actor, key("enemies", "missing")]]
        steps = [action("begin", order=value) for value in invalid] + [action("begin")]
        actual = self.invoke([case(steps)])["cases"][0]
        for observation in actual["observations"][:-1]:
            self.assertFalse(observation["value"]["ok"])
            self.assertEqual(observation["session"]["round"], 0)
        self.assertTrue(actual["observations"][-1]["value"]["ok"])

    # {
    #   責務: [test_nonfinite_initial_values_refuse_without_partially_initializing_a_team: 検証: nonfinite initial values refuse without partially initializing a team]
    #   処理: [1: 検証: nonfinite initial values refuse without partially initializing a team]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_nonfinite_initial_values_refuse_without_partially_initializing_a_team(self):
        cases = []
        for side in ("allies", "enemies"):
            for location in ([side, 0, "hp"], [side, 0, "mp"], *[[side, 0, "stats", name] for name in combatant.STAT_KEYS]):
                for special in ("inf", "nan"):
                    cases.append(case(special=[{"path": location, "value": special}]))
        for actual in self.invoke(cases)["cases"]:
            with self.subTest(reason=actual["initialized"]):
                self.assertFalse(actual["initialized"]["ok"])
                self.assertEqual(actual["session"]["phase"], "not_started")
                self.assertEqual(actual["session"]["teams"], {"allies": [], "enemies": []})

    # {
    #   責務: [test_unknown_resource_targets_and_bad_amounts_preserve_all_resources: 検証: unknown resource targets and bad amounts preserve all resources]
    #   処理: [1: 検証: unknown resource targets and bad amounts preserve all resources]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_unknown_resource_targets_and_bad_amounts_preserve_all_resources(self):
        invalid_keys = [None, {}, [], key("other", "ally"), key("allies", "missing"), key("enemies", "ally"),
                        key("allies", "../escape"), {**key("allies", "ally"), "extra": 1}]
        steps = [action(kind, actor=actor, value=1) for kind in ("damage", "cost", "pay", "flee") for actor in invalid_keys]
        steps += [action(kind, actor=key("allies", "ally"), value=value)
                  for kind in ("damage", "cost", "pay") for value in (None, True, -1, 1.5, "1", [], {}, 2**53)]
        steps += [action(kind, actor=key("allies", "ally"), special=value)
                  for kind in ("damage", "cost", "pay") for value in ("inf", "nan")]
        actual = self.invoke([case(steps)])["cases"][0]
        for observation in actual["observations"]:
            self.assertFalse(observation["value"]["ok"])
            self.assertEqual(observation["session"]["teams"], actual["initialized"]["session"]["teams"])

    # {
    #   責務: [test_empty_sides_stop_without_outcome_and_cannot_restart: 検証: empty sides stop without outcome and cannot restart]
    #   処理: [1: 検証: empty sides stop without outcome and cannot restart]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_empty_sides_stop_without_outcome_and_cannot_restart(self):
        cases = [case([action("begin"), action("next"), action("begin"), action("start")], request(*teams))
                 for teams in (([], []), ([], [member("e")]), ([member("a")], []))]
        for actual in self.invoke(cases)["cases"]:
            self.assertTrue(actual["observations"][0]["value"]["stop"])
            self.assertEqual(actual["session"]["phase"], "stopped")
            self.assertEqual(actual["observations"][2]["value"]["reason"], "round_not_available")
            self.assertEqual(actual["observations"][3]["value"]["reason"], "already_initialized")
            self.assertNotIn("outcome", actual["session"])

    # {
    #   責務: [test_inputs_outputs_and_same_id_across_sides_are_independent: 検証: inputs outputs and same id across sides are independent]
    #   処理: [1: 検証: inputs outputs and same id across sides are independent]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_inputs_outputs_and_same_id_across_sides_are_independent(self):
        parameters = request([member("shared"), member("other")], [member("shared")])
        steps = [action("snapshot", mutate_result=True), action("begin", mutate_result=True),
                 action("input_mutation"), *cycle(mutate_result=True),
                 action("damage", actor=key("allies", "shared"), value=4),
                 action("pay", actor=key("enemies", "shared"), value=2), action("snapshot", mutate_result=True)]
        actual = self.invoke([case(steps, parameters)])["cases"][0]
        status = actual["session"]
        self.assertEqual(status["order"], parameters["shuffle_order"])
        self.assertEqual(status["cursor"], 1)
        self.assertEqual((status["teams"]["allies"][0]["hp"], status["teams"]["allies"][0]["mp"]), (26, 7))
        self.assertEqual((status["teams"]["enemies"][0]["hp"], status["teams"]["enemies"][0]["mp"]), (30, 5))
        for team in status["teams"].values():
            for entry in team:
                self.assertEqual(entry["stats"]["hp"], 30)
                self.assertEqual(entry["identity"]["name"], "比較個体")
        self.assertFalse(actual["input_preserved"])  # Only intentional caller-side edits.

    # {
    #   責務: [test_readonly_record_start_matches_python_and_preserves_learned_ai_and_saves: 検証: readonly record start matches python and preserves learned ai and saves]
    #   処理: [1: 検証: readonly record start matches python and preserves learned ai and saves]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_readonly_record_start_matches_python_and_preserves_learned_ai_and_saves(self):
        self.seed_state(current_party=["owned", None, None, None], private={"keep": True})
        monster = self.seed_record("owned", level=50, plus_choices=[], equipment_id=None)
        ai = {"schema_version": 1, "battles": 123, "actions": 456, "action_preferences": {"attack": 0.9}}
        self.write("monsters/owned/ai.json", ai)
        self.write("items/items.json", {"items": {"herb": 99}, "private": True})
        self.write("parties/owned.json", {"members": ["owned"]})
        joined = [{"allies": [{"monster": monster, "ai": ai}], "enemies": [combatant.record("owned")],
                   "shuffle_order": [key("enemies", "owned"), key("allies", "owned")]}]
        for species in GameRepository(self.content / "data").list_species_ids():
            for level in (1, 50, 100):
                joined.append({"allies": [combatant.record("a", species, level=level)], "enemies": [combatant.record("e")],
                               "shuffle_order": [key("enemies", "e"), key("allies", "a")]})
        before = self.byte_snapshot()
        actual = self.invoke([case([action("begin"), action("damage", actor=key("allies", "ally"), value=30),
                                    action("pay", actor=key("enemies", "enemy"), value=7), action("drain")])], joined=joined)
        loader = BattleDataLoader(GameRepository(self.content / "data"))
        for parameters, result in zip(joined, actual["joined"]):
            with self.subTest(monster=parameters["allies"][0]["monster"]):
                self.assertTrue(result["value"]["ok"], result)
                self.assertTrue(result["preserved"])
                self.assertEqual(result["again"]["reason"], "already_initialized")
                self.assertEqual(result["session"], result["value"]["session"])
                for side in ("allies", "enemies"):
                    expected = loader.build_combatant(MonsterRecord(parameters[side][0]["monster"], parameters[side][0]["ai"]))
                    entry = result["session"]["teams"][side][0]
                    self.assertEqual(entry["stats"], expected.stats)
                    self.assertEqual((entry["hp"], entry["mp"]), (expected.hp, expected.mp))
                    self.assertNotIn("ai", entry)
        self.assertEqual(self.byte_snapshot(), before)

    # {
    #   責務: [test_application_bad_records_or_shuffle_refuse_without_partial_session_or_repairs: 検証: application bad records or shuffle refuse without partial session or repairs]
    #   処理: [1: 検証: application bad records or shuffle refuse without partial session or repairs]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_application_bad_records_or_shuffle_refuse_without_partial_session_or_repairs(self):
        invalid = [None, {}, [None], [combatant.record("dup"), combatant.record("dup")],
                   [combatant.record(str(index)) for index in range(5)], [combatant.record(species="missing")],
                   [combatant.record(level=101)], [combatant.record(schema_version=99)]]
        joined = [{"allies": value, "enemies": [combatant.record("e")], "shuffle_order": []} for value in invalid]
        joined.append({"allies": [combatant.record("a")], "enemies": [], "shuffle_order": []})
        before = self.byte_snapshot()
        for actual in self.invoke(joined=joined)["joined"]:
            self.assertFalse(actual["value"]["ok"])
            self.assertEqual(actual["session"]["phase"], "not_started")
            self.assertTrue(actual["preserved"])
        self.assertEqual(self.byte_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
