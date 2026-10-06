# {
#   責務: [run_fixed_mobs_probe: Test/developer-only runner: explicit clocks/RNG and production Scene integration.]
#   フィールド: []
# }
extends SceneTree
## Test/developer-only runner: explicit clocks/RNG and production Scene integration.

const Rules = preload("res://engine/field_engine.gd")
const Controller = preload("res://engine/fixed_mob_controller.gd")
const Dialogue = preload("res://engine/dialogue_deck.gd")

# {
#   責務: [TapeRandom: tape・乱数の状態と振る舞いを担当する]
#   フィールド: [
#     rolls: rolls（Array）
#     roll_index: roll・位置番号
#     shuffle_index: 並べ替え・位置番号
#   ]
# }
class TapeRandom extends RefCounted:
	var rolls: Array = [0]
	var roll_index := 0
	var shuffle_index := 0

	# {
	#   責務: [_init: run・fixed・モブ一覧・probeが利用する初期状態と依存を設定する]
	#   処理: [1: run・fixed・モブ一覧・probeが利用する初期状態と依存を設定する]
	#   引数: [values: 値一覧（Array）]
	#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
	# }
	func _init(values: Array) -> void:
		if not values.is_empty():
			rolls = values

	# {
	#   責務: [randrange: run・fixed・モブ一覧・probeのrandrangeを求める]
	#   処理: [1: run・fixed・モブ一覧・probeのrandrangeを求める]
	#   引数: [limit: limit（int）]
	#   戻り値: [result: run・fixed・モブ一覧・probeのrandrangeを求めるための結果（int）]
	# }
	func randrange(limit: int) -> int:
		var value := int(rolls[roll_index % rolls.size()]) % limit
		roll_index += 1
		return value

	# {
	#   責務: [shuffle: run・fixed・モブ一覧・probeの並べ替えを求める]
	#   処理: [1: run・fixed・モブ一覧・probeの並べ替えを求める]
	#   引数: [values: 値一覧（Array）]
	#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
	# }
	func shuffle(values: Array) -> void:
		var original := values.duplicate()
		for index in values.size():
			values[index] = original[(index + shuffle_index) % values.size()]
		shuffle_index += 1


# {
#   責務: [_initialize: run・fixed・モブ一覧・probeのエントリ処理を実行する]
#   処理: [1: run・fixed・モブ一覧・probeのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _initialize() -> void:
	_run.call_deferred()


