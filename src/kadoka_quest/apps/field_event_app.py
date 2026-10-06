# {
#   責務: [field_event_app: フィールド・イベント・appの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations


# {
#   責務: [FieldEventApplication: Translate field interactions into one plain-data application effect.]
#   フィールド: [
#     OPPOSITE_DIRECTIONS: opposite・directions
#     last_effect: last・効果
#   ]
# }
class FieldEventApplication:
    """Translate field interactions into one plain-data application effect."""

    OPPOSITE_DIRECTIONS = {
        "left": "right",
        "right": "left",
        "back": "front",
        "front": "back",
    }

    # {
    #   責務: [__init__: フィールド・イベント・applicationが利用する初期状態と依存を設定する]
    #   処理: [1: フィールド・イベント・applicationが利用する初期状態と依存を設定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self) -> None:
        self.last_effect: dict | None = None

    # {
    #   責務: [resolve_step: stepを解決する]
    #   処理: [1: stepを解決する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     event: イベント（dict | None）
    #   ]
    #   戻り値: [result: stepを解決するための結果（dict）]
    # }
    def resolve_step(self, event: dict | None) -> dict:
        if event is None:
            return self._finish({"kind": "none"})
        return self._finish({"kind": "transition", "target": dict(event["target"])})

    # {
    #   責務: [resolve_interaction: interactionを解決する]
    #   処理: [1: interactionを解決する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     npc: npc（dict | None）
    #     event: イベント（dict | None）
    #     player_direction: 主人公・direction（str）
    #     dialogue: 会話（str | None）
    #   ]
    #   戻り値: [result: interactionを解決するための結果（dict）]
    # }
    def resolve_interaction(
        self,
        npc: dict | None,
        event: dict | None,
        player_direction: str,
        dialogue: str | None = None,
    ) -> dict:
        if npc is not None:
            npc["direction"] = self.OPPOSITE_DIRECTIONS.get(str(player_direction), "front")
            status = f"{npc.get('name', npc['species_id'])}『{dialogue or '……'}』"
            if npc.get("interaction", "talk") == "battle":
                level = max(1, min(100, int(npc.get("level", 1))))
                return self._finish(
                    {
                        "kind": "npc_battle",
                        "status": status,
                        "npc_id": str(npc["id"]),
                        "spawn": {
                            "species_id": npc["species_id"],
                            "min_level": level,
                            "max_level": level,
                        },
                    }
                )
            if npc.get("despawn_after_interaction", npc.get("despawn_after_talk", False)):
                return self._finish(
                    {"kind": "npc_despawn", "status": status, "npc_id": str(npc["id"])}
                )
            return self._finish({"kind": "message", "status": status})

        if event is None:
            return self._finish({"kind": "message", "status": "近くに調べられるものはありません。"})
        status = str(event.get("text", "何もない。"))
        event_type = str(event.get("type", "message"))
        if event_type == "transition" and event.get("activation") == "interact":
            return self._finish(
                {"kind": "transition", "status": status, "target": dict(event["target"])}
            )
        if event_type == "church":
            return self._finish(
                {"kind": "register_church", "status": status, "revive": dict(event["revive"])}
            )
        if event_type == "password_spring":
            return self._finish({"kind": "open_password", "status": status})
        if event_type == "open_manager":
            return self._finish({"kind": "open_manager", "status": status})
        if event_type == "open_simulation_manager":
            return self._finish({"kind": "open_simulation_manager", "status": status})
        if event.get("id") == "orange_tree":
            return self._finish({"kind": "gain_item", "status": status, "item": "orange"})
        return self._finish({"kind": "message", "status": status})

    # {
    #   責務: [resolve_use: Resolve a data-defined item/skill use at a map location.]
    #   処理: [1: Resolve a data-defined item/skill use at a map location.]
    #   引数: [
    #     self: 処理対象インスタンス
    #     events: イベント一覧（list[dict]）
    #     player_position: 主人公・座標（tuple[int, int]）
    #     requirement_kind: requirement・種別（str）
    #     requirement_id: requirement・識別子（str）
    #   ]
    #   戻り値: [result: Resolve a data-defined item/skill use at a map location.ための結果（dict）]
    # }
    def resolve_use(
        self,
        events: list[dict],
        player_position: tuple[int, int],
        requirement_kind: str,
        requirement_id: str,
    ) -> dict:
        """Resolve a data-defined item/skill use at a map location.

        The event is deliberately declarative: it can only return one of the
        existing plain field effects.  A mismatched use is not an interaction
        and therefore has no side effect beyond its short status message.
        """
        kind = str(requirement_kind)
        identifier = str(requirement_id)
        player_x, player_y = (int(player_position[0]), int(player_position[1]))
        for event in events:
            if not isinstance(event, dict) or event.get("type") != "use_requirement":
                continue
            required = event.get("required", {})
            if not isinstance(required, dict):
                continue
            if required.get("kind") != kind or required.get("id") != identifier:
                continue
            radius = max(0, int(event.get("radius", 0)))
            distance = abs(int(event.get("x", -1)) - player_x) + abs(int(event.get("y", -1)) - player_y)
            if distance > radius:
                continue
            effect = dict(event.get("effect", {}))
            effect_kind = str(effect.get("kind", "message"))
            if effect_kind not in {"message", "gain_item"}:
                return self._finish({"kind": "none", "status": "この仕掛けは設定が不正です。"})
            effect["kind"] = effect_kind
            effect.setdefault("status", str(event.get("text", "何かが起きた。")))
            return self._finish(effect)
        return self._finish({"kind": "none", "status": "何も起きない。"})

    # {
    #   責務: [_finish: フィールド・イベント・applicationを終了処理を行う]
    #   処理: [1: フィールド・イベント・applicationを終了処理を行う]
    #   引数: [
    #     self: 処理対象インスタンス
    #     effect: 効果（dict）
    #   ]
    #   戻り値: [result: 効果（dict）]
    # }
    def _finish(self, effect: dict) -> dict:
        self.last_effect = effect
        return effect
