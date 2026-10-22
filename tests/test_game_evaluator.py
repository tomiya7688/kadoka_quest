# {
#   責務: [test_game_evaluator: 小さなインメモリマップで評価器の経路選択・移動・戦闘帰還・停止理由を検査します]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.devtools.field_explorer import FieldExplorer
from kadoka_quest.devtools.game_evaluator import GameEvaluationRunner


# {
#   責務: [_Repository: 評価テスト用の利用可能マップIDを返します]
#   フィールド: []
# }
class _Repository:
    # {
    #   責務: [list_maps: 評価テストで使う二つのマップIDを返します]
    #   処理: [1: 評価テストで使う二つのマップIDを返します]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: マップ一覧を列挙するための結果（list[str]）]
    # }
    def list_maps(self) -> list[str]:
        return ["first", "second"]


# {
#   責務: [_Runtime: 評価テストの小マップに対して移動・接触遷移・調査回数・戦闘帰還を再現します]
#   フィールド: [game: ゲーム]
# }
class _Runtime:
    # {
    #   責務: [__init__: 実行時が利用する初期状態と依存を設定する]
    #   処理: [1: 実行時が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     game: コマンドによって変更するテスト用ゲーム状態（'_Game'）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, game: "_Game") -> None:
        self.game = game

    # {
    #   責務: [dispatch: 評価器から受け取った移動・調査・帰還コマンドを、インメモリの状態へ反映します]
    #   処理: [1: 評価器から受け取った移動・調査・帰還コマンドを、インメモリの状態へ反映します]
    #   引数: [
    #     self: 処理対象インスタンス
    #     target: fieldまたはbattleのコマンド受付先（str）
    #     action: 移動開始・調査・戦闘帰還などの操作名（str）
    #     payload: コマンドへ渡す移動方向などの入力（object）
    #   ]
    #   戻り値: [result: 実行時を配送するための結果（object）]
    # }
    def dispatch(self, target: str, action: str, **payload: object) -> object:
        if target == "field" and action == "move.start":
            field = self.game.field_session
            player = field.player
            direction = str(payload["direction"])
            dx, dy = {"left": (-1, 0), "right": (1, 0), "back": (0, -1), "front": (0, 1)}[direction]
            next_x, next_y = player.x + dx, player.y + dy
            if 0 <= next_x < field.map_data["width"] and 0 <= next_y < field.map_data["height"]:
                player.x, player.y = next_x, next_y
            for event in field.map_data.get("events", []):
                if (event["x"], event["y"]) == (player.x, player.y) and event.get("activation") == "step":
                    field.map_data = self.game.maps[event["target"]["map_id"]]
                    player.x, player.y = 0, 0
            return True
        if target == "field" and action == "interact":
            self.game.interactions += 1
        if target == "battle" and action == "return":
            self.game.battle_session.battle = None
            self.game.mode = "field"
        return True


# {
#   責務: [_Game: 評価器の経路と停止条件を検査する、二つの小マップとゲーム状態を保持します]
#   フィールド: [
#     maps: マップ一覧
#     field_session: フィールド・セッション
#     mode: 現在の画面名
#     runtime: 状態変更を再現するテスト用コマンド受付
#     repository: データ取得先
#     interactions: 調査コマンドの受信回数
#     battle_session: 戦闘・セッション
#   ]
# }
class _Game:
    # {
    #   責務: [__init__: ゲームが利用する初期状態と依存を設定する]
    #   処理: [1: ゲームが利用する初期状態と依存を設定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self) -> None:
        self.maps = {
            "first": {
                "id": "first", "width": 3, "height": 1, "tiles": [["floor", "floor", "floor"]],
                "events": [
                    {"id": "local", "type": "message", "x": 0, "y": 0, "activation": "interact"},
                    {"id": "to_second", "type": "transition", "x": 2, "y": 0, "activation": "step", "target": {"map_id": "second"}},
                ],
            },
            "second": {"id": "second", "width": 1, "height": 1, "tiles": [["floor"]], "events": []},
        }
        self.field_session = SimpleNamespace(
            map_data=self.maps["first"],
            blocks={"floor": {"player_walkable": True}, "wall": {"player_walkable": False}},
            player=SimpleNamespace(x=0, y=0),
        )
        self.mode = "field"
        self.runtime = _Runtime(self)
        self.repository = _Repository()
        self.interactions = 0
        self.battle_session = SimpleNamespace(battle=None, playback=False, finalized=True)


