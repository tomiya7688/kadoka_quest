extends RefCounted
## Coordinate owned-folder validation and the game's first-save starter policy.

const Contract = preload("res://engine/monster_record_contract.gd")
const MonsterStore = preload("res://data/monster_store.gd")
const STARTERS := [{"species_id": "hero", "name": "主人公"}, {"species_id": "ball_slime", "name": "ボールスライム"}]
var repository: RefCounted
var saves: RefCounted
var profile_name: String


func _init(content: RefCounted, store: RefCounted, name: String) -> void:
	repository = content
	saves = store
	profile_name = name


func read_snapshot(state: Dictionary) -> Dictionary:
	var profile: Dictionary = saves.resolve_profile(profile_name)
	if not profile["ok"]:
		return profile
	var documents: Dictionary = MonsterStore.new(profile["path"]).scan_documents()
	if not documents["ok"]:
		return documents
	var records: Dictionary = {}
	var warnings: Array = documents["warnings"]
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
	if not state.get("current_party", []) is Array:
		warnings.append("current_partyが配列ではありません")
	return {"ok": true, "records": records, "warnings": warnings, "party": Contract.party_entries(state, records)}


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


static func _existing_species(records: Dictionary, species_id: String) -> String:
	for id: String in records:
		if records[id]["monster"]["species_id"] == species_id:
			return id
	return ""
