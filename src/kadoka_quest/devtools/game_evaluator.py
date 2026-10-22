# {
#   責務: [game_evaluator: 通常ゲームのコマンド経路で探索・戦闘を進め、評価ログを収集します]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any, Callable

from kadoka_quest.devtools.evaluation_log import EvaluationLog
from kadoka_quest.devtools.field_explorer import FieldExplorer


# {
#   責務: [GameEvaluationRunner: Drive a KadokaQuest-compatible session through its semantic command boundary.]
#   フィールド: [
#     game: 評価対象のゲームセッション
#     explorer: 未試行イベントまでの到達経路を選ぶ探索器
#     log: 操作と停止理由を記録する評価ログ
#     visited_maps: 評価中に訪れたマップIDの集合（set[str]）
#     attempted_events: 操作済みまたは通行不能で断念したイベントキーの集合（set[str]）
#     now: コマンドへ渡す評価内の経過時刻（ミリ秒）
#   ]
# }
class GameEvaluationRunner:
    """Drive a KadokaQuest-compatible session through its semantic command boundary."""

    # {
    #   責務: [__init__: 評価対象と探索器・ログを保持し、訪問履歴と評価時刻を初期化します]
    #   処理: [1: 注入された依存または既定の探索器・ログを選び、評価中だけの履歴を作ります]
    #   引数: [
    #     self: 処理対象インスタンス
    #     game: field_sessionとbattle_sessionとruntimeを公開する評価対象（Any）
    #     explorer: 到達経路の選択器。省略時はFieldExplorerを使います（FieldExplorer | None）
    #     log: 評価結果の記録先。省略時は新規作成します（EvaluationLog | None）
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
    #   責務: [from_default_game: 設定済みの保存先で通常ゲームを生成し、評価器へ渡します]
    #   処理: [1: 保存先の環境変数が設定された後にゲームをimportし、評価器を作ります]
    #   引数: [cls: 対象クラス]
    #   戻り値: [result: 通常ゲームをコマンド経由で操作する評価器（'GameEvaluationRunner'）]
    # }
    @classmethod
    def from_default_game(cls) -> "GameEvaluationRunner":
        from kadoka_quest.apps.game import KadokaQuest

        return cls(KadokaQuest())

    # {
    #   責務: [run: 手数上限まで探索・戦闘を進め、訪問先と停止理由を含むレポートを返します]
    #   処理: [1: 現在の画面に応じて戦闘処理・入力取消・経路移動・イベント調査を選びます]
    #   引数: [
    #     self: 処理対象インスタンス
    #     max_steps: 評価操作の最大手数。1以上で指定します（int）
    #   ]
    #   戻り値: [result: 終了理由・訪問マップ・試行イベント・操作ログを含むレポート（dict[str, Any]）]
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
                activates_step_event = len(directions) == 1 and plan["event"].get("activation", "interact") == "step"
                self._move(step, str(directions[0]), str(plan["event_key"]), activates_step_event)
                continue
            self._interact(step, plan)
        return self.log.report(status=status, visited_maps=self.visited_maps, attempted_events=self.attempted_events)

    # {
    #   責務: [_observe_map: 現在マップへの初回訪問を履歴とログへ記録します]
    #   処理: [1: 未訪問のマップIDだけを追加し、map_enteredを記録します]
    #   引数: [
    #     self: 処理対象インスタンス
    #     step: 訪問を観測した評価の手数（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _observe_map(self, step: int) -> None:
        map_id = str(self.game.field_session.map_data["id"])
        if map_id not in self.visited_maps:
            self.visited_maps.add(map_id)
            self.log.add("map_entered", step, map_id=map_id)

    # {
    #   責務: [_move: 一歩の移動結果を記録し、接触イベントの実行または経路の断念を履歴へ残します]
    #   処理: [1: 移動開始と停止を送り、移動・マップ遷移・通行不能を区別します]
    #   引数: [
    #     self: 処理対象インスタンス
    #     step: 移動を試みる評価の手数（int）
    #     direction: 左右前後を表す移動コマンドの方向（str）
    #     event_key: 移動先イベントをマップ内で識別するキー（str）
    #     activates_step_event: この一歩で接触型イベントの位置へ到達する場合True（bool）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _move(self, step: int, direction: str, event_key: str, activates_step_event: bool) -> None:
        before = (int(self.game.field_session.player.x), int(self.game.field_session.player.y))
        before_map = str(self.game.field_session.map_data["id"])
        self.now += 100
        self._dispatch("field", "move.start", direction=direction, now=self.now)
        self._dispatch("field", "move.stop", direction=direction)
        after = (int(self.game.field_session.player.x), int(self.game.field_session.player.y))
        # 遷移先の座標が元と同じでも、マップが変わっていれば通行不能とは扱いません。
        if after == before and str(self.game.field_session.map_data["id"]) == before_map:
            self.attempted_events.add(event_key)
            self.log.add("blocked", step, direction=direction, position=list(before), event_key=event_key)
        else:
            # 調査型は接近だけで試行済みにせず、次のinteractコマンドまで候補に残します。
            if activates_step_event:
                self.attempted_events.add(event_key)
            self.log.add("move", step, direction=direction, from_position=list(before), to_position=list(after))

    # {
    #   責務: [_interact: 調査コマンドを送り、対象イベントを試行したことを記録します]
    #   処理: [1: 対象キーを履歴へ追加し、通常の調査コマンドと評価ログを送ります]
    #   引数: [
    #     self: 処理対象インスタンス
    #     step: 調査を試みる評価の手数（int）
    #     plan: 対象イベントと一意キーを含む到達済みの探索計画（dict[str, Any]）
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
    #   責務: [_resolve_battle: 通常の戦闘コマンドでログ再生と成長保存を終えてからフィールドへ戻します]
    #   処理: [1: 時刻更新で再生を進め、未決着時だけ戦い、確定保存済みの結果を記録します]
    #   引数: [
    #     self: 処理対象インスタンス
    #     step: 戦闘を処理している評価の手数（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _resolve_battle(self, step: int) -> None:
        self.log.add("battle_started", step)
        rounds = 0
        # 一行ずつの再生待ちを戦闘ラウンドに数えず、別の上限で異常な再生停止も打ち切ります。
        for _ in range(12_000):
            self.now += 1_000
            self._dispatch("battle", "tick", now=self.now)
            battle = self.game.battle_session.battle
            if battle and battle.outcome:
                if self.game.battle_session.playback:
                    continue
                if not self.game.battle_session.finalized:
                    self.log.add("stalled", step, reason="battle_not_finalized")
                    return
                outcome = str(battle.outcome)
                self._dispatch("battle", "return")
                self.log.add("battle_finished", step, outcome=outcome)
                return
            if self.game.battle_session.playback:
                continue
            if rounds >= 120:
                self.log.add("stalled", step, reason="battle_round_limit")
                return
            rounds += 1
            self._dispatch("battle", "execute", command="fight", now=self.now)
        self.log.add("stalled", step, reason="battle_playback_limit")

    # {
    #   責務: [_dispatch: 評価操作を通常ゲームと共通のコマンド受付へ渡します]
    #   処理: [1: 対象画面・操作名・入力値をruntimeへ委譲します]
    #   引数: [
    #     self: 処理対象インスタンス
    #     target: fieldやbattleなどのコマンド受付先（str）
    #     action: move.startやtickなどの操作名（str）
    #     payload: 操作固有の入力値（Any）
    #   ]
    #   戻り値: [result: 通常ゲームのコマンド受付が返す処理結果（Any）]
    # }
    def _dispatch(self, target: str, action: str, **payload: Any) -> Any:
        return self.game.runtime.dispatch(target, action, **payload)
