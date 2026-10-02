extends RefCounted
## Pure grid rules: Python kadoka_engine.field_engine input/output contract.
## No file access, drawing, Input, scene changes, or save effects.

const DIRECTIONS = {
	"left": [-1, 0], "right": [1, 0], "back": [0, -1], "front": [0, 1],
}

var map_data: Dictionary
var blocks: Dictionary


func _init(world: Dictionary = {}, block_definitions: Dictionary = {}) -> void:
	set_world(world, block_definitions)


func set_world(world: Dictionary, block_definitions: Dictionary) -> void:
	map_data = world
	blocks = block_definitions


static func direction_for_step(dx: int, dy: int, current: String = "front") -> String:
	if dx < 0:
		return "left"
	if dx > 0:
		return "right"
	if dy < 0:
		return "back"
	if dy > 0:
		return "front"
	return current


static func _character_at(characters: Array, x: int, y: int) -> Dictionary:
	for character: Dictionary in characters:
		if int(character["x"]) == x and int(character["y"]) == y:
			return character
	return {}


func resolve_player_move(
	x: int, y: int, dx: int, dy: int, direction: String,
	visible_characters: Array, hidden_characters: Array,
) -> Dictionary:
	var new_x := x + dx
	var new_y := y + dy
	var result := {
		"kind": "blocked", "reason": "out_of_bounds", "x": x, "y": y,
		"direction": direction_for_step(dx, dy, direction),
	}
	if not (0 <= new_x and new_x < int(map_data["width"])
		and 0 <= new_y and new_y < int(map_data["height"])):
		return result
	var hidden := _character_at(hidden_characters, new_x, new_y)
	if not hidden.is_empty():
		result.merge({"reason": "hidden_character", "character": hidden}, true)
		return result
	var visible := _character_at(visible_characters, new_x, new_y)
	if not visible.is_empty():
		result.merge({"reason": "visible_character", "character": visible}, true)
		return result
	for event: Dictionary in map_data.get("events", []):
		if int(event["x"]) == new_x and int(event["y"]) == new_y and bool(event.get("blocking", false)):
			result.merge({"reason": "blocking_event", "event": event}, true)
			return result
	var block_id: String = map_data["tiles"][new_y][new_x]
	var block: Dictionary = blocks.get(block_id, {})
	if not bool(block.get("player_walkable", false)):
		result.merge({"reason": "blocked_tile", "block_id": block_id, "block": block}, true)
		return result
	return {
		"kind": "moved", "reason": "walkable", "x": new_x, "y": new_y,
		"direction": result["direction"], "block_id": block_id,
	}


func front_position(x: int, y: int, direction: String) -> Array:
	var step: Array = DIRECTIONS.get(direction, [0, 1])
	return [x + int(step[0]), y + int(step[1])]


func step_transition_at(x: int, y: int) -> Variant:
	for event: Dictionary in map_data.get("events", []):
		if int(event["x"]) == x and int(event["y"]) == y and event.get("type") == "transition" \
			and event.get("activation", "step") == "step":
			return event
	return null


func nearby_event(x: int, y: int) -> Variant:
	var nearest: Variant = null
	var nearest_distance := 2
	for event: Dictionary in map_data.get("events", []):
		var distance := absi(int(event["x"]) - x) + absi(int(event["y"]) - y)
		if distance < nearest_distance:
			nearest = event
			nearest_distance = distance
	return nearest


func tile_allows(x: int, y: int, rule: String) -> bool:
	if not (0 <= x and x < int(map_data["width"]) and 0 <= y and y < int(map_data["height"])):
		return false
	var block_id: String = map_data["tiles"][y][x]
	return bool(blocks.get(block_id, {}).get(rule, false))


func has_clear_axis_path(start: Array, target: Array, rule: String) -> bool:
	var start_x := int(start[0])
	var start_y := int(start[1])
	var target_x := int(target[0])
	var target_y := int(target[1])
	if start_x != target_x and start_y != target_y:
		return false
	var dx := 0 if start_x == target_x else (1 if target_x > start_x else -1)
	var dy := 0 if start_y == target_y else (1 if target_y > start_y else -1)
	var x := start_x + dx
	var y := start_y + dy
	while x != target_x or y != target_y:
		if not tile_allows(x, y, rule):
			return false
		x += dx
		y += dy
	return true
