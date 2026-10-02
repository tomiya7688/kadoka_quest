extends RefCounted
## Validate before applying a load or writing a save. Does not render or move a session.

const Contract = preload("res://engine/field_save_contract.gd")
const Roster = preload("res://application/owned_roster.gd")
var repository: RefCounted
var store: RefCounted
var blocks: Dictionary
var profile_name: String
var roster: RefCounted


func _init(content: RefCounted, saves: RefCounted, definitions: Dictionary, name: String) -> void:
	repository = content
	store = saves
	blocks = definitions
	profile_name = name
	roster = Roster.new(content, saves, name)


func load_position() -> Dictionary:
	var loaded: Dictionary = store.load_profile(profile_name)
	if not loaded["ok"]:
		return loaded
	var state: Dictionary = loaded["value"]
	var valid: Dictionary = Contract.validate_document(state)
	if not valid["ok"]:
		return valid
	var world: Dictionary = repository.load_map(state["map_id"])
	if world.is_empty():
		return {"ok": false, "error": "invalid_map", "message": repository.last_error}
	valid = Contract.validate_location(state, world, blocks)
	if not valid["ok"]:
		return valid
	loaded["world"] = world
	return loaded


func save_position(session: RefCounted) -> Dictionary:
	var previous := load_position()
	if not previous["ok"] and previous["error"] != "not_found":
		return previous
	var base: Dictionary = previous.get("value", Contract.DEFAULT_STATE)
	var snapshot := Contract.capture(base, session.world["id"], session.x, session.y, session.direction)
	var valid := Contract.validate_location(snapshot, session.world, blocks)
	if not valid["ok"]:
		return valid
	if not previous["ok"]:
		var starters: Dictionary = roster.prepare_starters()
		if not starters["ok"]:
			return starters
		snapshot["current_party"] = starters["members"]
	return store.save_profile(profile_name, snapshot, previous.get("digest", ""), Contract.INITIAL_INVENTORY)


func read_owned_roster() -> Dictionary:
	var loaded := load_position()
	if not loaded["ok"]:
		return loaded
	return roster.read_snapshot(loaded["value"])
