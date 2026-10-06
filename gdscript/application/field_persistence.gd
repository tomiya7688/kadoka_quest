# {
#   責務: [field_persistence: Validate before applying a load or writing a save. Does not render or move a session.]
#   フィールド: [
#     repository: データ取得先（RefCounted）
#     store: 保存先（RefCounted）
#     blocks: ブロック定義（Dictionary）
#     profile_name: プロファイル・名前（String）
#     roster: 所有個体台帳（RefCounted）
#   ]
# }
extends RefCounted
## Validate before applying a load or writing a save. Does not render or move a session.

const Contract = preload("res://engine/field_save_contract.gd")
const Roster = preload("res://application/owned_roster.gd")
var repository: RefCounted
var store: RefCounted
var blocks: Dictionary
var profile_name: String
var roster: RefCounted


# {
#   責務: [_init: フィールド・persistenceが利用する初期状態と依存を設定する]
#   処理: [1: フィールド・persistenceが利用する初期状態と依存を設定する]
#   引数: [
#     content: content（RefCounted）
#     saves: saves（RefCounted）
#     definitions: definitions（Dictionary）
#     name: 名前（String）
#   ]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(content: RefCounted, saves: RefCounted, definitions: Dictionary, name: String) -> void:
	repository = content
	store = saves
	blocks = definitions
	profile_name = name
	roster = Roster.new(content, saves, name)


# {
#   責務: [load_position: 座標を読み込む]
#   処理: [1: 座標を読み込む]
#   引数: []
#   戻り値: [result: 座標を読み込むための結果（Dictionary）]
# }
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


# {
#   責務: [save_position: 座標を保存する]
#   処理: [1: 座標を保存する]
#   引数: [session: セッション（RefCounted）]
#   戻り値: [result: 座標を保存するための結果（Dictionary）]
# }
func save_position(session: RefCounted) -> Dictionary:
	var previous := load_position()
	if not previous["ok"] and previous["error"] != "not_found":
		return previous
	var base: Dictionary = previous.get("value", Contract.DEFAULT_STATE)
	var snapshot := Contract.capture(base, session.world["id"], session.x, session.y, session.direction)
	var valid := Contract.validate_location(snapshot, session.world, blocks, session.visible_characters)
	if not valid["ok"]:
		return valid
	if not previous["ok"]:
		var starters: Dictionary = roster.prepare_starters()
		if not starters["ok"]:
			return starters
		snapshot["current_party"] = starters["members"]
	return store.save_profile(profile_name, snapshot, previous.get("digest", ""), Contract.INITIAL_INVENTORY)


# {
#   責務: [read_owned_roster: owned・所有個体台帳を読み取る]
#   処理: [1: owned・所有個体台帳を読み取る]
#   引数: []
#   戻り値: [result: owned・所有個体台帳を読み取るための結果（Dictionary）]
# }
func read_owned_roster() -> Dictionary:
	var loaded := load_position()
	if not loaded["ok"]:
		return loaded
	return roster.read_snapshot(loaded["value"])
