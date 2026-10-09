# {
#   責務: [content_repository: プロジェクト内の正規dataを読み取る入口です。保存やUserData管理は担当しません]
#   フィールド: [
#     root: data/を含むプロジェクトの基準ディレクトリ（String）
#     last_error: 直近JSON読み取りの失敗理由。成功時は空文字列です（String）
#   ]
# }
extends RefCounted
## 正規dataの読み取りを担当し、保存データの書き込みは行いません。

var root: String
var last_error := ""


# {
#   責務: [_init: 正規dataの相対参照に使うプロジェクト基準パスを保持します]
#   処理: [1: 指定パスを簡約化し、rootへ保持します]
#   引数: [content_root: data/を含むプロジェクトのディレクトリ。data/自体ではありません（String）]
#   戻り値: [result: なし（void）]
# }
func _init(content_root: String) -> void:
	root = content_root.simplify_path()


# {
#   責務: [_read_dictionary: 基準ディレクトリ内のJSONオブジェクトを読み、失敗時は空辞書とlast_errorを返します]
#   処理: [1: 基準ディレクトリ内のJSONオブジェクトを読み、失敗時は空辞書とlast_errorを返します]
#   引数: [relative: 正規data内のJSON相対パス（String）]
#   戻り値: [result: 読み取ったJSONオブジェクト、またはlast_errorを設定した空辞書（Dictionary）]
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
#   責務: [valid_id: 種族やマップのIDが小文字英数字・下線・ハイフンだけの非空文字列か確認します]
#   処理: [1: 種族やマップのIDが小文字英数字・下線・ハイフンだけの非空文字列か確認します]
#   引数: [value: 検証する種族またはマップのID候補（String）]
#   戻り値: [result: 非空IDが小文字英数字・下線・ハイフンだけならtrue、それ以外false（bool）]
# }
static func valid_id(value: String) -> bool:
	if value.is_empty():
		return false
	for character in value:
		if not character in "abcdefghijklmnopqrstuvwxyz0123456789_-":
			return false
	return true


# {
#   責務: [load_blocks: 正規ブロックJSONを読み、各IDをキーにした定義辞書を返します]
#   処理: [1: 正規ブロックJSONを読み、各IDをキーにした定義辞書を返します]
#   引数: []
#   戻り値: [result: ブロックIDをキーにした定義一覧、またはlast_errorを設定した空辞書（Dictionary）]
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
#   責務: [load_map: 指定マップの寸法・行・開始位置を検証し、イベントファイルをID付きイベントへ追加します]
#   処理: [1: 指定マップの寸法・行・開始位置を検証し、イベントファイルをID付きイベントへ追加します]
#   引数: [map_id: マップ・識別子（String）]
#   戻り値: [result: 寸法・開始地点・タイル・結合イベントを持つマップ、または失敗時の空辞書（Dictionary）]
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
#   責務: [_positive_integer: 値が有限で小数部のない正の数値か検証します]
#   処理: [1: 値が有限で小数部のない正の数値か検証します]
#   引数: [value: 値（Variant）]
#   戻り値: [result: 有限で小数部のない正の数値ならtrue、それ以外false（bool）]
# }
static func _positive_integer(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value)) and float(value) > 0 \
		and float(value) == floorf(float(value))


# {
#   責務: [load_species: 安全な種族IDのspecies.jsonを読み、失敗時は空辞書とlast_errorを返します]
#   処理: [1: 安全な種族IDのspecies.jsonを読み、失敗時は空辞書とlast_errorを返します]
#   引数: [species_id: 種族・識別子（String）]
#   戻り値: [result: 指定種族のspecies.jsonオブジェクト、またはlast_errorを設定した空辞書（Dictionary）]
# }
func load_species(species_id: String) -> Dictionary:
	if not valid_id(species_id):
		last_error = "Invalid species id: " + species_id
		return {}
	return _read_dictionary("data/species/" + species_id + "/species.json")


# {
#   責務: [load_progression: 指定種族のstats.jsonとskills.jsonを読み、基礎再構築用の定義組を返します]
#   処理: [1: 指定種族のstats.jsonとskills.jsonを読み、基礎再構築用の定義組を返します]
#   引数: [species_id: 種族・識別子（String）]
#   戻り値: [result: ok=trueとstats/skillsの定義組、またはerror/message付き読込失敗（Dictionary）]
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
#   責務: [load_plus: 指定種族のplus.jsonを読み、okと定義valueまたは読込失敗を返します]
#   処理: [1: 指定種族のplus.jsonを読み、okと定義valueまたは読込失敗を返します]
#   引数: [species_id: 種族・識別子（String）]
#   戻り値: [result: ok=trueとplus.jsonのvalue、またはerror/message付き読込失敗（Dictionary）]
# }
func load_plus(species_id: String) -> Dictionary:
	if not valid_id(species_id):
		last_error = "Invalid species id: " + species_id
		return {"ok": false, "error": "invalid_species_id", "message": last_error}
	return _content_result("data/species/" + species_id + "/plus.json")


# {
#   責務: [load_equipment: 正規equipment.jsonを読み、okと定義valueまたは読込失敗を返します]
#   処理: [1: 正規equipment.jsonを読み、okと定義valueまたは読込失敗を返します]
#   引数: []
#   戻り値: [result: ok=trueとequipment.jsonのvalue、またはerror/message付き読込失敗（Dictionary）]
# }
func load_equipment() -> Dictionary:
	return _content_result("data/equipment/equipment.json")


# {
#   責務: [load_skills: 正規skills.jsonを読み、okと定義valueまたは読込失敗を返します]
#   処理: [1: 正規skills.jsonを読み、okと定義valueまたは読込失敗を返します]
#   引数: []
#   戻り値: [result: ok=trueとskills.jsonのvalue、またはerror/message付き読込失敗（Dictionary）]
# }
func load_skills() -> Dictionary:
	return _content_result("data/skills/skills.json")


# {
#   責務: [_content_result: 正規JSONオブジェクトの読込を成功valueまたは失敗理由として返します]
#   処理: [1: 正規JSONオブジェクトの読込を成功valueまたは失敗理由として返します]
#   引数: [relative: 正規data内のJSON相対パス（String）]
#   戻り値: [result: ok=trueと読み取ったvalue、またはerror/message付き読込失敗（Dictionary）]
# }
func _content_result(relative: String) -> Dictionary:
	var document := _read_dictionary(relative)
	if not last_error.is_empty():
		return {"ok": false, "error": "invalid_content", "message": last_error}
	return {"ok": true, "value": document}
