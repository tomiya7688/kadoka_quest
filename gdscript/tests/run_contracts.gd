extends SceneTree
## One real-engine invocation for plain-data parity with the Python reference.

const Rules = preload("res://engine/field_engine.gd")
const Repository = preload("res://data/content_repository.gd")
const Session = preload("res://application/field_session.gd")
const Keyboard = preload("res://ui/field_input.gd")


func _initialize() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		quit(2)
		return
	var payload: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	var results: Array = []
	for case: Dictionary in payload["cases"]:
		results.append(_evaluate(case))
	var repository = Repository.new(payload["root"])
	var blocks: Dictionary = repository.load_blocks()
	var maps := {}
	for map_id in payload["map_ids"]:
		maps[map_id] = repository.load_map(map_id)
	var invalid_ids: Array = []
	for map_id in ["../starting_town", "", "/absolute", "town\\other"]:
		invalid_ids.append({"value": repository.load_map(map_id), "error": repository.last_error})
	var session = Session.new()
	session.enter_map(maps["starting_town"], blocks, {"x": 34, "y": 14})
	var edge: Dictionary = session.move_player(1, 0)
	session.enter_map(maps["fresh_forest"], blocks, {"x": 22, "y": 26})
	var rock: Dictionary = session.move_player(0, 1)
	var rock_interaction: Dictionary = session.interaction_event()
	session.enter_map(maps["ghost_home"], blocks, {"x": 9, "y": 7})
	var mob: Dictionary = session.move_player(1, 0)
	var keyboard = Keyboard.new()
	var key := InputEventKey.new()
	key.physical_keycode = KEY_RIGHT
	key.pressed = true
	Input.parse_input_event(key.duplicate())
	Input.flush_buffered_events()
	var repeats: Array = []
	for delta in [0.0, 0.1, 0.041]:
		var step: Vector2i = keyboard.movement_step(delta)
		repeats.append([step.x, step.y])
	key.pressed = false
	Input.parse_input_event(key.duplicate())
	Input.flush_buffered_events()
	var released: Vector2i = keyboard.movement_step(1.0)
	repeats.append([released.x, released.y])
	print("KADOKA_CONTRACT_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({
		"results": results, "blocks": blocks, "maps": maps,
		"invalid_ids": invalid_ids, "hero": repository.load_species("hero"),
		"sessions": {"edge": edge, "rock": rock, "rock_interaction": rock_interaction, "mob": mob},
		"repeats": repeats,
	})))
	quit(0)


func _evaluate(case: Dictionary) -> Dictionary:
	var world: Dictionary = case["map"]
	var blocks: Dictionary = case["blocks"]
	var visible: Array = case.get("visible", [])
	var hidden: Array = case.get("hidden", [])
	var before := JSON.stringify([world, blocks, visible, hidden])
	var rules = Rules.new(world, blocks)
	var value: Variant
	var args: Array = case["args"]
	match case["operation"]:
		"move":
			value = rules.resolve_player_move(int(args[0]), int(args[1]), int(args[2]), int(args[3]), str(args[4]), visible, hidden)
		"front":
			value = rules.front_position(int(args[0]), int(args[1]), str(args[2]))
		"transition":
			value = rules.step_transition_at(int(args[0]), int(args[1]))
		"nearby":
			value = rules.nearby_event(int(args[0]), int(args[1]))
		"tile":
			value = rules.tile_allows(int(args[0]), int(args[1]), str(args[2]))
		"path":
			value = rules.has_clear_axis_path(args[0], args[1], str(args[2]))
	return {"value": value, "mutated": before != JSON.stringify([world, blocks, visible, hidden])}
