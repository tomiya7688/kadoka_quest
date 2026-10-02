extends RefCounted
## In-memory exploration state only. Battle, acquisition and persistence are not ported.

const FieldRules = preload("res://engine/field_engine.gd")
var rules = FieldRules.new()
var world: Dictionary = {}
var visible_characters: Array = []
var x := 0
var y := 0
var direction := "front"


func enter_map(map_data: Dictionary, blocks: Dictionary, entry: Dictionary = {}) -> void:
	world = map_data
	rules.set_world(world, blocks)
	x = clampi(int(entry.get("x", world["start"]["x"])), 0, int(world["width"]) - 1)
	y = clampi(int(entry.get("y", world["start"]["y"])), 0, int(world["height"]) - 1)
	visible_characters = []
	for mob: Dictionary in world.get("fixed_mobs", []):
		if bool(mob.get("enabled", true)):
			visible_characters.append(mob.duplicate(true))


func move_player(dx: int, dy: int) -> Dictionary:
	var result: Dictionary = rules.resolve_player_move(x, y, dx, dy, direction, visible_characters, [])
	direction = result["direction"]
	if result["kind"] == "moved":
		x = result["x"]
		y = result["y"]
		result["event"] = rules.step_transition_at(x, y)
	return result


func interaction_event() -> Dictionary:
	var front: Array = rules.front_position(x, y, direction)
	for event: Dictionary in world.get("events", []):
		if (int(event["x"]) == int(front[0]) and int(event["y"]) == int(front[1])) \
			or (int(event["x"]) == x and int(event["y"]) == y):
			if event.get("type") != "transition" or event.get("activation", "step") == "interact":
				return event
	return {}
