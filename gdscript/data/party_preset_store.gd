extends RefCounted
## Read JSON files and create a uniquely named new preset, never update or delete existing ones.

const Documents = preload("res://data/json_documents.gd")
const Individual = preload("res://engine/monster_record_contract.gd")
var root: String


func _init(profile_path: String) -> void:
	root = profile_path.path_join("parties")


static func safe_filename(filename: String) -> bool:
	return filename.ends_with(".json") and not filename.trim_suffix(".json").is_empty() \
		and Individual.safe_id(filename) and filename.get_file() == filename


func scan_documents() -> Dictionary:
	var entries: Array = []
	var warnings: Array = []
	if not DirAccess.dir_exists_absolute(root):
		if FileAccess.file_exists(root):
			return {"ok": false, "message": "partiesがフォルダではありません。"}
		return {"ok": true, "entries": entries, "warnings": warnings}
	var directory := DirAccess.open(root)
	if directory == null:
		return {"ok": false, "message": "プリセット一覧を読込できません。"}
	var filenames := DirAccess.get_files_at(root)
	filenames.sort()
	for filename in filenames:
		if not filename.ends_with(".json"):
			continue
		var result := read_document(filename)
		if result["ok"]:
			entries.append({"filename": filename, "value": result["value"]})
		else:
			warnings.append(filename + ": " + str(result["message"]))
	return {"ok": true, "entries": entries, "warnings": warnings}


func read_document(filename: String) -> Dictionary:
	if not safe_filename(filename):
		return {"ok": false, "message": "不正なプリセットファイル名です。"}
	var directory := DirAccess.open(root)
	if directory != null and directory.is_link(filename):
		return {"ok": false, "message": "リンクされたプリセットは読込しません。"}
	return Documents.read_object(root.path_join(filename))


func create_new(stem: String, document: Dictionary) -> Dictionary:
	if not safe_filename(stem + ".json"):
		return {"ok": false, "message": "不正なプリセット保存名です。"}
	if FileAccess.file_exists(root) and not DirAccess.dir_exists_absolute(root):
		return {"ok": false, "message": "partiesがフォルダではありません。元のファイルは保持します。"}
	if DirAccess.make_dir_recursive_absolute(root) != OK:
		return {"ok": false, "message": "プリセット保存先を作成できません。"}
	var filename := stem + ".json"
	var directory := DirAccess.open(root)
	var index := 2
	if directory == null:
		return {"ok": false, "message": "プリセット保存先を開けません。"}
	while directory.file_exists(filename) or directory.dir_exists(filename) or directory.is_link(filename):
		filename = "%s_%d.json" % [stem, index]
		index += 1
	var result := Documents.write_atomic(root.path_join(filename), document)
	if result["ok"]:
		result["filename"] = filename
	return result
