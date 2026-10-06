# {
#   責務: [field_session: フィールド・セッションの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from dataclasses import dataclass

from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.fixed_mob_controller import FixedMobController
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController
from kadoka_engine.player_field_controller import PlayerFieldController


# {
#   責務: [FieldSession: Own one live field's engine and actors without duplicating their state.]
#   フィールド: [
#     field: フィールド
#     player: 主人公（PlayerFieldController）
#     fixed_mobs: fixed・モブ一覧（FixedMobController）
#     hidden_enemies: 非表示・敵（HiddenEnemyController）
#   ]
# }
@dataclass
class FieldSession:
    """Own one live field's engine and actors without duplicating their state.

    The engine owns the world references; controllers retain their own actor
    state. Loading, saving, and progress-dependent population resets remain
    application operations, not session I/O.
    """

    field: FieldEngine
    player: PlayerFieldController
    fixed_mobs: FixedMobController
    hidden_enemies: HiddenEnemyController

    # {
    #   責務: [__post_init__: フィールド・セッションが利用する初期状態と依存を設定する]
    #   処理: [1: フィールド・セッションが利用する初期状態と依存を設定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __post_init__(self) -> None:
        self.replace_field(self.field)

    # {
    #   責務: [replace_field: フィールド・セッションのreplace・フィールドを求める]
    #   処理: [1: フィールド・セッションのreplace・フィールドを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     field: フィールド（FieldEngine）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def replace_field(self, field: FieldEngine) -> None:
        self.field = field
        self.fixed_mobs.field = field
        self.hidden_enemies.field = field
        self.set_world(field.map_data, field.blocks)

    # {
    #   責務: [map_data: フィールド・セッションのマップ・データを求める]
    #   処理: [1: フィールド・セッションのマップ・データを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.field.map・データ（dict）]
    # }
    @property
    def map_data(self) -> dict:
        return self.field.map_data

    # {
    #   責務: [blocks: フィールド・セッションのブロック定義を求める]
    #   処理: [1: フィールド・セッションのブロック定義を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.field.blocks（dict[str, dict]）]
    # }
    @property
    def blocks(self) -> dict[str, dict]:
        return self.field.blocks

    # {
    #   責務: [set_world: マップ状態を設定する]
    #   処理: [1: マップ状態を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_data: マップ・データ（dict）
    #     blocks: ブロック定義（dict[str, dict]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def set_world(self, map_data: dict, blocks: dict[str, dict]) -> None:
        self.field.set_world(map_data, blocks)
        self.hidden_enemies.set_world(map_data, blocks)

    # {
    #   責務: [enter_map: Rebind the loaded world and snap actor position before repopulation.]
    #   処理: [1: Rebind the loaded world and snap actor position before repopulation.]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_data: マップ・データ（dict）
    #     x: X座標（int）
    #     y: Y座標（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def enter_map(self, map_data: dict, x: int, y: int) -> None:
        """Rebind the loaded world and snap actor position before repopulation."""
        self.set_world(map_data, self.blocks)
        self.player.snap(x, y)
