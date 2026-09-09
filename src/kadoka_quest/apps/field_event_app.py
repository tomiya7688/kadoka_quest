from __future__ import annotations


class FieldEventApplication:
    """Translate field interactions into one plain-data application effect."""

    OPPOSITE_DIRECTIONS = {
        "left": "right",
        "right": "left",
        "back": "front",
        "front": "back",
    }

    def __init__(self) -> None:
        self.last_effect: dict | None = None

    def resolve_step(self, event: dict | None) -> dict:
        if event is None:
            return self._finish({"kind": "none"})
        return self._finish({"kind": "transition", "target": dict(event["target"])})

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
        if event.get("id") == "orange_tree":
            return self._finish({"kind": "gain_item", "status": status, "item": "orange"})
        return self._finish({"kind": "message", "status": status})

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

    def _finish(self, effect: dict) -> dict:
        self.last_effect = effect
        return effect
