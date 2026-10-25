# {
#   責務: [field_save_store: Named folders/state JSON. Never writes existing monsters, AI, items or presets.]
#   フィールド: [root: 基準ディレクトリ（String）]
# }
extends RefCounted
## Named folders/state JSON. Never writes existing monsters, AI, items or presets.

const Documents = preload("res://data/json_documents.gd")
var root: String


# {
#   責務: [_init: フィールド・保存・保存先が利用する初期状態と依存を設定する]
#   処理: [1: フィールド・保存・保存先が利用する初期状態と依存を設定する]
#   引数: [save_root: 保存・基準ディレクトリ（String）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(save_root: String) -> void:
	root = ProjectSettings.globalize_path(save_root).replace("\\", "/").simplify_path()


# {
#   責務: [validate_name: 名前を妥当性を検査する]
#   処理: [1: 名前を妥当性を検査する]
#   引数: [name: 名前（String）]
#   戻り値: [result: 名前を妥当性を検査するための結果（Dictionary）]
# }
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


# {
#   責務: [resolve_profile: プロファイルを解決する]
#   処理: [1: プロファイルを解決する]
#   引数: [name: 名前（String）]
#   戻り値: [result: プロファイルを解決するための結果（Dictionary）]
# }
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


# {
#   責務: [list_profiles: タイトル画面の「つづきから」で選べる、保存先直下の名前付きセーブを列挙します。読み書きはしません]
#   処理: [
#     1: 保存先がまだない場合は、セーブなしの成功として空の一覧を返します
#     2: 保存先直下のフォルダごとに、resolve_profileと同じ名前・リンク検査を行い、state.jsonがあるものだけを残します
#     3: 選べないフォルダの理由を警告へ残し、名前を大文字小文字を区別しない自然順で並べて返します
#   ]
#   引数: []
#   戻り値: [result: ok・セーブ名の一覧names・除外したフォルダの説明warnings、または保存先を開けない理由（Dictionary）]
# }
func list_profiles() -> Dictionary:
	# 初回起動では保存先フォルダがないため、失敗ではなく「セーブなし」として扱います。
	if not root.is_absolute_path():
		return {"ok": false, "error": "invalid_root", "message": "保存先には絶対パスを指定してください。"}
	if not DirAccess.dir_exists_absolute(root):
		return {"ok": true, "names": [], "warnings": []}
	var directory := DirAccess.open(root)
	if directory == null:
		return {"ok": false, "error": "read_failed", "message": "保存先を開けません: " + root}
	var names: Array[String] = []
	var warnings: Array[String] = []
	# 読込時と同じ検査を通らないフォルダは、一覧へ出しても開けないため除外します。
	for folder in directory.get_directories():
		var profile := resolve_profile(folder)
		if not profile["ok"] or profile["name"] != folder:
			warnings.append("%s: %s" % [folder, profile.get("message", "セーブ名は40文字以内にしてください。")])
		elif FileAccess.file_exists(profile["path"].path_join("state.json")):
			names.append(folder)
	names.sort_custom(func(left: String, right: String): return left.naturalnocasecmp_to(right) < 0)
	return {"ok": true, "names": names, "warnings": warnings}


# {
#   責務: [load_profile: プロファイルを読み込む]
#   処理: [1: プロファイルを読み込む]
#   引数: [name: 名前（String）]
#   戻り値: [result: プロファイルを読み込むための結果（Dictionary）]
# }
func load_profile(name: String) -> Dictionary:
	var profile := resolve_profile(name)
	if not profile["ok"]:
		return profile
	return Documents.read_object(profile["path"].path_join("state.json"))


# {
#   責務: [save_profile: プロファイルを保存する]
#   処理: [1: プロファイルを保存する]
#   引数: [
#     name: 名前（String）
#     value: 値（Dictionary）
#     expected_digest: expected・digest（String）
#     inventory: inventory（Dictionary）
#   ]
#   戻り値: [result: プロファイルを保存するための結果（Dictionary）]
# }
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


# {
#   責務: [_prepare_profile: プロファイルを準備する]
#   処理: [1: プロファイルを準備する]
#   引数: [
#     path: パス（String）
#     name: 名前（String）
#     inventory: inventory（Dictionary）
#   ]
#   戻り値: [result: プロファイルを準備するための結果（Dictionary）]
# }
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
