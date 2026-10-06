# {
#   責務: [party_preset_store: Read JSON files and create a uniquely named new preset, never update or delete existing ones.]
#   フィールド: [root: 基準ディレクトリ（String）]
# }
extends RefCounted
## Read JSON files and create a uniquely named new preset, never update or delete existing ones.

const Documents = preload("res://data/json_documents.gd")
const Individual = preload("res://engine/monster_record_contract.gd")
var root: String


# {
#   責務: [_init: パーティ・プリセット・保存先が利用する初期状態と依存を設定する]
#   処理: [1: パーティ・プリセット・保存先が利用する初期状態と依存を設定する]
#   引数: [profile_path: プロファイル・パス（String）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(profile_path: String) -> void:
	root = profile_path.path_join("parties")


# {
#   責務: [safe_filename: パーティ・プリセット・保存先のsafe・filenameを求める]
#   処理: [1: パーティ・プリセット・保存先のsafe・filenameを求める]
#   引数: [filename: filename（String）]
#   戻り値: [result: パーティ・プリセット・保存先のsafe・filenameを求めるための結果（bool）]
# }
static func safe_filename(filename: String) -> bool:
	return filename.ends_with(".json") and not filename.trim_suffix(".json").is_empty() \
		and Individual.safe_id(filename) and filename.get_file() == filename


# {
#   責務: [scan_documents: 文書一覧を再走査する]
#   処理: [1: 文書一覧を再走査する]
#   引数: []
#   戻り値: [result: 文書一覧を再走査するための結果（Dictionary）]
# }
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


# {
#   責務: [read_document: 文書を読み取る]
#   処理: [1: 文書を読み取る]
#   引数: [filename: filename（String）]
#   戻り値: [result: 文書を読み取るための結果（Dictionary）]
# }
func read_document(filename: String) -> Dictionary:
	if not safe_filename(filename):
		return {"ok": false, "message": "不正なプリセットファイル名です。"}
	var directory := DirAccess.open(root)
	if directory != null and directory.is_link(filename):
		return {"ok": false, "message": "リンクされたプリセットは読込しません。"}
	return Documents.read_object(root.path_join(filename))


# {
#   責務: [create_new: newを作成する]
#   処理: [1: newを作成する]
#   引数: [
#     stem: stem（String）
#     document: 文書（Dictionary）
#   ]
#   戻り値: [result: newを作成するための結果（Dictionary）]
# }
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
