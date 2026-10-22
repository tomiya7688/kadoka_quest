# {
#   責務: [monster_modifiers: Ordered plus effects, equipment whitelist, and final six-stat clamp. No I/O or battle rules.]
#   フィールド: []
# }
extends RefCounted
## Ordered plus effects, equipment whitelist, and final six-stat clamp. No I/O or battle rules.

const Base = preload("res://engine/monster_progression.gd")
const Numbers = preload("res://engine/stat_numbers.gd")


# {
#   責務: [apply: 基礎能力値と習得スキルへ選択済みの＋効果と許可装備を順に反映した独立結果を返します]
#   処理: [1: 基礎値と個体の選択を検証し、＋補正・装備選択・装備補正の後に六能力値を最低1へ制限します]
#   引数: [
#     base: 基礎能力値再構築に成功したstats/skill_idsを持つ結果（Dictionary）
#     plus: schema_version/stagesを持つ種族の＋定義文書（Variant）
#     equipment: schema_version/equipmentを持つ装備一覧文書（Variant）
#     monster: species_id/plus_choices/equipment_idを持つ対象個体の記録（Dictionary）
#   ]
#   戻り値: [result: 補正済みstats/skill_ids・装備選択結果・警告、または理由付き失敗（Dictionary）]
# }
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


# {
#   責務: [_apply_plus: 選択IDの重複を除き、定義の宣言順で＋効果を作業用の能力値とスキルへ反映します]
#   処理: [1: 選択済み定義を_apply_optionへ渡し、不明な選択IDは元記録を消さず警告として返します]
#   引数: [
#     stats: 呼出元が原本から分離した更新対象の六能力値（Dictionary）
#     skills: 呼出元が原本から分離した更新対象の習得スキルID一覧（Array）
#     document: stages内に選択肢定義を持つ＋定義文書（Variant）
#     choices: 個体が選択した＋効果のID一覧（Array）
#   ]
#   戻り値: [result: 成功と警告、または定義不正の失敗。成功前の作業用更新は呼出元だけが保持します（Dictionary）]
# }
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


# {
#   責務: [_apply_option: 一つの＋定義に従いスキル追加または能力値の加算・倍率補正を作業用データへ反映します]
#   処理: [1: kindを判別し、重複しないスキル追加・整数加算・偶数丸めの倍率補正を行い、未知効果は警告にします]
#   引数: [
#     stats: 呼出元が所有する補正対象の六能力値（Dictionary）
#     skills: 呼出元が所有する追加対象の習得スキルID一覧（Array）
#     option: 選択されたid/kindと効果別の値を持つ＋定義（Dictionary）
#   ]
#   戻り値: [result: 成功と任意警告、または値不正/精度超過の失敗（Dictionary）]
# }
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


# {
#   責務: [_select_equipment: 個体の装備IDと装備側の許可種族一覧から、補正に使える定義と不適用理由を選びます]
#   処理: [1: 一覧をID索引へ変換し、未装備・不明ID・種族不許可・適用可能を区別します]
#   引数: [
#     document: schema_version/equipmentを持つ装備一覧文書。同IDは最後の定義を採用します（Variant）
#     id: 個体が記録した装備ID。nullまたは空文字列は未装備です（Variant）
#     species: 装備可否を判定する対象個体の種族ID（String）
#   ]
#   戻り値: [result: definition/warnings/statusを持つ選択結果、または形式不正の失敗。元個体の装備IDは変更しません（Dictionary）]
# }
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


# {
#   責務: [_apply_equipment: 装備を適用する]
#   処理: [1: 装備を適用する]
#   引数: [
#     stats: 能力値（Dictionary）
#     definition: 定義（Dictionary）
#   ]
#   戻り値: [result: 装備を適用するための結果（Dictionary）]
# }
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


# {
#   責務: [_supported: モンスター・modifiersのsupportedを求める]
#   処理: [1: モンスター・modifiersのsupportedを求める]
#   引数: [document: 文書（Variant）]
#   戻り値: [result: モンスター・modifiersのsupportedを求めるための結果（bool）]
# }
static func _supported(document: Variant) -> bool:
	if not document is Dictionary:
		return false
	var version: Variant = document.get("schema_version", 1)
	return (version is int or version is float) and float(version) == 1.0


# {
#   責務: [_failure: モンスター・modifiersのfailureを求める]
#   処理: [1: モンスター・modifiersのfailureを求める]
#   引数: [message: message（String）]
#   戻り値: [result: モンスター・modifiersのfailureを求めるための結果（Dictionary）]
# }
static func _failure(message: String) -> Dictionary:
	return {"ok": false, "error": "invalid_modifiers", "message": message}
