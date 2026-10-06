# {
#   責務: [basic_defend_contract: 正規skillsから基本defendだけを検証する純粋契約。I/Oや特殊防御を扱わない]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/attack_numbers.gd")
const StatNumbers = preload("res://engine/stat_numbers.gd")
const FIELDS := ["id", "display_name", "description", "kind", "damage_multiplier", "mp_cost"]


# {
#   責務: [prepare: 一意な基本ぼうぎょ定義を有限の倍率へ変換する]
#   処理: [
#     1: schemaとdefendの一意性を確認する
#     2: 未対応効果と非ゼロMPを拒否する
#     3: 正本と同じ既定0.5の倍率を検証する
#   ]
#   引数: [document: 読み取り専用skills文書（Variant）]
#   戻り値: [result: ok/guardまたはreason付き失敗（Dictionary）]
# }
static func prepare(document: Variant) -> Dictionary:
	if not document is Dictionary or document.size() != 2 or not document.get("skills") is Array:
		return _failure("invalid_skill_document")
	var version: Variant = document.get("schema_version")
	if not (version is int or version is float) or version != 1:
		return _failure("invalid_skill_document")
	var found: Array = []
	for entry: Variant in document["skills"]:
		if entry is Dictionary and entry.get("id") is String and entry["id"] == "defend":
			found.append(entry)
	if found.size() != 1:
		return _failure("defend_definition_missing_or_duplicate")
	var definition: Dictionary = found[0]
	for field: Variant in definition:
		if field not in FIELDS:
			return _failure("unsupported_defend_definition")
	for field in ["display_name", "description"]:
		if definition.has(field) and not definition[field] is String:
			return _failure("invalid_defend_metadata")
	var cost := StatNumbers.float_value(definition.get("mp_cost", 0))
	if not cost["ok"] or cost["value"] != 0 or not definition.get("kind") is String or definition["kind"] != "defend":
		return _failure("unsupported_defend_definition")
	return Numbers.defend_multiplier(definition)


# {
#   責務: [_failure: 定義を変更せず拒否理由を返す]
#   処理: [1: plainな失敗辞書を作る]
#   引数: [reason: 拒否理由（String）]
#   戻り値: [result: ok=falseとreason（Dictionary）]
# }
static func _failure(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
