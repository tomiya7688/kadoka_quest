# {
#   責務: [field_progress: フィールド・進行状態の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from kadoka_quest.data.state import StateStore


# {
#   責務: [FieldProgressStore: Persist field position, revival, inventory, flags, and despawn progress.]
#   フィールド: [states: states]
# }
class FieldProgressStore:
    """Persist field position, revival, inventory, flags, and despawn progress."""

    # {
    #   責務: [__init__: フィールド・進行状態・保存先が利用する初期状態と依存を設定する]
    #   処理: [1: フィールド・進行状態・保存先が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     states: states（StateStore）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, states: StateStore) -> None:
        self.states = states

    # {
    #   責務: [save_position: 座標を保存する]
    #   処理: [1: 座標を保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     state: 状態（dict）
    #     map_id: マップ・識別子（str）
    #     x: X座標（int）
    #     y: Y座標（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_position(self, state: dict, map_id: str, x: int, y: int) -> None:
        state["map_id"] = str(map_id)
        state["player"] = {"x": int(x), "y": int(y)}
        self.states.save(state)

    # {
    #   責務: [register_church: 教会を登録する]
    #   処理: [1: 教会を登録する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     state: 状態（dict）
    #     revive: 復活（dict）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def register_church(self, state: dict, revive: dict) -> None:
        state["revive_point"] = dict(revive)
        self.states.save(state)

    # {
    #   責務: [add_item: アイテムを追加する]
    #   処理: [1: アイテムを追加する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     state: 状態（dict）
    #     item_id: アイテム・識別子（str）
    #     amount: 量（int）
    #   ]
    #   戻り値: [result: アイテムを追加するための結果（int）]
    # }
    def add_item(self, state: dict, item_id: str, amount: int = 1) -> int:
        inventory = state.setdefault("inventory", {})
        inventory[str(item_id)] = int(inventory.get(str(item_id), 0)) + int(amount)
        self.states.save(state)
        return int(inventory[str(item_id)])

    # {
    #   責務: [set_flag: フラグを設定する]
    #   処理: [1: フラグを設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     state: 状態（dict）
    #     flag_id: フラグ・識別子（str）
    #     value: 値（bool）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def set_flag(self, state: dict, flag_id: str, value: bool) -> None:
        state.setdefault("flags", {})[str(flag_id)] = bool(value)
        self.states.save(state)

    # {
    #   責務: [mark_despawned: despawnedを状態を記録する]
    #   処理: [1: despawnedを状態を記録する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     state: 状態（dict）
    #     key: キー（str）
    #   ]
    #   戻り値: [result: despawnedを状態を記録するための結果（bool）]
    # }
    def mark_despawned(self, state: dict, key: str) -> bool:
        despawned = state.setdefault("despawned_fixed_mobs", [])
        if str(key) in despawned:
            return False
        despawned.append(str(key))
        self.states.save(state)
        return True

    # {
    #   責務: [revive_point: フィールド・進行状態・保存先の復活・地点を求める]
    #   処理: [1: フィールド・進行状態・保存先の復活・地点を求める]
    #   引数: [state: 状態（dict）]
    #   戻り値: [result: フィールド・進行状態・保存先の復活・地点を求めるための結果（dict）]
    # }
    @staticmethod
    def revive_point(state: dict) -> dict:
        return dict(
            state.get(
                "revive_point",
                {"map_id": "starting_town", "x": 18, "y": 11, "name": "はじまりの街の教会"},
            )
        )
