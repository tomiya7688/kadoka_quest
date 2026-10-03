extends SceneTree
## Real production controls/input, plus isolated-fixture changes and pure draft contracts.

const Selection = preload("res://engine/party_selection.gd")
const Documents = preload("res://data/json_documents.gd")
const KEYS := {"F5": KEY_F5, "F6": KEY_F6, "F9": KEY_F9, "ESC": KEY_ESCAPE,
	"UP": KEY_UP, "DOWN": KEY_DOWN, "LEFT": KEY_LEFT, "RIGHT": KEY_RIGHT, "TAB": KEY_TAB,
	"HOME": KEY_HOME, "END": KEY_END, "PAGEUP": KEY_PAGEUP, "PAGEDOWN": KEY_PAGEDOWN,
	"E": KEY_E, "S": KEY_S, "DELETE": KEY_DELETE, "ENTER": KEY_ENTER, "SPACE": KEY_SPACE}


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
			"click":
				await _click(scene, action)
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
	print("KADOKA_PARTY_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({"observations": observations, "cases": contracts})))
	quit(0)


func _press(scene: Control, action: Dictionary) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = KEYS[action["key"]]
	event.keycode = event.physical_keycode
	event.ctrl_pressed = action.get("ctrl", false)
	event.shift_pressed = action.get("shift", false)
	event.pressed = true
	Input.parse_input_event(event.duplicate())
	Input.flush_buffered_events()
	await process_frame
	scene._process(0.01)
	event.pressed = false
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


func _snapshot(scene: Control) -> Dictionary:
	var focus := root.gui_get_focus_owner()
	var state: Dictionary = scene.persistence.store.load_profile(scene.profile_name)
	var texts: Array = []
	for index in scene.party_view.slots.item_count:
		texts.append(scene.party_view.slots.get_item_text(index))
	return {"editing": scene.party_view.visible, "roster_visible": scene.roster_view.visible,
		"draft": scene.party_editor.snapshot() if scene.party_editor != null else {},
		"message": scene.party_view.message.text, "status": scene.status.text,
		"state": state.get("value"), "focus": str(focus.get_path()) if focus != null else "",
		"x": scene.session.x, "y": scene.session.y, "slots": texts,
		"slot_selection": Array(scene.party_view.slots.get_selected_items()),
		"owned_selection": Array(scene.party_view.owned.get_selected_items()),
		"owned_scroll": scene.party_view.owned.get_v_scroll_bar().value,
		"panel_rect": str(scene.party_view.get_global_rect())}
