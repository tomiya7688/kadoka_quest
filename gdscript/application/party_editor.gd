# {
#   責務: [party_editor: Own the draft; validate a fresh roster and save only current_party with a digest guard.]
#   フィールド: [
#     persistence: persistence（RefCounted）
#     selection: 選択状態
#     baseline: baseline（Dictionary）
#     digest: digest
#     records: 個体レコード一覧（Dictionary）
#     warnings: warnings（Array）
#   ]
# }
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


# {
#   責務: [_init: パーティ・editorが利用する初期状態と依存を設定する]
#   処理: [1: パーティ・editorが利用する初期状態と依存を設定する]
#   引数: [field_persistence: フィールド・persistence（RefCounted）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(field_persistence: RefCounted) -> void:
	persistence = field_persistence


# {
#   責務: [begin: パーティ・editorを開始する]
#   処理: [1: パーティ・editorを開始する]
#   引数: []
#   戻り値: [result: パーティ・editorを開始するための結果（Dictionary）]
# }
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


# {
#   責務: [assign: パーティ・editorのassignを求める]
#   処理: [1: パーティ・editorのassignを求める]
#   引数: [
#     slot: 編成枠（int）
#     id: 識別子（Variant）
#   ]
#   戻り値: [result: パーティ・editorのassignを求めるための結果（Dictionary）]
# }
func assign(slot: int, id: Variant) -> Dictionary:
	return selection.assign(slot, id, records)


# {
#   責務: [member_ids: パーティ・editorの個体・識別子一覧を求める]
#   処理: [1: パーティ・editorの個体・識別子一覧を求める]
#   引数: []
#   戻り値: [result: パーティ・editorの個体・識別子一覧を求めるための結果（Array）]
# }
func member_ids() -> Array:
	return selection.members.duplicate(true)


# {
#   責務: [replace_members: パーティ・editorのreplace・個体一覧を求める]
#   処理: [1: パーティ・editorのreplace・個体一覧を求める]
#   引数: [
#     members: 個体一覧（Array）
#     available: available（Dictionary）
#     notes: notes（Array）
#   ]
#   戻り値: [result: パーティ・editorのreplace・個体一覧を求めるための結果（Dictionary）]
# }
func replace_members(members: Array, available: Dictionary, notes: Array) -> Dictionary:
	var result: Dictionary = selection.replace_members(members, available)
	if result["ok"]:
		records = available
		warnings = notes
	return result


# {
#   責務: [snapshot: パーティ・editorを状態を複製する]
#   処理: [1: パーティ・editorを状態を複製する]
#   引数: []
#   戻り値: [result: パーティ・editorを状態を複製するための結果（Dictionary）]
# }
func snapshot() -> Dictionary:
	return {"records": records, "party": RecordContract.party_entries({"current_party": selection.members}, records),
		"dirty": selection.is_dirty(), "warnings": warnings}


# {
#   責務: [save: パーティ・editorを保存する]
#   処理: [1: パーティ・editorを保存する]
#   引数: []
#   戻り値: [result: パーティ・editorを保存するための結果（Dictionary）]
# }
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
