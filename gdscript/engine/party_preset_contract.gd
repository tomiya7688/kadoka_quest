# {
#   責務: [party_preset_contract: Editable preset documents, portable generated stems and missing-member projection.]
#   フィールド: []
# }
extends RefCounted
## Editable preset documents, portable generated stems and missing-member projection.

const Selection = preload("res://engine/party_selection.gd")
const Individual = preload("res://engine/monster_record_contract.gd")


# {
#   責務: [validate: パーティ・プリセット・契約を妥当性を検査する]
#   処理: [1: パーティ・プリセット・契約を妥当性を検査する]
#   引数: [document: 文書（Dictionary）]
#   戻り値: [result: パーティ・プリセット・契約を妥当性を検査するための結果（Dictionary）]
# }
static func validate(document: Dictionary) -> Dictionary:
	var version: Variant = document.get("schema_version", 1)
	if not (version is int or version is float) or float(version) != 1:
		return {"ok": false, "message": "未対応のプリセット形式です。"}
	if not document.get("name") is String or document["name"].strip_edges().is_empty():
		return {"ok": false, "message": "プリセット名を入力してください。"}
	var draft = Selection.new()
	return draft.start(document.get("members"))


# {
#   責務: [create: パーティ・プリセット・契約を作成する]
#   処理: [1: パーティ・プリセット・契約を作成する]
#   引数: [
#     name: 名前（String）
#     members: 個体一覧（Array）
#   ]
#   戻り値: [result: パーティ・プリセット・契約を作成するための結果（Dictionary）]
# }
static func create(name: String, members: Array) -> Dictionary:
	var document := {"schema_version": 1, "name": name.strip_edges(), "members": members.duplicate(true)}
	var valid := validate(document)
	if not valid["ok"]:
		return valid
	while document["members"].size() < 4:
		document["members"].append(null)
	return {"ok": true, "value": document}


# {
#   責務: [filename_stem: パーティ・プリセット・契約のfilename・stemを求める]
#   処理: [1: パーティ・プリセット・契約のfilename・stemを求める]
#   引数: [name: 名前（String）]
#   戻り値: [result: パーティ・プリセット・契約のfilename・stemを求めるための結果（String）]
# }
static func filename_stem(name: String) -> String:
	var pattern := RegEx.new()
	pattern.compile("[^a-zA-Z0-9_-]+")
	var stem := pattern.sub(name, "_", true).to_lower()
	while stem.begins_with("_"):
		stem = stem.trim_prefix("_")
	while stem.ends_with("_"):
		stem = stem.trim_suffix("_")
	stem = stem.left(80)
	if stem.is_empty():
		stem = "party"
	if not Individual.safe_id(stem + ".json"):
		stem = "party_" + stem
	return stem


# {
#   責務: [project: パーティ・プリセット・契約のprojectを求める]
#   処理: [1: パーティ・プリセット・契約のprojectを求める]
#   引数: [
#     document: 文書（Dictionary）
#     records: 個体レコード一覧（Dictionary）
#   ]
#   戻り値: [result: パーティ・プリセット・契約のprojectを求めるための結果（Dictionary）]
# }
static func project(document: Dictionary, records: Dictionary) -> Dictionary:
	var valid := validate(document)
	if not valid["ok"]:
		return valid
	var members: Array = []
	var warnings: Array = []
	for id in document["members"]:
		if id != null and not records.has(id):
			members.append(null)
			warnings.append("読込できない個体を空き枠にしました: " + str(id))
		else:
			members.append(id)
	var draft = Selection.new()
	draft.start(members)
	valid = draft.validate(records)
	if not valid["ok"]:
		return valid
	return {"ok": true, "members": draft.members.duplicate(true), "warnings": warnings}
