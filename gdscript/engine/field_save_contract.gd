extends RefCounted
## Pure field save validation/serialization, preserving unrelated state keys.

const Rules = preload("res://engine/field_engine.gd")
const INITIAL_INVENTORY := {"orange": 3}
const DEFAULT_STATE := {
	"schema_version": 1, "map_id": "starting_town", "player": {"x": 18, "y": 14},
	"revive_point": {"map_id": "starting_town", "x": 18, "y": 11, "name": "はじまりの街の教会"},
	"current_party": [], "flags": {"story_complete": false, "ghost_entrance_open": false},
}


static func validate_document(state: Dictionary) -> Dictionary:
	var version: Variant = state.get("schema_version", 1)
	if not _integer(version) or int(version) != 1:
		return {"ok": false, "error": "unsupported_schema", "message": "未対応のセーブ形式です。"}
	if not state.get("map_id") is String or str(state["map_id"]).is_empty() or not state.get("player") is Dictionary:
		return {"ok": false, "error": "invalid_position", "message": "マップ・座標データが不正です。"}
	var player: Dictionary = state["player"]
	if not _integer(player.get("x")) or not _integer(player.get("y")):
		return {"ok": false, "error": "invalid_position", "message": "座標は整数で指定してください。"}
	if player.get("direction", "front") not in Rules.DIRECTIONS:
		return {"ok": false, "error": "invalid_direction", "message": "向きのデータが不正です。"}
	return {"ok": true}


static func _integer(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value)) and float(value) == floorf(float(value))


static func validate_location(state: Dictionary, world: Dictionary, blocks: Dictionary) -> Dictionary:
	var document := validate_document(state)
	if not document["ok"]:
		return document
	var player: Dictionary = state["player"]
	var characters: Array = []
	for mob: Dictionary in world.get("fixed_mobs", []):
		if bool(mob.get("enabled", true)):
			characters.append(mob)
	var rules = Rules.new(world, blocks)
	var move: Dictionary = rules.resolve_player_move(
		int(player["x"]), int(player["y"]), 0, 0, str(player.get("direction", "front")), characters, [],
	)
	if move["kind"] != "moved":
		return {"ok": false, "error": "blocked_position", "message": "復元座標へ移動できません: " + move["reason"]}
	return {"ok": true}


static func capture(base: Dictionary, map_id: String, x: int, y: int, direction: String) -> Dictionary:
	var state := base.duplicate(true)
	state["map_id"] = map_id
	var player: Dictionary = state.get("player", {}).duplicate(true)
	player.merge({"x": x, "y": y, "direction": direction}, true)
	state["player"] = player
	return state
