extends RefCounted
## Named folders/state JSON. Never writes existing monsters, AI, items or presets.

const Documents = preload("res://data/json_documents.gd")
var root: String


func _init(save_root: String) -> void:
	root = ProjectSettings.globalize_path(save_root).replace("\\", "/").simplify_path()


static func validate_name(name: String) -> Dictionary:
	if name.is_empty() or name != name.strip_edges() or name in [".", ".."] or name.ends_with("."):
		return {"ok": false, "error": "invalid_name", "message": "セーブ名の空白・ドットを確認してください。"}
	for index in name.length():
		if name.unicode_at(index) < 32 or name[index] in "\\/:*?\"<>|":
			return {"ok": false, "error": "invalid_name", "message": "セーブ名にパスや制御文字は使えません。"}
	var device := name.get_slice(".", 0).to_upper()
	if device in ["CON", "PRN", "AUX", "NUL"] or device in [
		"COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
		"LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
	]:
		return {"ok": false, "error": "invalid_name", "message": "Windowsの予約名は使えません。"}
	return {"ok": true, "name": name.left(40)}


func resolve_profile(name: String) -> Dictionary:
	var result := validate_name(name)
	if not result["ok"]:
		return result
	if not root.is_absolute_path():
		return {"ok": false, "error": "invalid_root", "message": "保存先には絶対パスを指定してください。"}
	var path := root.path_join(result["name"])
	var directory := DirAccess.open(root)
	if directory != null and directory.is_link(result["name"]):
		return {"ok": false, "error": "linked_profile", "message": "リンクされたセーブフォルダは使用できません。"}
	var inside := DirAccess.open(path)
	if inside != null:
		for child in ["state.json", "items", "meta.json", "monsters", "parties"]:
			if inside.is_link(child):
				return {"ok": false, "error": "linked_profile", "message": "リンクされた保存データは使用できません。"}
	return {"ok": true, "path": path, "name": result["name"]}


func load_profile(name: String) -> Dictionary:
	var profile := resolve_profile(name)
	if not profile["ok"]:
		return profile
	return Documents.read_object(profile["path"].path_join("state.json"))


func save_profile(name: String, value: Dictionary, expected_digest: String, inventory: Dictionary) -> Dictionary:
	var profile := resolve_profile(name)
	if not profile["ok"]:
		return profile
	var path: String = profile["path"]
	var current := Documents.read_object(path.path_join("state.json"))
	if not current["ok"] and current["error"] != "not_found":
		return current
	var digest: String = current.get("digest", "")
	if digest != expected_digest:
		return {"ok": false, "error": "changed", "message": "セーブが外部で変更されました。読み込み直してください。"}
	if not current["ok"]:
		var prepared := _prepare_profile(path, profile["name"], inventory)
		if not prepared["ok"]:
			return prepared
	return Documents.write_atomic(path.path_join("state.json"), value)


func _prepare_profile(path: String, name: String, inventory: Dictionary) -> Dictionary:
	for folder in ["", "monsters", "items", "parties"]:
		var error := DirAccess.make_dir_recursive_absolute(path.path_join(folder))
		if error != OK:
			return {"ok": false, "error": "mkdir_failed", "message": "保存フォルダを作成できません: " + path}
	var initial := {
		"items/items.json": {"schema_version": 1, "items": inventory},
		"meta.json": {"schema_version": 1, "name": name, "created_at": Time.get_datetime_string_from_system()},
	}
	for relative: String in initial:
		if not FileAccess.file_exists(path.path_join(relative)):
			var result := Documents.write_atomic(path.path_join(relative), initial[relative])
			if not result["ok"]:
				return result
	return {"ok": true}
