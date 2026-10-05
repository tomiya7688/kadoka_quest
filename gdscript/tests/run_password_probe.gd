extends SceneTree
## Developer-only pure operation parity and production Scene input/modal probes.
const Password = preload("res://engine/password_session.gd")
const KEYS := {"Enter": KEY_ENTER, "KPEnter": KEY_KP_ENTER, "Escape": KEY_ESCAPE, "Backspace": KEY_BACKSPACE,
	"F5": KEY_F5, "F9": KEY_F9, "F6": KEY_F6, "Tab": KEY_TAB, "Space": KEY_SPACE,
	"Left": KEY_LEFT, "Right": KEY_RIGHT, "E": KEY_E}
const Documents = preload("res://data/json_documents.gd")


class FaultStore extends "res://data/monster_store.gd":
	var mode: String
	var profile: String
	var calls := 0

	func _init(path: String, fault: String) -> void:
		super(path)
		profile = path
		mode = fault

	func create_new(record: Dictionary) -> Dictionary:
		calls += 1
		if mode == "fail_second" and calls == 2:
			return {"ok": false, "error": "write_failed", "message": "test-only second-publication failure"}
		var result: Dictionary = super.create_new(record)
		if result["ok"] and mode == "external_state" and calls == 1:
			var state: Dictionary = Documents.read_object(profile.path_join("state.json"))["value"]
			state["external_update"] = "kept"
			Documents.write_atomic(profile.path_join("state.json"), state)
		return result


class FaultService extends "res://application/ghost_acquisition.gd":
	var mode: String

	func _init(field: RefCounted, fault: String) -> void:
		super(field)
		mode = fault

	func _monster_store(path: String) -> RefCounted:
		return FaultStore.new(path, mode)


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var request: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	var result: Variant
	if request.get("scene", false):
		result = await _scene(request)
	else:
		result = _cases(request)
	print("KADOKA_PASSWORD=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit()


func _cases(request: Dictionary) -> Array:
	var result: Array = []
	for case: Dictionary in request["cases"]:
		var session = Password.new(case.get("secret", Password.PASSWORD), case.get("keys", Password.KANA_KEYS))
		var observations: Array = [{"state": session.snapshot(), "result": null}]
		for operation: Dictionary in case["operations"]:
			var outcome: Variant = null
			match operation["kind"]:
				"open": session.open()
				"append": outcome = session.append(operation["value"])
				"backspace": outcome = session.backspace()
				"submit": outcome = session.submit()
				"cancel": session.cancel()
			observations.append({"state": session.snapshot(), "result": outcome})
		result.append(observations)
	return result


func _scene(request: Dictionary) -> Array:
	root.size = Vector2i(960, 540)  # Headless OS window defaults to 64x64, not the game's viewport.
	var scene = load("res://scenes/field.tscn").instantiate()
	root.add_child(scene)
	scene.set_process(false)
	var signals: Array = []
	scene.password_finished.connect(func(result: Dictionary): signals.append(result))
	await process_frame
	var observations: Array = []
	for action: Dictionary in request["actions"]:
		var outcome: Variant = null
		match action["kind"]:
			"open": scene.open_map("ghost_home", action.get("entry", {"x": 17, "y": 8, "direction": "back"}))
			"key": await _key(action)
			"type":
				for index in str(action["value"]).length():
					await _key({"unicode": str(action["value"]).unicode_at(index)})
			"click": await _click(scene.password_view.buttons[action["target"]])
			"commit_signal":
				# Adapter-level batch signal, not a real OS IME composition.
				scene.password_view.text_input.text = action["value"]
				scene.password_view.text_input.text_changed.emit(action["value"])
			"focus": scene.password_view.buttons[action["target"]].grab_focus()
			"tick": scene._process(float(action["delta"]))
			"save": outcome = scene.save_current_position()
			"load": outcome = scene.load_saved_position()
			"roster": scene.open_owned_roster()
			"party": scene.begin_party_edit()
			"fault": scene.ghost_acquisition = FaultService.new(scene.persistence, action["mode"])
			"change_state":
				var profile: Dictionary = scene.persistence.store.resolve_profile(scene.profile_name)
				var state: Dictionary = scene.persistence.store.load_profile(scene.profile_name)["value"]
				state.merge(action["changes"], true)
				Documents.write_atomic(profile["path"].path_join("state.json"), state)
		await process_frame
		var slot_texts: Array = []
		for slot: Label in scene.password_view.slots:
			slot_texts.append(slot.text)
		var panel: Rect2 = scene.password_view.get_global_rect()
		var bounds_ok := Rect2(Vector2.ZERO, Vector2(root.size)).encloses(panel)
		for button: Button in scene.password_view.buttons.values():
			bounds_ok = bounds_ok and panel.encloses(button.get_global_rect())
		observations.append({"state": scene.password_session.snapshot(), "visible": scene.password_view.visible,
			"slots": slot_texts, "keys": scene.password_view.buttons.keys(), "clock": scene.session.clock_ms,
			"player": [scene.session.x, scene.session.y], "npcs": scene.session.character_snapshot(),
			"keyboard_elapsed": scene.keyboard.elapsed, "roster": scene.roster_view.visible, "party": scene.party_view.visible,
			"outcome": outcome, "signals": signals.duplicate(true), "result": scene.password_outcome.duplicate(),
			"status": scene.status.text, "message": scene.password_view.message.text,
			"native_text": scene.password_view.text_input.text, "bounds_ok": bounds_ok,
			"panel_rect": str(panel), "window_size": str(root.size),
			"acquisition": scene.acquisition_result.duplicate(true), "owned": scene.owned_snapshot.duplicate(true),
			"roster_text": scene.roster_view.body.text})
	return observations


func _key(action: Dictionary) -> void:
	var key := InputEventKey.new()
	key.physical_keycode = KEYS.get(action.get("key", ""), 0)
	key.keycode = key.physical_keycode  # Native Tab/Space actions need logical codes too.
	key.unicode = int(action.get("unicode", 0))
	key.echo = action.get("echo", false)
	key.pressed = true
	Input.parse_input_event(key.duplicate())
	Input.flush_buffered_events()
	await process_frame
	key.pressed = false
	key.echo = false
	Input.parse_input_event(key.duplicate())
	Input.flush_buffered_events()
	await process_frame


func _click(control: Control) -> void:
	var point := root.get_final_transform() * control.get_global_rect().get_center()
	root.notify_mouse_entered()
	var motion := InputEventMouseMotion.new()
	motion.position = point
	motion.global_position = point
	Input.parse_input_event(motion)
	Input.flush_buffered_events()
	await process_frame
	var button := InputEventMouseButton.new()
	button.position = point
	button.global_position = point
	button.button_index = MOUSE_BUTTON_LEFT
	button.pressed = true
	Input.parse_input_event(button.duplicate())
	Input.flush_buffered_events()
	await process_frame
	button.pressed = false
	Input.parse_input_event(button.duplicate())
	Input.flush_buffered_events()
	await process_frame
