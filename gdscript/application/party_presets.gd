extends RefCounted
## Validate catalog/new drafts and coordinate preset-only I/O; no implicit state save.

const Contract = preload("res://engine/party_preset_contract.gd")
const Store = preload("res://data/party_preset_store.gd")
const Selection = preload("res://engine/party_selection.gd")
var persistence: RefCounted


func _init(field_persistence: RefCounted) -> void:
	persistence = field_persistence


func _profile() -> Dictionary:
	var state: Dictionary = persistence.load_position()
	if not state["ok"]:
		return state
	return persistence.store.resolve_profile(persistence.profile_name)


func read_catalog() -> Dictionary:
	var profile := _profile()
	if not profile["ok"]:
		return profile
	var scanned: Dictionary = Store.new(profile["path"]).scan_documents()
	if not scanned["ok"]:
		return scanned
	var entries: Array = []
	var warnings: Array = scanned["warnings"]
	for entry: Dictionary in scanned["entries"]:
		var valid := Contract.validate(entry["value"])
		if not valid["ok"]:
			warnings.append(entry["filename"] + ": " + str(valid["message"]))
			continue
		entries.append({"filename": entry["filename"], "name": entry["value"]["name"], "members": entry["value"]["members"]})
	return {"ok": true, "entries": entries, "warnings": warnings}


func save_new(name: String, members: Array) -> Dictionary:
	var profile := _profile()
	if not profile["ok"]:
		return profile
	var roster: Dictionary = persistence.read_owned_roster()
	if not roster["ok"]:
		return roster
	var draft = Selection.new()
	var valid: Dictionary = draft.start(members)
	if not valid["ok"]:
		return valid
	valid = draft.validate(roster["records"])
	if not valid["ok"]:
		return valid
	var document := Contract.create(name, members)
	if not document["ok"]:
		return document
	return Store.new(profile["path"]).create_new(Contract.filename_stem(document["value"]["name"]), document["value"])


func load_draft(filename: String, editor: RefCounted) -> Dictionary:
	var profile := _profile()
	if not profile["ok"]:
		return profile
	var loaded: Dictionary = Store.new(profile["path"]).read_document(filename)
	if not loaded["ok"]:
		return loaded
	var roster: Dictionary = persistence.read_owned_roster()
	if not roster["ok"]:
		return roster
	var projected := Contract.project(loaded["value"], roster["records"])
	if not projected["ok"]:
		return projected
	var result: Dictionary = editor.replace_members(projected["members"], roster["records"], roster["warnings"])
	if result["ok"]:
		result["warnings"] = projected["warnings"]
	return result
