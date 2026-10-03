extends SceneTree
## Real production controls/input, plus isolated-fixture changes and pure draft contracts.

const Selection = preload("res://engine/party_selection.gd")
const Documents = preload("res://data/json_documents.gd")
const PresetContract = preload("res://engine/party_preset_contract.gd")
const PresetStore = preload("res://data/party_preset_store.gd")
const KEYS := {"F5": KEY_F5, "F6": KEY_F6, "F9": KEY_F9, "ESC": KEY_ESCAPE,
	"UP": KEY_UP, "DOWN": KEY_DOWN, "LEFT": KEY_LEFT, "RIGHT": KEY_RIGHT, "TAB": KEY_TAB,
	"HOME": KEY_HOME, "END": KEY_END, "PAGEUP": KEY_PAGEUP, "PAGEDOWN": KEY_PAGEDOWN,
	"E": KEY_E, "S": KEY_S, "P": KEY_P, "A": KEY_A, "BACKSPACE": KEY_BACKSPACE,
	"DELETE": KEY_DELETE, "ENTER": KEY_ENTER, "SPACE": KEY_SPACE}


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
		match action["kind"]:
			"key":
				await _press(scene, action)
			"key_down", "key_up":
				await _set_key(action, action["kind"] == "key_down")
				scene._process(0.01 if action["kind"] == "key_down" else 0.0)
			"tick":
				scene._process(float(action.get("seconds", 0.14)))
			"click":
				await _click(scene, action)
			"text":
				await _type_text(action["text"])
			"load_preset":
				scene.load_party_preset(action["filename"])
			"preset_raw":
				var profile: Dictionary = scene.persistence.store.resolve_profile(scene.profile_name)
				var path: String = profile["path"].path_join("parties").path_join(action["filename"])
				var file := FileAccess.open(path, FileAccess.WRITE)
				file.store_string(action["raw"])
				file.close()
			"external_state":
				var profile: Dictionary = scene.persistence.store.resolve_profile(scene.profile_name)
				var path: String = profile["path"].path_join("state.json")
				if action.has("raw"):
					var file := FileAccess.open(path, FileAccess.WRITE)
					file.store_string(action["raw"])
					file.close()
				else:
					var state: Dictionary = Documents.read_object(path)["value"]
					state.merge(action["changes"], true)
					Documents.write_atomic(path, state)
			"remove_ai":
				var profile: Dictionary = scene.persistence.store.resolve_profile(scene.profile_name)
				DirAccess.remove_absolute(profile["path"].path_join("monsters").path_join(action["id"]).path_join("ai.json"))
		await process_frame
		await process_frame
		observations.append(_snapshot(scene))
	var contracts: Array = []
	for case: Dictionary in request.get("cases", []):
		var draft = Selection.new()
		var result: Dictionary = draft.start(case.get("members"))
		var started := bool(result["ok"])
		if started:
			for assignment: Dictionary in case.get("assignments", []):
				result = draft.assign(int(assignment["slot"]), assignment.get("id"), case.get("records", {}))
		contracts.append({"start_ok": started, "result": result, "members": draft.members,
			"valid": draft.validate(case.get("records", {})) if started else {}, "dirty": draft.is_dirty()})
	var presets: Array = []
	for case: Dictionary in request.get("preset_cases", []):
		presets.append({"valid": PresetContract.validate(case.get("document", {})),
			"project": PresetContract.project(case.get("document", {}), case.get("records", {})),
			"stem": PresetContract.filename_stem(case.get("name", "")),
			"safe": PresetStore.safe_filename(case.get("filename", "party.json"))})
	print("KADOKA_PARTY_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({
		"observations": observations, "cases": contracts, "preset_cases": presets})))
	quit(0)


func _press(scene: Control, action: Dictionary) -> void:
	await _set_key(action, true)
	scene._process(0.01)
	await _set_key(action, false)
	scene._process(0.0)  # A real release frame clears held movement without advancing time.


func _set_key(action: Dictionary, pressed: bool) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = KEYS[action["key"]]
	event.keycode = event.physical_keycode
	event.ctrl_pressed = action.get("ctrl", false)
	event.shift_pressed = action.get("shift", false)
	event.pressed = pressed
	Input.parse_input_event(event.duplicate())
	Input.flush_buffered_events()
	await process_frame


func _click(scene: Control, action: Dictionary) -> void:
	var control: Control
	var local: Vector2
	match action["target"]:
		"edit": control = scene.roster_view.edit_button
		"slots": control = scene.party_view.slots
		"owned": control = scene.party_view.owned
		"presets": control = scene.party_view.presets_button
		"preset_list": control = scene.preset_view.listing
		"preset_name": control = scene.preset_view.name_input
		"preset_save", "preset_load", "preset_refresh", "preset_back":
			control = scene.preset_view.buttons[action["target"].trim_prefix("preset_")]
		_: control = scene.party_view.buttons[action["target"]]
	if control is ItemList:
		local = control.get_item_rect(int(action.get("index", 0))).get_center()
	else:
		local = control.size / 2
	var point := root.get_final_transform() * (control.global_position + local)
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



func _type_text(value: String) -> void:
	# Unicode key input enters the real LineEdit; this is not a direct text-property assignment.
	for index in value.length():
		var event := InputEventKey.new()
		event.unicode = value.unicode_at(index)
		event.pressed = true
		Input.parse_input_event(event.duplicate())
		Input.flush_buffered_events()
		await process_frame
		event.pressed = false
		Input.parse_input_event(event.duplicate())
		Input.flush_buffered_events()
	await process_frame


func _snapshot(scene: Control) -> Dictionary:
	var focus := root.gui_get_focus_owner()
	var state: Dictionary = scene.persistence.store.load_profile(scene.profile_name)
	var texts: Array = []
	for index in scene.party_view.slots.item_count:
		texts.append(scene.party_view.slots.get_item_text(index))
	return {"editing": scene.party_view.visible, "roster_visible": scene.roster_view.visible,
		"map_id": scene.session.world.get("id", ""), "direction": scene.session.direction,
		"roster_text": scene.roster_view.body.text, "owned_ids": Array(scene.owned_snapshot.get("records", {}).keys()),
		"preset_visible": scene.preset_view.visible, "preset_message": scene.preset_view.message.text,
		"preset_name": scene.preset_view.name_input.text, "preset_count": scene.preset_view.listing.item_count,
		"preset_selection": Array(scene.preset_view.listing.get_selected_items()),
		"preset_scroll": scene.preset_view.listing.get_v_scroll_bar().value,
		"draft": scene.party_editor.snapshot() if scene.party_editor != null else {},
		"message": scene.party_view.message.text, "status": scene.status.text,
		"state": state.get("value"), "focus": str(focus.get_path()) if focus != null else "",
		"x": scene.session.x, "y": scene.session.y, "slots": texts,
		"slot_selection": Array(scene.party_view.slots.get_selected_items()),
		"owned_selection": Array(scene.party_view.owned.get_selected_items()),
		"owned_scroll": scene.party_view.owned.get_v_scroll_bar().value,
		"panel_rect": str(scene.party_view.get_global_rect())}
