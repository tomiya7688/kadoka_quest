extends SceneTree
## Test/developer-only runner: explicit clocks/RNG and production Scene integration.

const Rules = preload("res://engine/field_engine.gd")
const Controller = preload("res://engine/fixed_mob_controller.gd")

class TapeRandom extends RefCounted:
	var rolls: Array = [0]
	var roll_index := 0
	var shuffle_index := 0

	func _init(values: Array) -> void:
		if not values.is_empty():
			rolls = values

	func randrange(limit: int) -> int:
		var value := int(rolls[roll_index % rolls.size()]) % limit
		roll_index += 1
		return value

	func shuffle(values: Array) -> void:
		var original := values.duplicate()
		for index in values.size():
			values[index] = original[(index + shuffle_index) % values.size()]
		shuffle_index += 1


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var request: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var result: Variant
	if request.get("scene", false):
		result = await _scene(request)
	elif request.get("performance", false):
		result = _performance(request)
	else:
		result = []
		for case: Dictionary in request["cases"]:
			result.append(_engine(case))
	print("KADOKA_FIXED_MOBS=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)


func _engine(request: Dictionary) -> Array:
	var rules = Rules.new()
	var rng = TapeRandom.new(request.get("rolls", [0]))
	var controller = Controller.new(rules, rng, int(request.get("duration", 180)))
	var player: Array = request["player"]
	var now := int(request.get("now", 0))
	var world: Dictionary = request["world"]
	var original := JSON.stringify(world)
	controller.reset(world, request["blocks"], request.get("despawned", []), player, now)
	var result: Array = [_observation(controller, now, false)]
	for action: Dictionary in request["actions"]:
		now = int(action.get("now", now))
		player = action.get("player", player)
		var moved := false
		if action.get("kind", "update") == "reset":
			controller.reset(world, request["blocks"], request.get("despawned", []), player, now)
		elif action.get("kind", "update") == "update":
			moved = controller.update(player, now)
		var item := _observation(controller, now, moved)
		item["source_unchanged"] = original == JSON.stringify(world)
		item["rolls_used"] = rng.roll_index
		item["shuffles_used"] = rng.shuffle_index
		result.append(item)
	return result


func _observation(controller: RefCounted, now: int, moved: bool) -> Dictionary:
	return {"npcs": controller.snapshot(now), "moved": moved, "warnings": controller.warnings.duplicate()}


func _scene(request: Dictionary) -> Array:
	var scene = load("res://scenes/field.tscn").instantiate()
	scene.set_process(false)
	root.add_child(scene)
	scene.set_process(false)  # Entering the tree enables script processing automatically.
	await process_frame
	scene.session.fixed_mobs.rng = TapeRandom.new(request.get("rolls", [0]))
	var result: Array = []
	for action: Dictionary in request["actions"]:
		var outcome: Variant = null
		match action["kind"]:
			"open":
				outcome = scene.open_map(action.get("map_id", "ghost_home"), action.get("entry", {}))
			"tick":
				scene._process(float(action["delta"]))
			"modal":
				scene.roster_view.visible = action["name"] == "roster"
				scene.party_view.visible = action["name"] == "party"
				scene.preset_view.visible = action["name"] == "preset"
			"save":
				outcome = scene.save_current_position()
			"load":
				outcome = scene.load_saved_position()
			"move":
				outcome = scene.session.move_player(int(action["dx"]), int(action["dy"]))
			"place":
				scene.session.x = int(action["x"])
				scene.session.y = int(action["y"])
			"refresh":
				scene._refresh_view()
		await process_frame  # Exercise actual renderer without advancing the field clock.
		result.append({"clock": scene.session.clock_ms, "npcs": scene.session.character_snapshot(),
			"player": [scene.session.x, scene.session.y], "outcome": outcome,
			"drawn": scene.view.model.get("characters", []).duplicate(true), "status": scene.status.text})
	return result


func _performance(request: Dictionary) -> Dictionary:
	var world: Dictionary = request["world"]
	var controller = Controller.new(Rules.new(), TapeRandom.new([0]))
	controller.reset(world, request["blocks"], [], request["player"], 0)
	var now := 0
	for index in int(request["warmup"]):
		now += 100
		controller.update(request["player"], now)
		controller.snapshot(now)
	var samples: Array = []
	for sample in int(request["samples"]):
		var started := Time.get_ticks_usec()
		for index in int(request["iterations"]):
			now += 100
			controller.update(request["player"], now)
			controller.snapshot(now)
		samples.append(float(Time.get_ticks_usec() - started) / int(request["iterations"]))
	samples.sort()
	return {"microseconds": samples[samples.size() / 2], "actors": controller.npcs.size(),
		"iterations": request["iterations"], "samples": request["samples"], "warmup": request["warmup"]}
