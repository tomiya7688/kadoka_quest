extends RefCounted
## JSON object I/O. Replacement failure never deletes the previous destination.


static func read_object(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {"ok": false, "error": "not_found", "message": "セーブがありません。"}
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {"ok": false, "error": "read_failed", "message": "読込できません: " + path}
	var text := file.get_as_text()
	file.close()
	var json := JSON.new()
	if json.parse(text) != OK or not json.data is Dictionary:
		return {"ok": false, "error": "invalid_json", "message": "JSONが壊れています: " + path}
	return {"ok": true, "value": json.data, "digest": text.sha256_text()}


static func write_atomic(path: String, value: Dictionary) -> Dictionary:
	var token := Crypto.new().generate_random_bytes(12).hex_encode()
	var temporary := path.get_base_dir().path_join("." + path.get_file() + "." + token + ".tmp")
	var file := FileAccess.open(temporary, FileAccess.WRITE)
	if file == null:
		return {"ok": false, "error": "write_failed", "message": "一時ファイルを作成できません: " + path}
	file.store_string(JSON.stringify(value, "  ") + "\n")
	file.flush()
	var error := file.get_error()
	file.close()
	if error == OK:
		error = DirAccess.rename_absolute(temporary, path)
	if error != OK:
		DirAccess.remove_absolute(temporary)  # Only this invocation's owned temporary file.
		return {"ok": false, "error": "replace_failed", "message": "保存できません（前のセーブは保持）: " + path}
	return {"ok": true, "path": path}
