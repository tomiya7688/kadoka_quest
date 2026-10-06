# {
#   責務: [content_repository: Read-only access to the existing canonical data, never savedata/UserData.]
#   フィールド: [
#     root: 基準ディレクトリ（String）
#     last_error: last・error
#   ]
# }
extends RefCounted
## Read-only access to the existing canonical data, never savedata/UserData.

var root: String
var last_error := ""


# {
#   責務: [_init: content・データ取得先が利用する初期状態と依存を設定する]
#   処理: [1: content・データ取得先が利用する初期状態と依存を設定する]
#   引数: [content_root: content・基準ディレクトリ（String）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(content_root: String) -> void:
	root = content_root.simplify_path()


# {
#   責務: [_read_dictionary: dictionaryを読み取る]
#   処理: [1: dictionaryを読み取る]
#   引数: [relative: relative（String）]
#   戻り値: [result: dictionaryを読み取るための結果（Dictionary）]
# }
func _read_dictionary(relative: String) -> Dictionary:
	last_error = ""
	var path := root.path_join(relative)
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		last_error = "Cannot read: " + path
		return {}
	var json := JSON.new()
	if json.parse(file.get_as_text()) != OK or not json.data is Dictionary:
		last_error = "Invalid JSON object: " + path
		return {}
	return json.data


# {
#   責務: [valid_id: content・データ取得先のvalid・識別子を求める]
#   処理: [1: content・データ取得先のvalid・識別子を求める]
#   引数: [value: 値（String）]
#   戻り値: [result: content・データ取得先のvalid・識別子を求めるための結果（bool）]
# }
static func valid_id(value: String) -> bool:
	if value.is_empty():
		return false
	for character in value:
		if not character in "abcdefghijklmnopqrstuvwxyz0123456789_-":
			return false
	return true


# {
#   責務: [load_blocks: ブロック定義を読み込む]
#   処理: [1: ブロック定義を読み込む]
#   引数: []
#   戻り値: [result: ブロック定義を読み込むための結果（Dictionary）]
# }
func load_blocks() -> Dictionary:
	var definitions := {}
	var folder := root.path_join("data/blocks")
	if not DirAccess.dir_exists_absolute(folder):
		last_error = "Missing blocks directory: " + folder
		return {}
	for filename in DirAccess.get_files_at(folder):
		if filename.ends_with(".json"):
			var block := _read_dictionary("data/blocks/" + filename)
			if block.is_empty() or not block.get("id") is String:
				if last_error.is_empty():
					last_error = "Missing block id: " + filename
				return {}
			definitions[block["id"]] = block
	return definitions


# {
#   責務: [load_map: マップを読み込む]
#   処理: [1: マップを読み込む]
#   引数: [map_id: マップ・識別子（String）]
#   戻り値: [result: マップを読み込むための結果（Dictionary）]
# }
func load_map(map_id: String) -> Dictionary:
	if not valid_id(map_id):
		last_error = "Invalid map id: " + map_id
		return {}
	var world := _read_dictionary("data/maps/" + map_id + "/map.json")
	if world.is_empty():
		return {}
	if world.get("id") != map_id or not world.get("tiles") is Array \
		or not _positive_integer(world.get("width")) or not _positive_integer(world.get("height")) \
		or not world.get("start") is Dictionary or not world.get("events", []) is Array:
		last_error = "Invalid map dimensions/start: " + map_id
		return {}
	if world["tiles"].size() != int(world["height"]):
		last_error = "Invalid map rows: " + map_id
		return {}
	for row in world["tiles"]:
		if not row is Array or row.size() != int(world["width"]):
			last_error = "Invalid map columns: " + map_id
			return {}
	world["events"] = world.get("events", []).duplicate(true)
	var folder := "data/maps/" + map_id + "/events"
	var filenames := PackedStringArray()
	if DirAccess.dir_exists_absolute(root.path_join(folder)):
		filenames = DirAccess.get_files_at(root.path_join(folder))
	filenames.sort()
	for filename in filenames:
		if not filename.ends_with(".json"):
			continue
		var extra := _read_dictionary(folder.path_join(filename))
		var embedded: Variant = extra.get("events")
		var values: Array = embedded if embedded is Array else [extra]
		for event in values:
			if event is Dictionary and event.get("id"):
				world["events"].append(event)
	last_error = ""
	return world


# {
#   責務: [_positive_integer: content・データ取得先のpositive・integerを求める]
#   処理: [1: content・データ取得先のpositive・integerを求める]
#   引数: [value: 値（Variant）]
#   戻り値: [result: content・データ取得先のpositive・integerを求めるための結果（bool）]
# }
static func _positive_integer(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value)) and float(value) > 0 \
		and float(value) == floorf(float(value))


# {
#   責務: [load_species: 種族を読み込む]
#   処理: [1: 種族を読み込む]
#   引数: [species_id: 種族・識別子（String）]
#   戻り値: [result: 種族を読み込むための結果（Dictionary）]
# }
func load_species(species_id: String) -> Dictionary:
	if not valid_id(species_id):
		last_error = "Invalid species id: " + species_id
		return {}
	return _read_dictionary("data/species/" + species_id + "/species.json")


# {
#   責務: [load_progression: progressionを読み込む]
#   処理: [1: progressionを読み込む]
#   引数: [species_id: 種族・識別子（String）]
#   戻り値: [result: progressionを読み込むための結果（Dictionary）]
# }
func load_progression(species_id: String) -> Dictionary:
	if not valid_id(species_id):
		last_error = "Invalid species id: " + species_id
		return {"ok": false, "error": "invalid_species_id", "message": last_error}
	var bundle: Dictionary = {"ok": true}
	for name: String in ["stats", "skills"]:
		var document := _read_dictionary("data/species/" + species_id + "/" + name + ".json")
		if not last_error.is_empty():
			return {"ok": false, "error": "invalid_content", "message": last_error}
		bundle[name] = document
	return bundle


# {
#   責務: [load_plus: ＋選択を読み込む]
#   処理: [1: ＋選択を読み込む]
#   引数: [species_id: 種族・識別子（String）]
#   戻り値: [result: ＋選択を読み込むための結果（Dictionary）]
# }
func load_plus(species_id: String) -> Dictionary:
	if not valid_id(species_id):
		last_error = "Invalid species id: " + species_id
		return {"ok": false, "error": "invalid_species_id", "message": last_error}
	return _content_result("data/species/" + species_id + "/plus.json")


# {
#   責務: [load_equipment: 装備を読み込む]
#   処理: [1: 装備を読み込む]
#   引数: []
#   戻り値: [result: 装備を読み込むための結果（Dictionary）]
# }
func load_equipment() -> Dictionary:
	return _content_result("data/equipment/equipment.json")


# {
#   責務: [load_skills: スキル一覧を読み込む]
#   処理: [1: スキル一覧を読み込む]
#   引数: []
#   戻り値: [result: スキル一覧を読み込むための結果（Dictionary）]
# }
func load_skills() -> Dictionary:
	return _content_result("data/skills/skills.json")


# {
#   責務: [_content_result: content・データ取得先のcontent・処理結果を求める]
#   処理: [1: content・データ取得先のcontent・処理結果を求める]
#   引数: [relative: relative（String）]
#   戻り値: [result: content・データ取得先のcontent・処理結果を求めるための結果（Dictionary）]
# }
func _content_result(relative: String) -> Dictionary:
	var document := _read_dictionary(relative)
	if not last_error.is_empty():
		return {"ok": false, "error": "invalid_content", "message": last_error}
	return {"ok": true, "value": document}
