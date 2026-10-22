# {
#   責務: [field_command_app: フィールド・コマンド・appの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand


# {
#   責務: [FieldCommandApplication: Executes semantic field commands without knowing pygame events.]
#   フィールド: [session: セッション]
# }
class FieldCommandApplication:
    """Executes semantic field commands without knowing pygame events."""

    # {
    #   責務: [__init__: フィールド・コマンド・applicationが利用する初期状態と依存を設定する]
    #   処理: [1: フィールド・コマンド・applicationが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     session: セッション（Any）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, session: Any) -> None:
        self.session = session

    # {
    #   責務: [handle: フィールド・コマンド・applicationを入力を処理する]
    #   処理: [1: フィールド・コマンド・applicationを入力を処理する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     command: コマンド（AppCommand）
    #   ]
    #   戻り値: [result: フィールド・コマンド・applicationを入力を処理するための結果（Any）]
    # }
    def handle(self, command: AppCommand) -> Any:
        payload = command.payload
        if command.action == "move.start":
            return self.session.start_held_direction(str(payload["direction"]), int(payload["now"]))
        if command.action == "move.stop":
            self.session.stop_held_direction(str(payload["direction"]))
            return True
        if command.action == "interact":
            return self.session.interact()
        if command.action == "use":
            return self.session.use_field_requirement(
                str(payload["kind"]), str(payload["id"])
            )
        if command.action == "map.change":
            return self.session.change_map(
                str(payload["map_id"]),
                int(payload["x"]),
                int(payload["y"]),
                payload.get("message"),
            )
        if command.action == "mob.despawn":
            return self.session.despawn_fixed_mob_by_id(str(payload["npc_id"]))
        if command.action == "church.register":
            return self.session.register_church(dict(payload["revive"]))
        if command.action == "item.gain":
            return self.session.gain_field_item(str(payload["item_id"]))
        if command.action == "pickup":
            return self.session.field_pickup()
        if command.action == "party.select":
            return self.session.select_party(int(payload["index"]))
        if command.action == "tactic.cycle":
            return self.session.cycle_tactic()
        if command.action == "ai.reset":
            return self.session.reset_selected_ai()
        if command.action == "acquire.scan":
            return self.session.scan_acquire()
        if command.action == "party.save_preset":
            return self.session.save_preset()
        if command.action == "party.load_next_preset":
            return self.session.load_next_preset()
        if command.action == "tick":
            now = int(payload["now"])
            moved = self.session.update_field_mobs(now)
            repeated = self.session.update_held_move(now)
            return bool(moved or repeated)
        raise ValueError(f"フィールドコマンド {command.action} は未対応です。")
