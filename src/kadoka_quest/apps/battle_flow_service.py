# {
#   責務: [battle_flow_service: 戦闘・進行・serviceの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from kadoka_quest.apps.battle_flow_dependencies import BattleFlowDependencies
from kadoka_quest.apps.battle_progression_service import BattleProgressionService


# {
#   責務: [BattleFlowService: Own battle command orchestration, playback timing, and auto flow.]
#   フィールド: [
#     dependencies: dependencies
#     progression: progression
#   ]
# }
class BattleFlowService:
    """Own battle command orchestration, playback timing, and auto flow."""

    # {
    #   責務: [__init__: 戦闘・進行・serviceが利用する初期状態と依存を設定する]
    #   処理: [1: 戦闘・進行・serviceが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     dependencies: dependencies（BattleFlowDependencies）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, dependencies: BattleFlowDependencies) -> None:
        self.dependencies = dependencies
        self.progression = BattleProgressionService(dependencies)

    # {
    #   責務: [session: 戦闘・進行・serviceのセッションを求める]
    #   処理: [1: 戦闘・進行・serviceのセッションを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.dependencies.session（型注釈なし）]
    # }
    @property
    def session(self):
        return self.dependencies.session

    # {
    #   責務: [execute: 戦闘・進行・serviceを実行する]
    #   処理: [1: 戦闘・進行・serviceを実行する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     command: コマンド（str）
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def execute(self, command: str, now: int) -> None:
        battle = self.session.battle
        if not battle or battle.outcome or self.session.playback:
            return

        log_start = len(battle.log)
        if self.session.simulation and command in {"scout", "item"}:
            battle.log.append(
                "模擬戦ではスカウトできない。"
                if command == "scout"
                else "模擬戦では消費アイテムを使用できない。"
            )
        elif command == "fight":
            battle.run_round()
        elif command == "scout":
            self.progression.scout()
        elif command == "item":
            self.progression.use_item()
        elif command == "run":
            self._run()
        else:
            raise ValueError(f"戦闘コマンド {command} は未対応です。")

        self.session.start_playback(log_start, int(now))
        if not self.session.playback:
            self.progression.finalize_if_needed()

    # {
    #   責務: [_run: 戦闘・進行・serviceを実行する]
    #   処理: [1: 戦闘・進行・serviceを実行する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _run(self) -> None:
        battle = self.session.battle
        if battle is None:
            return
        if self.session.simulation:
            battle.log.append("模擬戦から退出した。")
            battle.outcome = "escaped"
            return
        battle.try_run()
        if not battle.outcome:
            battle.run_round()

    # {
    #   責務: [update_playback: playbackを更新する]
    #   処理: [1: playbackを更新する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: playbackを更新するための結果（bool）]
    # }
    def update_playback(self, now: int) -> bool:
        result = self.session.update_playback(int(now))
        if result["completed"]:
            self.progression.finalize_if_needed()
        return bool(result["changed"])

    # {
    #   責務: [selected_command: 戦闘・進行・serviceの選択中・コマンドを求める]
    #   処理: [1: 戦闘・進行・serviceの選択中・コマンドを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 戦闘・進行・serviceの選択中・コマンドを求めるための結果（str）]
    # }
    def selected_command(self) -> str:
        return self.session.selected_command()

    # {
    #   責務: [move_selection: 選択状態を移動する]
    #   処理: [1: 選択状態を移動する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     amount: 量（int）
    #   ]
    #   戻り値: [result: 選択状態を移動するための結果（int）]
    # }
    def move_selection(self, amount: int) -> int:
        return self.session.move_selection(amount)

    # {
    #   責務: [set_selection: 選択状態を設定する]
    #   処理: [1: 選択状態を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     index: 位置番号（int）
    #   ]
    #   戻り値: [result: 選択状態を設定するための結果（int）]
    # }
    def set_selection(self, index: int) -> int:
        return self.session.set_selection(index)

    # {
    #   責務: [stop_auto: 自動を停止する]
    #   処理: [1: 自動を停止する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def stop_auto(self) -> None:
        self.session.stop_auto()

    # {
    #   責務: [toggle_auto: 自動を切り替える]
    #   処理: [1: 自動を切り替える]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: 自動を切り替えるための結果（str | None）]
    # }
    def toggle_auto(self, now: int) -> str | None:
        enabled = self.session.toggle_auto(int(now))
        if enabled is None:
            return None
        return "オート戦闘を開始しました。" if enabled else "オート戦闘を停止しました。"

    # {
    #   責務: [update_auto: 自動を更新する]
    #   処理: [1: 自動を更新する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int）
    #     battle_mode: 戦闘・mode（bool）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def update_auto(self, now: int, *, battle_mode: bool) -> None:
        if not self.session.auto_command_due(int(now), battle_mode=battle_mode):
            return
        self.execute("fight", int(now))
        battle = self.session.battle
        if battle and battle.outcome:
            self.session.stop_auto()
