extends RefCounted
## Editable preset documents, portable generated stems and missing-member projection.

const Selection = preload("res://engine/party_selection.gd")
const Individual = preload("res://engine/monster_record_contract.gd")


static func validate(document: Dictionary) -> Dictionary:
	var version: Variant = document.get("schema_version", 1)
	if not (version is int or version is float) or float(version) != 1:
		return {"ok": false, "message": "未対応のプリセット形式です。"}
	if not document.get("name") is String or document["name"].strip_edges().is_empty():
		return {"ok": false, "message": "プリセット名を入力してください。"}
	var draft = Selection.new()
	return draft.start(document.get("members"))


static func create(name: String, members: Array) -> Dictionary:
	var document := {"schema_version": 1, "name": name.strip_edges(), "members": members.duplicate(true)}
	var valid := validate(document)
	if not valid["ok"]:
		return valid
	while document["members"].size() < 4:
		document["members"].append(null)
	return {"ok": true, "value": document}


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
