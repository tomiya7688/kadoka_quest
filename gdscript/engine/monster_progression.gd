# {
#   責務: [monster_progression: Read explicit level rows and ordered learnsets. Plain values, no I/O or final modifiers.]
#   フィールド: []
# }
extends RefCounted
## Read explicit level rows and ordered learnsets. Plain values, no I/O or final modifiers.

const STAT_KEYS := ["attack", "defense", "speed", "magic", "hp", "mp"]
const Numbers = preload("res://engine/stat_numbers.gd")


# {
#   責務: [rebuild: モンスター・progressionのrebuildを求める]
#   処理: [1: モンスター・progressionのrebuildを求める]
#   引数: [
#     stats_document: 能力値・文書（Variant）
#     skills_document: スキル一覧・文書（Variant）
#     level: レベル（Variant）
#   ]
#   戻り値: [result: モンスター・progressionのrebuildを求めるための結果（Dictionary）]
# }
static func rebuild(stats_document: Variant, skills_document: Variant, level: Variant = 1) -> Dictionary:
	if not _supported_document(stats_document) or not _supported_document(skills_document):
		return _failure("能力値/スキルのJSONオブジェクトまたはschemaが不正です")
	var converted := _integer(level)
	if not converted["ok"]:
		return _failure("レベルを整数に変換できません")
	var requested_level: int = converted["value"]
	var stats_level := clampi(requested_level, 1, 100)
	var stats := _stats_at(stats_document, stats_level)
	if not stats["ok"]:
		return stats
	var skills := _skills_at(skills_document, requested_level)
	if not skills["ok"]:
		return skills
	return {"ok": true, "level": requested_level, "stats_level": stats_level,
		"stats": stats["value"], "skill_ids": skills["value"], "scope": "level_base",
		"modifiers_applied": false, "unimplemented_modifiers": ["plus", "equipment"]}


# {
#   責務: [_stats_at: モンスター・progressionの能力値・atを求める]
#   処理: [1: モンスター・progressionの能力値・atを求める]
#   引数: [
#     document: 文書（Dictionary）
#     level: レベル（int）
#   ]
#   戻り値: [result: モンスター・progressionの能力値・atを求めるための結果（Dictionary）]
# }
static func _stats_at(document: Dictionary, level: int) -> Dictionary:
	var levels: Variant = document.get("levels")
	if not levels is Dictionary or not levels.get(str(level)) is Dictionary:
		return _failure("Lv.%dの明示能力値がありません（成長式への自動補完なし）" % level)
	var values: Dictionary = levels[str(level)]
	var stats: Dictionary = {}
	for key: String in STAT_KEYS:
		var converted := _integer(values.get(key))
		if not converted["ok"]:
			return _failure("Lv.%dの%sを整数に変換できません" % [level, key])
		stats[key] = converted["value"]
	return {"ok": true, "value": stats}


# {
#   責務: [_skills_at: モンスター・progressionのスキル一覧・atを求める]
#   処理: [1: モンスター・progressionのスキル一覧・atを求める]
#   引数: [
#     document: 文書（Dictionary）
#     level: レベル（int）
#   ]
#   戻り値: [result: モンスター・progressionのスキル一覧・atを求めるための結果（Dictionary）]
# }
static func _skills_at(document: Dictionary, level: int) -> Dictionary:
	var learnset: Variant = document.get("learnset", [])
	if not learnset is Array:
		return _failure("learnsetは配列です")
	var learned: Array = []
	for entry in learnset:
		if not entry is Dictionary:
			return _failure("learnsetの要素はオブジェクトです")
		var threshold := _integer(entry.get("level", 1))
		if not threshold["ok"] or not entry.get("skill_id") is String or entry["skill_id"].is_empty():
			return _failure("習得レベルまたはskill_idが不正です")
		if threshold["value"] <= level and entry["skill_id"] not in learned:
			learned.append(entry["skill_id"])
	return {"ok": true, "value": learned}


# {
#   責務: [_supported_document: モンスター・progressionのsupported・文書を求める]
#   処理: [1: モンスター・progressionのsupported・文書を求める]
#   引数: [value: 値（Variant）]
#   戻り値: [result: モンスター・progressionのsupported・文書を求めるための結果（bool）]
# }
static func _supported_document(value: Variant) -> bool:
	if not value is Dictionary:
		return false
	var version: Variant = value.get("schema_version", 1)
	return (version is int or version is float) and float(version) == 1.0


# {
#   責務: [_integer: モンスター・progressionのintegerを求める]
#   処理: [1: モンスター・progressionのintegerを求める]
#   引数: [value: 値（Variant）]
#   戻り値: [result: モンスター・progressionのintegerを求めるための結果（Dictionary）]
# }
static func _integer(value: Variant) -> Dictionary:
	return Numbers.integer_value(value)


# {
#   責務: [_failure: モンスター・progressionのfailureを求める]
#   処理: [1: モンスター・progressionのfailureを求める]
#   引数: [message: message（String）]
#   戻り値: [result: モンスター・progressionのfailureを求めるための結果（Dictionary）]
# }
static func _failure(message: String) -> Dictionary:
	return {"ok": false, "error": "invalid_progression", "message": message}