# {
#   責務: [_run: run・fixed・モブ一覧・probeを実行する]
#   処理: [1: run・fixed・モブ一覧・probeを実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var request: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var result: Variant
	if request.get("scene", false):
		result = await _scene(request)
	elif request.get("performance", false):
		result = _performance(request)
	elif request.get("dialogue", false):
		result = []
		for case: Dictionary in request["cases"]:
			result.append(_dialogue(case))
	else:
		result = []
		for case: Dictionary in request["cases"]:
			result.append(_engine(case))
	print("KADOKA_FIXED_MOBS=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)


# {
#   責務: [_dialogue: run・fixed・モブ一覧・probeの会話を求める]
#   処理: [1: run・fixed・モブ一覧・probeの会話を求める]
#   引数: [request: 要求（Dictionary）]
#   戻り値: [result: run・fixed・モブ一覧・probeの会話を求めるための結果（Dictionary）]
# }
func _dialogue(request: Dictionary) -> Dictionary:
	var original := JSON.stringify(request["source"])
	var state: Dictionary = Dialogue.create(request["source"])
	var rng = TapeRandom.new([0])
	var observations: Array = []
	for index in int(request["count"]):
		var result: Dictionary = Dialogue.next_line(state, rng)
		observations.append({"result": result, "remaining": state.get("remaining", []).duplicate(),
			"last": state.get("last"), "shuffles": rng.shuffle_index})
	return {"selections": observations, "source_unchanged": original == JSON.stringify(request["source"])}


# {
#   責務: [_engine: run・fixed・モブ一覧・probeのルール処理を求める]
#   処理: [1: run・fixed・モブ一覧・probeのルール処理を求める]
#   引数: [request: 要求（Dictionary）]
#   戻り値: [result: run・fixed・モブ一覧・probeのルール処理を求めるための結果（Array）]
# }
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
		var outcome: Dictionary = {}
		if action.get("kind", "update") == "reset":
			controller.reset(world, request["blocks"], request.get("despawned", []), player, now)
		elif action.get("kind", "update") == "update":
			moved = controller.update(player, now)
		elif action["kind"] == "talk":
			outcome = controller.talk(controller.npcs[int(action.get("index", 0))], action.get("direction", "right"))
		var item := _observation(controller, now, moved)
		item["outcome"] = outcome
		item["source_unchanged"] = original == JSON.stringify(world)
		item["rolls_used"] = rng.roll_index
		item["shuffles_used"] = rng.shuffle_index
		result.append(item)
	return result


# {
#   責務: [_observation: run・fixed・モブ一覧・probeのobservationを求める]
#   処理: [1: run・fixed・モブ一覧・probeのobservationを求める]
#   引数: [
#     controller: controller（RefCounted）
#     now: 現在時刻（int）
#     moved: moved（bool）
#   ]
#   戻り値: [result: run・fixed・モブ一覧・probeのobservationを求めるための結果（Dictionary）]
# }
func _observation(controller: RefCounted, now: int, moved: bool) -> Dictionary:
	return {"npcs": controller.snapshot(now), "moved": moved, "warnings": controller.warnings.duplicate()}


# {
#   責務: [_scene: run・fixed・モブ一覧・probeのsceneを求める]
#   処理: [1: run・fixed・モブ一覧・probeのsceneを求める]
#   引数: [request: 要求（Dictionary）]
#   戻り値: [result: run・fixed・モブ一覧・probeのsceneを求めるための結果（Array）]
# }
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
				scene.session.direction = action.get("direction", scene.session.direction)
			"key":
				var key := InputEventKey.new()
				key.physical_keycode = {"Enter": KEY_ENTER, "Space": KEY_SPACE, "E": KEY_E, "F6": KEY_F6}[action["key"]]
				key.pressed = true
				key.echo = action.get("echo", false)
				Input.parse_input_event(key.duplicate())
				Input.flush_buffered_events()
				await process_frame
				key.pressed = false
				key.echo = false
				Input.parse_input_event(key.duplicate())
				Input.flush_buffered_events()
			"refresh":
				scene._refresh_view()
		await process_frame  # Exercise actual renderer without advancing the field clock.
		result.append({"clock": scene.session.clock_ms, "npcs": scene.session.character_snapshot(),
			"player": [scene.session.x, scene.session.y], "outcome": outcome,
			"drawn": scene.view.model.get("characters", []).duplicate(true), "status": scene.status.text})
	return result


# {
#   責務: [_performance: run・fixed・モブ一覧・probeのperformanceを求める]
#   処理: [1: run・fixed・モブ一覧・probeのperformanceを求める]
#   引数: [request: 要求（Dictionary）]
#   戻り値: [result: run・fixed・モブ一覧・probeのperformanceを求めるための結果（Dictionary）]
# }
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
	var movement_us: float = samples[samples.size() / 2]
	var npc: Dictionary = controller.npcs[-1]
	for index in int(request["warmup"]):
		controller.talk(npc, "left")
	samples.clear()
	for sample in int(request["samples"]):
		var started := Time.get_ticks_usec()
		for index in int(request["iterations"]):
			controller.talk(npc, "left")
		samples.append(float(Time.get_ticks_usec() - started) / int(request["iterations"]))
	samples.sort()
	return {"microseconds": movement_us, "dialogue_microseconds": samples[samples.size() / 2],
		"actors": controller.npcs.size(),
		"iterations": request["iterations"], "samples": request["samples"], "warmup": request["warmup"]}
