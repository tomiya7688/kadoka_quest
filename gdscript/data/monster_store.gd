extends RefCounted
## Read individual folders; publish only entirely new two-document folders.

const Documents = preload("res://data/json_documents.gd")
const Contract = preload("res://engine/monster_record_contract.gd")
var root: String


func _init(profile_path: String) -> void:
	root = profile_path.path_join("monsters")


func scan_documents() -> Dictionary:
	var entries: Array = []
	var warnings: Array = []
	if not DirAccess.dir_exists_absolute(root):
		if FileAccess.file_exists(root):
			return {"ok": false, "message": "monstersがフォルダではありません"}
		return {"ok": true, "entries": entries, "warnings": warnings}
	var directory := DirAccess.open(root)
	if directory == null:
		return {"ok": false, "message": "monstersを読込できません"}
	var folders := DirAccess.get_directories_at(root)
	folders.sort()
	for id in folders:
		if id.begins_with("."):
			continue  # Owned staging folders are not published individuals.
		if not Contract.safe_id(id) or directory.is_link(id):
			warnings.append(id + ": 不正なID/リンクのため読込しません")
			continue
		var folder := root.path_join(id)
		var inside := DirAccess.open(folder)
		if inside == null or inside.is_link("monster.json") or inside.is_link("ai.json"):
			warnings.append(id + ": 個体フォルダを安全に読込できません")
			continue
		var monster := Documents.read_object(folder.path_join("monster.json"))
		var ai := Documents.read_object(folder.path_join("ai.json"))
		if not monster["ok"] or not ai["ok"]:
			warnings.append(id + ": monster.json/ai.jsonが欠損または不正です")
			continue
		entries.append({"folder_id": id, "monster": monster["value"], "ai": ai["value"]})
	return {"ok": true, "entries": entries, "warnings": warnings}


func create_new(record: Dictionary) -> Dictionary:
	var id: String = record["monster"]["id"]
	if not Contract.safe_id(id):
		return {"ok": false, "message": "不正な個体IDです"}
	var destination := root.path_join(id)
	if DirAccess.dir_exists_absolute(destination) or FileAccess.file_exists(destination):
		return {"ok": false, "message": "既存個体は上書きしません: " + id}
	if DirAccess.make_dir_recursive_absolute(root) != OK:
		return {"ok": false, "message": "個体保存先を作成できません"}
	var temporary := root.path_join(".pending_" + Crypto.new().generate_random_bytes(12).hex_encode())
	if DirAccess.make_dir_absolute(temporary) != OK:
		return {"ok": false, "message": "個体の一時フォルダを作成できません"}
	for document in ["monster", "ai"]:
		var result := Documents.write_atomic(temporary.path_join(document + ".json"), record[document])
		if not result["ok"]:
			_discard_staging(temporary)
			return result
	if DirAccess.dir_exists_absolute(destination) or FileAccess.file_exists(destination) \
		or DirAccess.rename_absolute(temporary, destination) != OK:
		_discard_staging(temporary)
		return {"ok": false, "message": "個体を公開できません（既存個体は保持）: " + id}
	return {"ok": true, "id": id}


static func _discard_staging(path: String) -> void:
	# Only the two files in this invocation's newly created staging folder, never recursive.
	for filename in ["monster.json", "ai.json"]:
		if FileAccess.file_exists(path.path_join(filename)):
			DirAccess.remove_absolute(path.path_join(filename))
	DirAccess.remove_absolute(path)
