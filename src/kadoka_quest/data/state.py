# {
#   責務: [state: 状態の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
from typing import Any

from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.paths import SAVE_ROOT


DEFAULT_STATE: dict[str, Any] = {
    "schema_version": 1,
    "map_id": "starting_town",
    "player": {"x": 18, "y": 14},
    "revive_point": {"map_id": "starting_town", "x": 18, "y": 11, "name": "はじまりの街の教会"},
    "current_party": [],
    "inventory": {"orange": 3},
    "flags": {"story_complete": False, "ghost_entrance_open": False},
}


# {
#   責務: [StateStore: 状態・保存先の状態と振る舞いを担当する]
#   フィールド: [path: パス]
# }
class StateStore:
    # {
    #   責務: [__init__: 状態・保存先が利用する初期状態と依存を設定する]
    #   処理: [1: 状態・保存先が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     path: パス（Path | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or (SAVE_ROOT / "state.json"))

    # {
    #   責務: [load: 状態・保存先を読み込む]
    #   処理: [1: 状態・保存先を読み込む]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 状態・保存先を読み込むための結果（dict[str, Any]）]
    # }
    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                **DEFAULT_STATE,
                "player": dict(DEFAULT_STATE["player"]),
                "revive_point": dict(DEFAULT_STATE["revive_point"]),
                "current_party": [],
                "inventory": dict(DEFAULT_STATE["inventory"]),
                "flags": dict(DEFAULT_STATE["flags"]),
            }
        state = read_json(self.path)
        item_path = self.path.parent / "items" / "items.json"
        if item_path.exists():
            state["inventory"] = dict(read_json(item_path).get("items", {}))
        for key, default in DEFAULT_STATE.items():
            state.setdefault(key, default.copy() if isinstance(default, dict) else list(default) if isinstance(default, list) else default)
        return state

    # {
    #   責務: [save: 状態・保存先を保存する]
    #   処理: [1: 状態・保存先を保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     state: 状態（dict[str, Any]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save(self, state: dict[str, Any]) -> None:
        payload = dict(state)
        inventory = dict(payload.pop("inventory", {}))
        write_json(self.path, payload)
        write_json(self.path.parent / "items" / "items.json", {"schema_version": 1, "items": inventory})

    # {
    #   責務: [ensure_starters: startersを必要な状態を用意する]
    #   処理: [1: startersを必要な状態を用意する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     state: 状態（dict[str, Any]）
    #     monsters: モンスター一覧（MonsterStore）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def ensure_starters(self, state: dict[str, Any], monsters: MonsterStore) -> None:
        hero = monsters.ensure_species("hero", "主人公")
        ball = monsters.ensure_species("ball_slime", "ボールスライム")
        valid = [record.monster_id for record in monsters.list_records()]
        current = [item for item in state.get("current_party", []) if item in valid]
        for record in (hero, ball):
            if record.monster_id not in current and len(current) < 4:
                current.append(record.monster_id)
        state["current_party"] = current[:4]
        self.save(state)

    # {
    #   責務: [party_records: 状態・保存先のパーティ・個体レコード一覧を求める]
    #   処理: [1: 状態・保存先のパーティ・個体レコード一覧を求める]
    #   引数: [
    #     state: 状態（dict[str, Any]）
    #     monsters: モンスター一覧（MonsterStore）
    #   ]
    #   戻り値: [result: 状態・保存先のパーティ・個体レコード一覧を求めるための結果（list）]
    # }
    @staticmethod
    def party_records(state: dict[str, Any], monsters: MonsterStore) -> list:
        return [record for monster_id in state.get("current_party", []) if (record := monsters.get(str(monster_id)))]

