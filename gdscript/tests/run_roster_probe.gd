extends SceneTree
## Production Scene/input plus pure-contract results, all under test-owned roots.

const Contract = preload("res://engine/monster_record_contract.gd")
const MonsterStore = preload("res://data/monster_store.gd")
const KEYS := {"F5": KEY_F5, "F6": KEY_F6, "F9": KEY_F9, "ESC": KEY_ESCAPE,
	"UP": KEY_UP, "DOWN": KEY_DOWN, "RIGHT": KEY_RIGHT, "HOME": KEY_HOME, "END": KEY_END,
	"PAGEUP": KEY_PAGEUP, "PAGEDOWN": KEY_PAGEDOWN}


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var request: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	var scene = load("res://scenes/field.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	scene.set_process(false)
	var observations: Array = [_snapshot(scene)]
	for action: Dictionary in request.get("actions", []):
		var outcome: Variant = null
		match action["kind"]:
			"key":
				await _press(scene, KEYS[action["key"]])
			"wheel":
				# Headless Window can be 64px: Input expects physical, not stretched game coordinates.
				var physical := root.get_final_transform() * Vector2(150, 250)
				root.notify_mouse_entered()
				var motion := InputEventMouseMotion.new()
				motion.position = physical
				motion.global_position = motion.position
				Input.parse_input_event(motion)
				Input.flush_buffered_events()
				await process_frame
				var wheel := InputEventMouseButton.new()
				wheel.position = physical
				wheel.global_position = wheel.position
				wheel.button_index = MOUSE_BUTTON_WHEEL_DOWN
				wheel.pressed = true
				Input.parse_input_event(wheel.duplicate())
				Input.flush_buffered_events()
				await process_frame
				wheel.pressed = false
				Input.parse_input_event(wheel.duplicate())
				Input.flush_buffered_events()
			"save":
				outcome = scene.save_current_position()
			"load":
				outcome = scene.load_saved_position()
			"open":
				outcome = scene.open_map(action["map_id"], action.get("entry", {}))
			"create":
				var profile: Dictionary = scene.persistence.store.resolve_profile(scene.profile_name)
				var species: Dictionary = scene.repository.load_species("slime")
				outcome = MonsterStore.new(profile["path"]).create_new(Contract.create_record(action["id"], species))
		await process_frame
		await process_frame
		var observation := _snapshot(scene)
		observation["outcome"] = outcome
		observations.append(observation)
	var defaults: Array = []
	for parameters: Dictionary in request.get("defaults", []):
		defaults.append(Contract.default_ai(parameters["profile"], parameters["tactic"]))
	var records: Array = []
	for parameters: Dictionary in request.get("records", []):
		records.append(Contract.create_record(parameters["id"], scene.repository.load_species(parameters["species_id"]),
			parameters.get("name", ""), int(parameters["level"])))
	print("KADOKA_ROSTER_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({
		"observations": observations, "defaults": defaults, "records": records,
	})))
	quit(0)


func _press(scene: Control, code: int) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = code
	event.pressed = true
	Input.parse_input_event(event.duplicate())
	Input.flush_buffered_events()
	await process_frame
	scene._process(0.01)  # The production movement update; modal UI must prevent it.
	event.pressed = false
	Input.parse_input_event(event.duplicate())
	Input.flush_buffered_events()
	await process_frame


func _snapshot(scene: Control) -> Dictionary:
	return {
		"map_id": scene.session.world.get("id", ""), "x": scene.session.x, "y": scene.session.y,
		"status": scene.status.text, "owned": scene.owned_snapshot,
		"visible": scene.roster_view.visible, "text": scene.roster_view.body.text,
		"scroll": scene.roster_view.scrolling.scroll_vertical,
		"scroll_max": scene.roster_view.scrolling.get_v_scroll_bar().max_value,
		"panel_rect": str(scene.roster_view.get_global_rect()),
		"scroll_rect": str(scene.roster_view.scrolling.get_global_rect()),
		"viewport_size": str(root.size), "mouse_position": str(root.get_mouse_position()),
	}