# {
#   責務: [FieldExplorerTests: 評価器の経路優先度・障害物回避・訪問記録・戦闘帰還・通行不能の断念を検査します]
#   フィールド: []
# }
class FieldExplorerTests(unittest.TestCase):
    # {
    #   責務: [test_unvisited_transition_is_prioritized_over_local_event: 未訪問マップへの接触遷移が同じマップの調査イベントより優先されることを検査します]
    #   処理: [1: 未訪問マップへの接触遷移が同じマップの調査イベントより優先されることを検査します]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_unvisited_transition_is_prioritized_over_local_event(self) -> None:
        game = _Game()
        plan = FieldExplorer().next_plan(game.field_session.map_data, game.field_session.blocks, (0, 0), {"first"}, set())

        self.assertEqual(plan["event_key"], "first:to_second")
        self.assertEqual(plan["directions"], ["right", "right"])

    # {
    #   責務: [test_planner_routes_around_blocking_event: 通行を妨げる看板を避け、接触型の出口へ到達する経路を検査します]
    #   処理: [1: 通行を妨げる看板を避け、接触型の出口へ到達する経路を検査します]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_planner_routes_around_blocking_event(self) -> None:
        map_data = {
            "id": "route", "width": 3, "height": 2,
            "tiles": [["floor", "floor", "floor"], ["floor", "floor", "floor"]],
            "events": [
                {"id": "sign", "type": "message", "x": 1, "y": 0, "blocking": True},
                {"id": "exit", "type": "transition", "x": 2, "y": 0, "activation": "step", "target": {"map_id": "next"}},
            ],
        }
        plan = FieldExplorer().next_plan(map_data, {"floor": {"player_walkable": True}}, (0, 0), {"route"}, set())

        self.assertEqual(plan["directions"], ["front", "right", "right", "back"])

    # {
    #   責務: [test_runner_visits_connected_map_and_logs_stall: 遷移先への訪問を記録し、到達可能な未試行イベントがなくなると停止することを検査します]
    #   処理: [1: 遷移先への訪問を記録し、到達可能な未試行イベントがなくなると停止することを検査します]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_runner_visits_connected_map_and_logs_stall(self) -> None:
        game = _Game()
        report = GameEvaluationRunner(game).run(max_steps=10)

        self.assertEqual(report["status"], "no_reachable_event")
        self.assertEqual(report["visited_maps"], ["first", "second"])
        self.assertTrue(any(entry["kind"] == "map_entered" and entry["map_id"] == "second" for entry in report["entries"]))
        self.assertTrue(any(entry["kind"] == "stalled" for entry in report["entries"]))

    # {
    #   責務: [test_runner_rejects_zero_steps: 評価手数に0を指定すると処理を始めず拒否することを検査します]
    #   処理: [1: 評価手数に0を指定すると処理を始めず拒否することを検査します]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_runner_rejects_zero_steps(self) -> None:
        with self.assertRaises(ValueError):
            GameEvaluationRunner(_Game()).run(0)

    # {
    #   責務: [test_battle_result_is_recorded_before_return_clears_session: 帰還で戦闘状態を消す前の勝利結果が評価ログへ残ることを検査します]
    #   処理: [1: 帰還で戦闘状態を消す前の勝利結果が評価ログへ残ることを検査します]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_battle_result_is_recorded_before_return_clears_session(self) -> None:
        game = _Game()
        game.mode = "battle"
        game.battle_session.battle = SimpleNamespace(outcome="victory")
        report = GameEvaluationRunner(game).run(max_steps=1)
        self.assertIsNone(game.battle_session.battle)
        self.assertTrue(any(entry["kind"] == "battle_finished" and entry["outcome"] == "victory" for entry in report["entries"]))

    # {
    #   責務: [test_blocked_route_is_logged_once_then_abandoned: 動けない経路を一回だけ記録して断念し、同じイベントを繰り返さないことを検査します]
    #   処理: [1: 動けない経路を一回だけ記録して断念し、同じイベントを繰り返さないことを検査します]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_blocked_route_is_logged_once_then_abandoned(self) -> None:
        game = _Game()
        original_dispatch = game.runtime.dispatch

        # {
        #   責務: [blocked_dispatch: 移動開始だけを無効化し、通行不能のテスト条件を再現します]
        #   処理: [1: 移動開始だけを無効化し、通行不能のテスト条件を再現します]
        #   引数: [
        #     target: fieldまたはbattleのコマンド受付先（str）
        #     action: 移動開始・調査・戦闘帰還などの操作名（str）
        #     payload: コマンドへ渡す移動方向などの入力（object）
        #   ]
        #   戻り値: [result: フィールド・explorer・testsのblocked・dispatchを求めるための結果（object）]
        # }
        def blocked_dispatch(target: str, action: str, **payload: object) -> object:
            if target == "field" and action == "move.start":
                return True
            return original_dispatch(target, action, **payload)

        game.runtime.dispatch = blocked_dispatch
        report = GameEvaluationRunner(game).run(max_steps=10)

        blocked = [entry for entry in report["entries"] if entry["kind"] == "blocked"]
        self.assertEqual(len(blocked), 1)
        self.assertIn("first:to_second", report["attempted_events"])


if __name__ == "__main__":
    unittest.main()
