extends RefCounted
## In-memory exploration state; clock advances only while the field is active.

const FieldRules = preload("res://engine/field_engine.gd")
const FixedMobs = preload("res://engine/fixed_mob_controller.gd")
const RandomSource = preload("res://engine/field_random.gd")
var rules = FieldRules.new()
var fixed_mobs = FixedMobs.new(rules, RandomSource.new())
var clock_ms := 0.0
var despawned_fixed_mobs: Array = []
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
	fixed_mobs.reset(world, blocks, despawned_fixed_mobs, [x, y], int(clock_ms))
	visible_characters = fixed_mobs.npcs


func advance(delta: float) -> void:
	clock_ms += maxf(0.0, delta) * 1000.0
	fixed_mobs.update([x, y], int(clock_ms))


func character_snapshot() -> Array:
	return fixed_mobs.snapshot(int(clock_ms))


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
