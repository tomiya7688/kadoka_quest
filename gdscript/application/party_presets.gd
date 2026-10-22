# {
#   責務: [party_presets: Validate catalog/new drafts and coordinate preset-only I/O; no implicit state save.]
#   フィールド: [persistence: persistence（RefCounted）]
# }
extends RefCounted
## Validate catalog/new drafts and coordinate preset-only I/O; no implicit state save.

const Contract = preload("res://engine/party_preset_contract.gd")
const Store = preload("res://data/party_preset_store.gd")
const Selection = preload("res://engine/party_selection.gd")
var persistence: RefCounted


# {
#   責務: [_init: パーティ・プリセット一覧が利用する初期状態と依存を設定する]
#   処理: [1: パーティ・プリセット一覧が利用する初期状態と依存を設定する]
#   引数: [field_persistence: フィールド・persistence（RefCounted）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(field_persistence: RefCounted) -> void:
	persistence = field_persistence


# {
#   責務: [_profile: パーティ・プリセット一覧のプロファイルを求める]
#   処理: [1: パーティ・プリセット一覧のプロファイルを求める]
#   引数: []
#   戻り値: [result: パーティ・プリセット一覧のプロファイルを求めるための結果（Dictionary）]
# }
func _profile() -> Dictionary:
	var state: Dictionary = persistence.load_position()
	if not state["ok"]:
		return state
	return persistence.store.resolve_profile(persistence.profile_name)


# {
#   責務: [read_catalog: catalogを読み取る]
#   処理: [1: catalogを読み取る]
#   引数: []
#   戻り値: [result: catalogを読み取るための結果（Dictionary）]
# }
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


# {
#   責務: [save_new: newを保存する]
#   処理: [1: newを保存する]
#   引数: [
#     name: 名前（String）
#     members: 個体一覧（Array）
#   ]
#   戻り値: [result: newを保存するための結果（Dictionary）]
# }
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


# {
#   責務: [load_draft: 下書きを読み込む]
#   処理: [1: 下書きを読み込む]
#   引数: [
#     filename: filename（String）
#     editor: editor（RefCounted）
#   ]
#   戻り値: [result: 下書きを読み込むための結果（Dictionary）]
# }
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
