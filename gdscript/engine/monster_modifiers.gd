extends RefCounted
## Ordered plus effects, equipment whitelist, and final six-stat clamp. No I/O or battle rules.

const Base = preload("res://engine/monster_progression.gd")
const Numbers = preload("res://engine/stat_numbers.gd")


static func apply(base: Dictionary, plus: Variant, equipment: Variant, monster: Dictionary) -> Dictionary:
	if not base.get("ok", false) or not base.get("stats") is Dictionary or not base.get("skill_ids") is Array:
		return _failure("基礎能力値/習得スキルがありません")
	if not monster.get("species_id") is String or monster["species_id"].is_empty():
		return _failure("種族IDが不正です")
	var choices: Variant = monster.get("plus_choices", [])
	if not choices is Array:
		return _failure("＋選択は配列です")
	for choice in choices:
		if not choice is String:
			return _failure("＋選択IDは文字列です")
	var stats: Dictionary = {}
	for key: String in Base.STAT_KEYS:
		var value := Numbers.integer_value(base["stats"].get(key))
		if not value["ok"]:
			return _failure("基礎能力値が不正です: " + key)
		stats[key] = value["value"]
	var skills: Array = []
	for id in base["skill_ids"]:
		if not id is String or id.is_empty():
			return _failure("基礎スキルIDが不正です")
		if id not in skills:
			skills.append(id)
	var changed := _apply_plus(stats, skills, plus, choices)
	if not changed["ok"]:
		return changed
	var selected := _select_equipment(equipment, monster.get("equipment_id"), monster["species_id"])
	if not selected["ok"]:
		return selected
	var equipment_stats := _apply_equipment(stats, selected["definition"])
	if not equipment_stats["ok"]:
		return equipment_stats
	var notes: Array = changed["warnings"] + selected["warnings"] + equipment_stats["warnings"]
	for key: String in Base.STAT_KEYS:
		stats[key] = maxi(1, stats[key])
	return {"ok": true, "stats": stats, "skill_ids": skills, "scope": "stats_with_modifiers",
		"modifiers_applied": true, "unimplemented_modifiers": [], "warnings": notes,
		"equipment_status": selected["status"], "equipment": selected["definition"].duplicate(true)}


static func _apply_plus(stats: Dictionary, skills: Array, document: Variant, choices: Array) -> Dictionary:
	if not _supported(document) or not document.get("stages", []) is Array:
		return _failure("＋定義のschema/stagesが不正です")
	var known: Dictionary = {}
	var selected: Dictionary = {}
	var notes: Array = []
	for choice: String in choices:
		selected[choice] = true
	for stage in document.get("stages", []):
		if not stage is Dictionary or not stage.get("options", []) is Array:
			return _failure("＋定義のstage/optionsが不正です")
		for option in stage.get("options", []):
			if not option is Dictionary or not option.get("id") is String or option["id"].is_empty():
				return _failure("＋定義の選択肢IDが不正です")
			known[option["id"]] = true
			if not selected.has(option["id"]):
				continue
			var result := _apply_option(stats, skills, option)
			if not result["ok"]:
				return result
			notes.append_array(result.get("warnings", []))
	for id: String in selected:
		if not known.has(id):
			notes.append("不明な＋選択ID（補正なし・IDは保持）: " + id)
	return {"ok": true, "warnings": notes}


static func _apply_option(stats: Dictionary, skills: Array, option: Dictionary) -> Dictionary:
	var kind: Variant = option.get("kind")
	if kind == "skill":
		if not option.get("skill_id") is String or option["skill_id"].is_empty():
			return _failure("＋スキルIDが不正です: " + option["id"])
		if option["skill_id"] not in skills:
			skills.append(option["skill_id"])
	elif kind in ["stat_add", "stat_multiplier"]:
		var stat: Variant = option.get("stat")
		if stat not in Base.STAT_KEYS:
			return {"ok": true, "warnings": ["＋の対象能力値が不明（補正なし）: " + option["id"]]}
		var value: Dictionary
		if kind == "stat_add":
			value = Numbers.integer_value(option.get("value", 0))
			if value["ok"]:
				value = Numbers.integer_value(stats[stat] + value["value"])
		else:
			value = Numbers.float_value(option.get("value", 1.0))
			if value["ok"]:
				value = Numbers.rounded_integer(stats[stat] * value["value"])
		if not value["ok"]:
			return _failure("＋補正値が不正/精度超過です: " + option["id"])
		stats[stat] = value["value"]
	else:
		return {"ok": true, "warnings": ["未対応の＋効果（能力値/スキル補正なし）: " + option["id"]]}
	return {"ok": true}


static func _select_equipment(document: Variant, id: Variant, species: String) -> Dictionary:
	if not _supported(document) or not document.get("equipment") is Array:
		return _failure("装備定義のschema/equipmentが不正です")
	var catalog: Dictionary = {}
	for entry in document["equipment"]:
		if not entry is Dictionary or not entry.get("id") is String or entry["id"].is_empty():
			return _failure("装備定義のIDが不正です")
		catalog[entry["id"]] = entry  # Python dict construction also keeps the last duplicate definition.
	if id != null and not id is String:
		return _failure("個体の装備IDは文字列またはnullです")
	var reason := "none"
	var definition: Dictionary = {}
	var notes: Array = []
	if id != null and not id.is_empty():
		if not catalog.has(id):
			reason = "unknown_id"
			notes.append("不明な装備ID（補正なし・IDは保持）: " + id)
		else:
			var allowed: Variant = catalog[id].get("allowed_species_ids", [])
			if not allowed is Array:
				return _failure("装備の許可種族リストが不正です: " + id)
			for value in allowed:
				if not value is String:
					return _failure("装備の許可種族IDは文字列です: " + id)
			if species in allowed:
				reason = "applied"
				definition = catalog[id]
			else:
				reason = "not_allowed"
				notes.append("装備不可の種族（補正なし・IDは保持）: " + id + " / " + species)
	return {"ok": true, "definition": definition, "warnings": notes,
		"status": {"requested_id": id, "applied": reason == "applied", "reason": reason}}


static func _apply_equipment(stats: Dictionary, definition: Dictionary) -> Dictionary:
	var multipliers: Variant = definition.get("stat_multipliers", {})
	if not multipliers is Dictionary:
		return _failure("装備の能力倍率はオブジェクトです")
	var notes: Array = []
	for stat in multipliers:
		if stat not in Base.STAT_KEYS:
			notes.append("装備の対象能力値が不明（補正なし）: " + str(stat))
			continue
		var value := Numbers.float_value(multipliers[stat])
		if value["ok"]:
			value = Numbers.rounded_integer(stats[stat] * value["value"])
		if not value["ok"]:
			return _failure("装備の能力倍率が不正/精度超過です: " + str(stat))
		stats[stat] = value["value"]
	return {"ok": true, "warnings": notes}


static func _supported(document: Variant) -> bool:
	if not document is Dictionary:
		return false
	var version: Variant = document.get("schema_version", 1)
	return (version is int or version is float) and float(version) == 1.0


static func _failure(message: String) -> Dictionary:
	return {"ok": false, "error": "invalid_modifiers", "message": message}
