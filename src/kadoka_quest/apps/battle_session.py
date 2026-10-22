# {
#   責務: [battle_session: 戦闘・セッションの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any


# {
#   責務: [BattleSession: Owns battle lifecycle, command selection, playback, and auto timing state.]
#   フィールド: [
#     COMMANDS: commands
#     initial_log_delay_ms: initial・ログ・delay・ミリ秒
#     action_log_delay_ms: action・ログ・delay・ミリ秒
#     short_log_delay_ms: short・ログ・delay・ミリ秒
#     next_round_delay_ms: next・ラウンド・delay・ミリ秒
#     battle: 戦闘
#     finalized: finalized
#     selection: 選択状態
#     auto: 自動
#     last_auto_tick: last・自動・tick
#     runtime_tick: 実行時・tick
#     playback: playback
#     visible_log_count: visible・ログ・count
#     next_log_tick: next・ログ・tick
#     action_line: action・line
#     focus_id: focus・識別子
#     simulation: simulation
#     fixed_mob_id: fixed・モブ・識別子
#   ]
# }
class BattleSession:
    """Owns battle lifecycle, command selection, playback, and auto timing state."""

    COMMANDS = ("fight", "scout", "item", "run")

    # {
    #   責務: [__init__: 戦闘・セッションが利用する初期状態と依存を設定する]
    #   処理: [1: 戦闘・セッションが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     initial_log_delay_ms: initial・ログ・delay・ミリ秒（int）
    #     action_log_delay_ms: action・ログ・delay・ミリ秒（int）
    #     short_log_delay_ms: short・ログ・delay・ミリ秒（int）
    #     next_round_delay_ms: next・ラウンド・delay・ミリ秒（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(
        self,
        initial_log_delay_ms: int = 140,
        action_log_delay_ms: int = 560,
        short_log_delay_ms: int = 300,
        next_round_delay_ms: int = 600,
    ) -> None:
        self.initial_log_delay_ms = int(initial_log_delay_ms)
        self.action_log_delay_ms = int(action_log_delay_ms)
        self.short_log_delay_ms = int(short_log_delay_ms)
        self.next_round_delay_ms = int(next_round_delay_ms)
        self.battle: Any | None = None
        self.finalized = False
        self.selection = 0
        self.auto = False
        self.last_auto_tick = 0
        self.runtime_tick = 0
        self.playback = False
        self.visible_log_count = 0
        self.next_log_tick = 0
        self.action_line = ""
        self.focus_id: str | None = None
        self.simulation = False
        self.fixed_mob_id: str | None = None

    # {
    #   責務: [begin: 戦闘・セッションを開始する]
    #   処理: [1: 戦闘・セッションを開始する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     battle: 戦闘（Any）
    #     now: 現在時刻（int）
    #     simulation: simulation（bool）
    #     fixed_mob_id: fixed・モブ・識別子（str | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def begin(
        self,
        battle: Any,
        now: int,
        *,
        simulation: bool = False,
        fixed_mob_id: str | None = None,
    ) -> None:
        self.battle = battle
        self.finalized = False
        self.selection = 0
        self.auto = False
        self.last_auto_tick = int(now)
        self.runtime_tick = int(now)
        self.simulation = bool(simulation)
        self.fixed_mob_id = fixed_mob_id
        self.reset_presentation()

    # {
    #   責務: [clear: 戦闘・セッションを消去する]
    #   処理: [1: 戦闘・セッションを消去する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 処理結果（dict[str, Any]）]
    # }
    def clear(self) -> dict[str, Any]:
        result = {
            "outcome": self.battle.outcome if self.battle else None,
            "simulation": self.simulation,
            "fixed_mob_id": self.fixed_mob_id,
        }
        self.battle = None
        self.finalized = False
        self.auto = False
        self.simulation = False
        self.fixed_mob_id = None
        self.reset_presentation()
        return result

    # {
    #   責務: [reset_presentation: presentationの初期状態へ戻す]
    #   処理: [1: presentationの初期状態へ戻す]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def reset_presentation(self) -> None:
        self.playback = False
        self.visible_log_count = len(self.battle.log) if self.battle else 0
        self.next_log_tick = 0
        self.action_line = ""
        self.focus_id = None

    # {
    #   責務: [start_playback: playbackを開始する]
    #   処理: [1: playbackを開始する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     log_start: ログ・start（int）
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: playbackを開始するための結果（bool）]
    # }
    def start_playback(self, log_start: int, now: int) -> bool:
        if not self.battle or len(self.battle.log) <= int(log_start):
            return False
        self.visible_log_count = min(self.visible_log_count, int(log_start))
        self.playback = True
        self.action_line = "行動を開始します……"
        self.focus_id = None
        self.next_log_tick = int(now) + self.initial_log_delay_ms
        return True

    # {
    #   責務: [log_delay: 戦闘・セッションのログ・delayを求める]
    #   処理: [1: 戦闘・セッションのログ・delayを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     line: line（str）
    #   ]
    #   戻り値: [result: 戦闘・セッションのログ・delayを求めるための結果（int）]
    # }
    def log_delay(self, line: str) -> int:
        if line.startswith(("---", "会心！")) or line in {"勝利した！", "パーティは戦闘不能になった。"} or "たおれた" in line:
            return self.short_log_delay_ms
        return self.action_log_delay_ms

    # {
    #   責務: [update_playback: playbackを更新する]
    #   処理: [1: playbackを更新する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: playbackを更新するための結果（dict[str, bool]）]
    # }
    def update_playback(self, now: int) -> dict[str, bool]:
        self.runtime_tick = int(now)
        if not self.playback or not self.battle or int(now) < self.next_log_tick:
            return {"changed": False, "completed": False}
        if self.visible_log_count < len(self.battle.log):
            line = self.battle.log[self.visible_log_count]
            self.visible_log_count += 1
            self.action_line = line
            self.focus_id = self._focus_for_log(line)
            self.next_log_tick = int(now) + self.log_delay(line)
            return {"changed": True, "completed": False}
        self.playback = False
        self.focus_id = None
        self.last_auto_tick = int(now)
        self.visible_log_count = len(self.battle.log)
        return {"changed": True, "completed": True}

    # {
    #   責務: [_focus_for_log: 戦闘・セッションのfocus・for・ログを求める]
    #   処理: [1: 戦闘・セッションのfocus・for・ログを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     line: line（str）
    #   ]
    #   戻り値: [result: 戦闘・セッションのfocus・for・ログを求めるための結果（str | None）]
    # }
    def _focus_for_log(self, line: str) -> str | None:
        if not self.battle or line.startswith("---"):
            return None
        for member in [*self.battle.allies, *self.battle.enemies]:
            if line.startswith(member.name):
                return str(member.record.monster_id)
        return None

    # {
    #   責務: [move_selection: 選択状態を移動する]
    #   処理: [1: 選択状態を移動する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     amount: 量（int）
    #   ]
    #   戻り値: [result: self.selection（int）]
    # }
    def move_selection(self, amount: int) -> int:
        self.selection = (self.selection + int(amount)) % len(self.COMMANDS)
        return self.selection

    # {
    #   責務: [set_selection: 選択状態を設定する]
    #   処理: [1: 選択状態を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     index: 位置番号（int）
    #   ]
    #   戻り値: [result: self.selection（int）]
    # }
    def set_selection(self, index: int) -> int:
        self.selection = max(0, min(len(self.COMMANDS) - 1, int(index)))
        return self.selection

    # {
    #   責務: [selected_command: 戦闘・セッションの選択中・コマンドを求める]
    #   処理: [1: 戦闘・セッションの選択中・コマンドを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 戦闘・セッションの選択中・コマンドを求めるための結果（str）]
    # }
    def selected_command(self) -> str:
        return self.COMMANDS[self.selection % len(self.COMMANDS)]

    # {
    #   責務: [toggle_auto: 自動を切り替える]
    #   処理: [1: 自動を切り替える]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: 自動を切り替えるための結果（bool | None）]
    # }
    def toggle_auto(self, now: int) -> bool | None:
        if not self.battle or self.battle.outcome:
            return None
        self.auto = not self.auto
        self.last_auto_tick = int(now)
        return self.auto

    # {
    #   責務: [stop_auto: 自動を停止する]
    #   処理: [1: 自動を停止する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def stop_auto(self) -> None:
        self.auto = False

    # {
    #   責務: [auto_command_due: 戦闘・セッションの自動・コマンド・dueを求める]
    #   処理: [1: 戦闘・セッションの自動・コマンド・dueを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int）
    #     battle_mode: 戦闘・mode（bool）
    #   ]
    #   戻り値: [result: 戦闘・セッションの自動・コマンド・dueを求めるための結果（bool）]
    # }
    def auto_command_due(self, now: int, *, battle_mode: bool) -> bool:
        self.runtime_tick = int(now)
        if not self.auto or self.playback or not battle_mode or not self.battle or self.battle.outcome:
            return False
        if int(now) - self.last_auto_tick < self.next_round_delay_ms:
            return False
        self.last_auto_tick = int(now)
        return True

    # {
    #   責務: [mark_finalized: finalizedを状態を記録する]
    #   処理: [1: finalizedを状態を記録する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: finalizedを状態を記録するための結果（bool）]
    # }
    def mark_finalized(self) -> bool:
        if not self.battle or not self.battle.outcome or self.finalized or self.playback:
            return False
        self.finalized = True
        self.auto = False
        return True
