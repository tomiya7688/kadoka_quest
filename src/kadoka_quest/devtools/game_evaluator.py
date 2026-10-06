# {
#   責務: [game_evaluator: ゲーム・evaluatorの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any, Callable

from kadoka_quest.devtools.evaluation_log import EvaluationLog
from kadoka_quest.devtools.field_explorer import FieldExplorer


# {
#   責務: [GameEvaluationRunner: Drive a KadokaQuest-compatible session through its semantic command boundary.]
#   フィールド: [
#     game: ゲーム
#     explorer: explorer
#     log: ログ
#     visited_maps: visited・マップ一覧（set[str]）
#     attempted_events: attempted・イベント一覧（set[str]）
#     now: 現在時刻
#   ]
# }
class GameEvaluationRunner:
    """Drive a KadokaQuest-compatible session through its semantic command boundary."""

    # {
    #   責務: [__init__: ゲーム・evaluation・runnerが利用する初期状態と依存を設定する]
    #   処理: [1: ゲーム・evaluation・runnerが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     game: ゲーム（Any）
    #     explorer: explorer（FieldExplorer | None）
    #     log: ログ（EvaluationLog | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, game: Any, explorer: FieldExplorer | None = None, log: EvaluationLog | None = None) -> None:
        self.game = game
        self.explorer = explorer or FieldExplorer()
        self.log = log or EvaluationLog()
        self.visited_maps: set[str] = set()
        self.attempted_events: set[str] = set()
        self.now = 0

    # {
    #   責務: [from_default_game: ゲーム・evaluation・runnerのfrom・default・ゲームを求める]
    #   処理: [1: ゲーム・evaluation・runnerのfrom・default・ゲームを求める]
    #   引数: [cls: 対象クラス]
    #   戻り値: [result: ゲーム・evaluation・runnerのfrom・default・ゲームを求めるための結果（'GameEvaluationRunner'）]
    # }
    @classmethod
    def from_default_game(cls) -> "GameEvaluationRunner":
        from kadoka_quest.apps.game import KadokaQuest

        return cls(KadokaQuest())

    # {
    #   責務: [run: ゲーム・evaluation・runnerを実行する]
    #   処理: [1: ゲーム・evaluation・runnerを実行する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     max_steps: max・steps（int）
    #   ]
    #   戻り値: [result: ゲーム・evaluation・runnerを実行するための結果（dict[str, Any]）]
    # }
    def run(self, max_steps: int = 2_000) -> dict[str, Any]:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        status = "step_limit"
        for step in range(1, max_steps + 1):
            self._observe_map(step)
            if self.game.mode == "battle":
                self._resolve_battle(step)
                continue
            if self.game.mode == "password":
                self._dispatch("password", "cancel")
                self.log.add("password_cancelled", step)
                continue
            plan = self.explorer.next_plan(
                self.game.field_session.map_data,
                self.game.field_session.blocks,
                (int(self.game.field_session.player.x), int(self.game.field_session.player.y)),
                self.visited_maps,
                self.attempted_events,
            )
            if plan is None:
                status = "no_reachable_event"
                self.log.add("stalled", step, reason=status, map_id=str(self.game.field_session.map_data["id"]))
                break
            directions = list(plan["directions"])
            if directions:
                self._move(step, str(directions[0]), str(plan["event_key"]), len(directions) == 1)
                continue
            self._interact(step, plan)
        return self.log.report(status=status, visited_maps=self.visited_maps, attempted_events=self.attempted_events)

    # {
    #   責務: [_observe_map: ゲーム・evaluation・runnerのobserve・マップを求める]
    #   処理: [1: ゲーム・evaluation・runnerのobserve・マップを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     step: step（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _observe_map(self, step: int) -> None:
        map_id = str(self.game.field_session.map_data["id"])
        if map_id not in self.visited_maps:
            self.visited_maps.add(map_id)
            self.log.add("map_entered", step, map_id=map_id)

    # {
    #   責務: [_move: ゲーム・evaluation・runnerを移動する]
    #   処理: [1: ゲーム・evaluation・runnerを移動する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     step: step（int）
    #     direction: direction（str）
    #     event_key: イベント・キー（str）
    #     reaches_target: reaches・対象（bool）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _move(self, step: int, direction: str, event_key: str, reaches_target: bool) -> None:
        before = (int(self.game.field_session.player.x), int(self.game.field_session.player.y))
        self.now += 100
        if reaches_target:
            self.attempted_events.add(event_key)
        self._dispatch("field", "move.start", direction=direction, now=self.now)
        self._dispatch("field", "move.stop", direction=direction)
        after = (int(self.game.field_session.player.x), int(self.game.field_session.player.y))
        if after == before:
            self.attempted_events.add(event_key)
            self.log.add("blocked", step, direction=direction, position=list(before), event_key=event_key)
        else:
            self.log.add("move", step, direction=direction, from_position=list(before), to_position=list(after))

    # {
    #   責務: [_interact: ゲーム・evaluation・runnerのinteractを求める]
    #   処理: [1: ゲーム・evaluation・runnerのinteractを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     step: step（int）
    #     plan: plan（dict[str, Any]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _interact(self, step: int, plan: dict[str, Any]) -> None:
        event_key = str(plan["event_key"])
        self.attempted_events.add(event_key)
        event = dict(plan["event"])
        self._dispatch("field", "interact")
        self.log.add("event_attempted", step, event_key=event_key, event_type=str(event.get("type", "message")))

    # {
    #   責務: [_resolve_battle: 戦闘を解決する]
    #   処理: [1: 戦闘を解決する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     step: step（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _resolve_battle(self, step: int) -> None:
        self.log.add("battle_started", step)
        for _ in range(120):
            battle = self.game.battle_session.battle
            if battle and battle.outcome:
                outcome = str(battle.outcome)
                self._dispatch("battle", "return")
                self.log.add("battle_finished", step, outcome=outcome)
                return
            self.now += 1_000
            self._dispatch("battle", "execute", command="fight")
            self._dispatch("battle", "tick", now=self.now)
        self.log.add("stalled", step, reason="battle_round_limit")

    # {
    #   責務: [_dispatch: ゲーム・evaluation・runnerを配送する]
    #   処理: [1: ゲーム・evaluation・runnerを配送する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     target: 対象（str）
    #     action: action（str）
    #     payload: 要求データ（Any）
    #   ]
    #   戻り値: [result: ゲーム・evaluation・runnerを配送するための結果（Any）]
    # }
    def _dispatch(self, target: str, action: str, **payload: Any) -> Any:
        return self.game.runtime.dispatch(target, action, **payload)
