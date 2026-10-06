# {
#   責務: [owned_roster: Coordinate owned-folder validation and the game's first-save starter policy.]
#   フィールド: [
#     repository: データ取得先（RefCounted）
#     saves: saves（RefCounted）
#     profile_name: プロファイル・名前（String）
#   ]
# }
extends RefCounted
## Coordinate owned-folder validation and the game's first-save starter policy.

const Contract = preload("res://engine/monster_record_contract.gd")
const MonsterStore = preload("res://data/monster_store.gd")
const Progression = preload("res://application/monster_reconstruction.gd")
const STARTERS := [{"species_id": "hero", "name": "主人公"}, {"species_id": "ball_slime", "name": "ボールスライム"}]
var repository: RefCounted
var saves: RefCounted
var profile_name: String


# {
#   責務: [_init: owned・所有個体台帳が利用する初期状態と依存を設定する]
#   処理: [1: owned・所有個体台帳が利用する初期状態と依存を設定する]
#   引数: [
#     content: content（RefCounted）
#     store: 保存先（RefCounted）
#     name: 名前（String）
#   ]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(content: RefCounted, store: RefCounted, name: String) -> void:
	repository = content
	saves = store
	profile_name = name


# {
#   責務: [read_snapshot: 独立した状態の写しを読み取る]
#   処理: [1: 独立した状態の写しを読み取る]
#   引数: [state: 状態（Dictionary）]
#   戻り値: [result: 独立した状態の写しを読み取るための結果（Dictionary）]
# }
func read_snapshot(state: Dictionary) -> Dictionary:
	var profile: Dictionary = saves.resolve_profile(profile_name)
	if not profile["ok"]:
		return profile
	var documents: Dictionary = MonsterStore.new(profile["path"]).scan_documents()
	if not documents["ok"]:
		return documents
	var records: Dictionary = {}
	var warnings: Array = documents["warnings"]
	var progression = Progression.new(repository)
	for entry: Dictionary in documents["entries"]:
		var valid := Contract.validate_record(entry["monster"], entry["ai"], entry["folder_id"])
		if not valid["ok"]:
			warnings.append(entry["folder_id"] + ": " + valid["message"])
			continue
		var species: Dictionary = repository.load_species(entry["monster"]["species_id"])
		if species.is_empty() or species.get("id") != entry["monster"]["species_id"]:
			warnings.append(entry["folder_id"] + ": 種族定義がありません")
			continue
		records[entry["folder_id"]] = {"monster": entry["monster"], "ai": entry["ai"], "species": species}
		var rebuilt: Dictionary = progression.rebuild(entry["monster"])
		records[entry["folder_id"]]["progression"] = rebuilt
		if not rebuilt["ok"]:
			warnings.append(entry["folder_id"] + ": 基礎能力値/習得スキルを読込できません: " + rebuilt["message"])
		elif not rebuilt["modifiers"]["ok"]:
			warnings.append(entry["folder_id"] + ": 能力値補正を読込できません: " + rebuilt["modifiers"]["message"])
	if not state.get("current_party", []) is Array:
		warnings.append("current_partyが配列ではありません")
	return {"ok": true, "records": records, "warnings": warnings, "party": Contract.party_entries(state, records)}


# {
#   責務: [prepare_starters: startersを準備する]
#   処理: [1: startersを準備する]
#   引数: []
#   戻り値: [result: startersを準備するための結果（Dictionary）]
# }
func prepare_starters() -> Dictionary:
	var snapshot := read_snapshot({})
	if not snapshot["ok"]:
		return snapshot
	if not snapshot["warnings"].is_empty():
		return {"ok": false, "message": "既存個体の問題を修正してから新規保存してください: " + str(snapshot["warnings"][0])}
	var definitions: Array = []
	for starter: Dictionary in STARTERS:
		var species: Dictionary = repository.load_species(starter["species_id"])
		if species.get("id") != starter["species_id"] or not species.get("display_name") is String:
			return {"ok": false, "message": "初期種族を読込できません: " + starter["species_id"]}
		definitions.append(species)
	var profile: Dictionary = saves.resolve_profile(profile_name)
	if not profile["ok"]:
		return profile
	var store = MonsterStore.new(profile["path"])
	var members: Array = []
	for index in STARTERS.size():
		var id := _existing_species(snapshot["records"], STARTERS[index]["species_id"])
		if id.is_empty():
			id = "monster_" + Crypto.new().generate_random_bytes(6).hex_encode()
			var record := Contract.create_record(id, definitions[index], STARTERS[index]["name"])
			var created: Dictionary = store.create_new(record)
			if not created["ok"]:
				return created
		members.append(id)
	return {"ok": true, "members": members}


# {
#   責務: [_existing_species: owned・所有個体台帳のexisting・種族を求める]
#   処理: [1: owned・所有個体台帳のexisting・種族を求める]
#   引数: [
#     records: 個体レコード一覧（Dictionary）
#     species_id: 種族・識別子（String）
#   ]
#   戻り値: [result: owned・所有個体台帳のexisting・種族を求めるための結果（String）]
# }
static func _existing_species(records: Dictionary, species_id: String) -> String:
	for id: String in records:
		if records[id]["monster"]["species_id"] == species_id:
			return id
	return ""
