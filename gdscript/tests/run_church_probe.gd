extends SceneTree
## Developer-only checkpoint contract and real Scene probes on private copies.
const Contract = preload("res://engine/revive_point_contract.gd")
const Documents = preload("res://data/json_documents.gd")
const KEYS := {"Enter": KEY_ENTER, "Space": KEY_SPACE, "E": KEY_E, "Escape": KEY_ESCAPE,
	"F5": KEY_F5, "F6": KEY_F6, "F9": KEY_F9, "P": KEY_P}


class FaultStore extends "res://data/field_save_store.gd":
	var mode: String

	func _init(path: String, fault: String) -> void:
		super(path)
		mode = fault

	func save_profile(name: String, state: Dictionary, digest: String, inventory: Dictionary) -> Dictionary:
		if mode == "false_success":
			return {"ok": true}
		if mode == "before_write":
			_change(name)
		var result: Dictionary = super.save_profile(name, state, digest, inventory)
		if result["ok"] and mode == "after_write":
			_change(name)
		return result

	func _change(name: String) -> void:
		var state: Dictionary = load_profile(name)["value"]
		state["external_update"] = "kept"
		Documents.write_atomic(resolve_profile(name)["path"].path_join("state.json"), state)


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var request: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	var result: Array = []
	if request.has("cases"):
		for case: Dictionary in request["cases"]:
			var valid := Contract.validate_point(case.get("point"))
			if valid["ok"]:
				valid["plan"] = Contract.plan(case["state"], valid["point"])
			result.append({"result": valid, "input": case})
	else:
		result = await _scene(request)
	print("KADOKA_CHURCH=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit()


func _scene(request: Dictionary) -> Array:
	root.size = Vector2i(960, 540)
	var scene = load("res://scenes/field.tscn").instantiate()
	root.add_child(scene)
	scene.set_process(false)
	await process_frame
	var observations: Array = [_snapshot(scene)]
	var pending: Dictionary = {}
	for action: Dictionary in request["actions"]:
		var outcome: Variant = null
		match action["kind"]:
			"open": outcome = scene.open_map(action.get("map_id", "starting_town"), action.get("entry", {"x": 18, "y": 10, "direction": "back"}))
			"key": await _key(action)
			"register": outcome = scene.register_church(action.get("revive"))
			"begin": pending = scene.church_registration.begin(action.get("revive"))
			"commit": outcome = scene.church_registration.commit(pending)
			"fault": scene.persistence.store = FaultStore.new(scene.persistence.store.root, action["mode"])
			"change_state":
				var profile: Dictionary = scene.persistence.store.resolve_profile(scene.profile_name)
				var state: Dictionary = scene.persistence.store.load_profile(scene.profile_name)["value"]
				state.merge(action["changes"], true)
				Documents.write_atomic(profile["path"].path_join("state.json"), state)
			"password": scene.open_password_input()
			"roster": scene.open_owned_roster()
			"party": scene.begin_party_edit()
			"presets": scene.open_party_presets()
			"tick": scene._process(float(action["delta"]))
		await process_frame
		var observation := _snapshot(scene)
		observation["outcome"] = outcome
		observations.append(observation)
	return observations


func _snapshot(scene: Control) -> Dictionary:
	var state: Dictionary = scene.persistence.store.load_profile(scene.profile_name)
	return {"map_id": scene.session.world.get("id"), "player": [scene.session.x, scene.session.y, scene.session.direction],
		"npcs": scene.session.character_snapshot(), "clock": scene.session.clock_ms, "status": scene.status.text,
		"result": scene.church_result.duplicate(true), "state": state.get("value", {}),
		"password": scene.password_session.active, "roster": scene.roster_view.visible,
		"party": scene.party_view.visible, "presets": scene.preset_view.visible}


func _key(action: Dictionary) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = KEYS[action["key"]]
	event.keycode = event.physical_keycode
	event.echo = action.get("echo", false)
	event.pressed = true
	Input.parse_input_event(event.duplicate())
	Input.flush_buffered_events()
	await process_frame
	event.pressed = false
	event.echo = false
	Input.parse_input_event(event.duplicate())
	Input.flush_buffered_events()
	await process_frame
