extends RefCounted
## Read-only reconstruction -> plain, full-resource battle snapshot; never a saved record update.

const Records = preload("res://engine/monster_record_contract.gd")
const Reconstruction = preload("res://application/monster_reconstruction.gd")
const State = preload("res://engine/combatant_state.gd")
const ACTIVE_TEAM_LIMIT := 4
var reconstruction: RefCounted


func _init(repository: RefCounted) -> void:
	reconstruction = Reconstruction.new(repository)


func build(record: Variant) -> Dictionary:
	if not record is Dictionary or not record.get("monster") is Dictionary or not record.get("ai") is Dictionary:
		return {"ok": false, "reason": "invalid_record"}
	var monster: Dictionary = record["monster"]
	var checked := Records.validate_record(monster, record["ai"], str(monster.get("id", "")))
	if not checked["ok"]:
		return {"ok": false, "reason": "invalid_record", "detail": checked}
	var rebuilt: Dictionary = reconstruction.rebuild(monster)
	if not rebuilt["ok"]:
		return {"ok": false, "reason": "reconstruction_failed", "detail": rebuilt.duplicate(true)}
	var modified: Dictionary = rebuilt["modifiers"]
	if not modified["ok"]:
		return {"ok": false, "reason": "modifiers_failed", "detail": modified.duplicate(true)}
	var state = State.new()
	var initialized: Dictionary = state.start(monster, modified["stats"])
	if not initialized["ok"]:
		return initialized
	return {"ok": true, "snapshot": state.snapshot(), "warnings": modified["warnings"].duplicate(true),
		"equipment": modified["equipment"].duplicate(true), "scope": "combatant_resources_only"}


func build_team(records: Variant) -> Dictionary:
	if not records is Array:
		return {"ok": false, "reason": "invalid_team"}
	if records.size() > ACTIVE_TEAM_LIMIT:
		return {"ok": false, "reason": "active_team_limit", "limit": ACTIVE_TEAM_LIMIT}
	var members: Array = []
	var ids: Dictionary = {}
	for index in records.size():
		var built := build(records[index])
		if not built["ok"]:
			built["index"] = index
			return built
		var id: String = built["snapshot"]["identity"]["id"]
		if ids.has(id):
			return {"ok": false, "reason": "duplicate_member", "index": index}
		ids[id] = true
		members.append(built)
	return {"ok": true, "members": members}
