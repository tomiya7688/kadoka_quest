extends RefCounted
## Own the draft; validate a fresh roster and save only current_party with a digest guard.

const Selection = preload("res://engine/party_selection.gd")
const RecordContract = preload("res://engine/monster_record_contract.gd")
var persistence: RefCounted
var selection = Selection.new()
var baseline: Dictionary = {}
var digest := ""
var records: Dictionary = {}
var warnings: Array = []


func _init(field_persistence: RefCounted) -> void:
	persistence = field_persistence


func begin() -> Dictionary:
	var loaded: Dictionary = persistence.load_position()
	if not loaded["ok"]:
		return loaded
	var roster: Dictionary = persistence.roster.read_snapshot(loaded["value"])
	if not roster["ok"]:
		return roster
	var started: Dictionary = selection.start(loaded["value"].get("current_party", []))
	if not started["ok"]:
		return started
	baseline = loaded["value"].duplicate(true)
	digest = loaded["digest"]
	records = roster["records"]
	warnings = roster["warnings"]
	return {"ok": true}


func assign(slot: int, id: Variant) -> Dictionary:
	return selection.assign(slot, id, records)


func member_ids() -> Array:
	return selection.members.duplicate(true)


func replace_members(members: Array, available: Dictionary, notes: Array) -> Dictionary:
	var result: Dictionary = selection.replace_members(members, available)
	if result["ok"]:
		records = available
		warnings = notes
	return result


func snapshot() -> Dictionary:
	return {"records": records, "party": RecordContract.party_entries({"current_party": selection.members}, records),
		"dirty": selection.is_dirty(), "warnings": warnings}


func save() -> Dictionary:
	if baseline.is_empty():
		return {"ok": false, "message": "編成を開き直してください。"}
	var latest: Dictionary = persistence.load_position()
	if not latest["ok"]:
		return latest
	if latest["digest"] != digest:
		return {"ok": false, "error": "changed", "message": "セーブが外部で変更されました。キャンセルして編成を開き直してください。"}
	var roster: Dictionary = persistence.roster.read_snapshot(latest["value"])
	if not roster["ok"]:
		return roster
	var valid: Dictionary = selection.validate(roster["records"])
	if not valid["ok"]:
		return valid
	if not selection.is_dirty():
		return {"ok": true, "message": "編成に変更はありません。"}
	var state := baseline.duplicate(true)
	state["current_party"] = selection.members.duplicate(true)
	var result: Dictionary = persistence.store.save_profile(persistence.profile_name, state, digest, {})
	if result["ok"]:
		result["message"] = "パーティ編成を保存しました。"
	return result
