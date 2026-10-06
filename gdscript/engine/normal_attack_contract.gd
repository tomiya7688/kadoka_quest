# {
#   責務: [normal_attack_contract: Project read-only content into the supported normal-attack context. No state/I/O/AI.]
#   フィールド: []
# }
extends RefCounted
## Project read-only content into the supported normal-attack context. No state/I/O/AI.

const Numbers = preload("res://engine/attack_numbers.gd")
const Order = preload("res://engine/turn_order.gd")
const State = preload("res://engine/combatant_state.gd")
const StatNumbers = preload("res://engine/stat_numbers.gd")
const SKILL_FIELDS := ["id", "display_name", "description", "kind", "power", "mp_cost", "critical_multiplier"]
const EQUIPMENT_FIELDS := ["id", "display_name", "description", "category", "allowed_species_ids",
	"stat_multipliers", "resistance_steps", "skill_modifiers", "fixed_bonus_damage"]


# {
#   責務: [prepare: normal・攻撃・契約を準備する]
#   処理: [1: normal・攻撃・契約を準備する]
#   引数: [
#     teams: 両陣営（Variant）
#     skills: スキル一覧（Variant）
#   ]
#   戻り値: [result: normal・攻撃・契約を準備するための結果（Dictionary）]
# }
static func prepare(teams: Variant, skills: Variant) -> Dictionary:
	var rule := _skill(skills)
	if not rule["ok"]:
		return rule
	if not teams is Dictionary or teams.size() != 2 or not teams.get("allies") is Array or not teams.get("enemies") is Array:
		return _failure("invalid_attack_context")
	var snapshots := {"allies": [], "enemies": []}
	var equipment := {"allies": {}, "enemies": {}}
	for side in Order.SIDES:
		for member: Variant in teams[side]:
			if not member is Dictionary or not member.get("snapshot") is Dictionary:
				return _failure("invalid_attack_context")
			var checked := _equipment(member.get("equipment"))
			if not checked["ok"]:
				return checked
			snapshots[side].append(member["snapshot"])
			var identity: Variant = member["snapshot"].get("identity")
			if not identity is Dictionary or not identity.get("id") is String:
				return _failure("invalid_attack_context")
			equipment[side][identity["id"]] = checked["equipment"]
	var participants := Order.participants(snapshots["allies"], snapshots["enemies"])
	if not participants["ok"]:
		return participants
	# Godot JSON numbers are floats; compare the same canonical integer snapshots as Session.
	for side in Order.SIDES:
		for index in snapshots[side].size():
			var snapshot: Dictionary = snapshots[side][index]
			if snapshot["hp"] != snapshot["stats"]["hp"] or snapshot["mp"] != snapshot["stats"]["mp"] or snapshot["fled"]:
				return _failure("fresh_attack_context_required")
			var state = State.new()
			var initialized: Dictionary = state.start(snapshot["identity"], snapshot["stats"])
			if not initialized["ok"]:
				return initialized
			snapshots[side][index] = state.snapshot()
	return {"ok": true, "skill": rule["skill"], "equipment": equipment, "snapshots": snapshots.duplicate(true)}


# {
#   責務: [_skill: normal・攻撃・契約のスキルを求める]
#   処理: [1: normal・攻撃・契約のスキルを求める]
#   引数: [document: 文書（Variant）]
#   戻り値: [result: normal・攻撃・契約のスキルを求めるための結果（Dictionary）]
# }
static func _skill(document: Variant) -> Dictionary:
	if not document is Dictionary or not document.get("skills") is Array:
		return _failure("invalid_skill_document")
	var version: Variant = document.get("schema_version")
	if not (version is int or version is float) or version != 1:
		return _failure("invalid_skill_document")
	var definitions: Array = []
	for entry: Variant in document["skills"]:
		if entry is Dictionary and entry.get("id") is String and entry["id"] == "attack":
			definitions.append(entry)
	if definitions.size() != 1:
		return _failure("attack_definition_missing_or_duplicate")
	var definition: Dictionary = definitions[0]
	for field: Variant in definition:
		if field not in SKILL_FIELDS:
			return _failure("unsupported_attack_definition")
	var cost := StatNumbers.float_value(definition.get("mp_cost", 0))
	if not cost["ok"] or cost["value"] != 0 or not definition.get("kind") is String or definition["kind"] != "physical":
		return _failure("unsupported_attack_definition")
	var skill := {"power": definition.get("power", 1.0), "critical_multiplier": definition.get("critical_multiplier", 1.0)}
	var checked := validate_numbers(skill, {}, 0.5, 1.0)
	return checked if not checked["ok"] else {"ok": true, "skill": skill.duplicate(true)}


# {
#   責務: [_equipment: normal・攻撃・契約の装備を求める]
#   処理: [1: normal・攻撃・契約の装備を求める]
#   引数: [definition: 定義（Variant）]
#   戻り値: [result: normal・攻撃・契約の装備を求めるための結果（Dictionary）]
# }
static func _equipment(definition: Variant) -> Dictionary:
	if not definition is Dictionary:
		return _failure("invalid_attack_equipment")
	for field: Variant in definition:
		if field not in EQUIPMENT_FIELDS:
			return _failure("unsupported_attack_equipment")
	var modifiers: Variant = definition.get("skill_modifiers", {})
	if not modifiers is Dictionary or not modifiers.get("attack", {}) is Dictionary:
		return _failure("invalid_attack_equipment")
	for field: Variant in modifiers.get("attack", {}):
		if field != "power_multiplier":
			return _failure("unsupported_attack_equipment")
	var equipment := {"skill_modifiers": {"attack": modifiers.get("attack", {}).duplicate(true)},
		"fixed_bonus_damage": definition.get("fixed_bonus_damage", 0)}
	var checked := validate_numbers({}, equipment, 0.5, 1.0)
	return checked if not checked["ok"] else {"ok": true, "equipment": equipment}


# {
#   責務: [validate_numbers: numbersを妥当性を検査する]
#   処理: [1: numbersを妥当性を検査する]
#   引数: [
#     skill: スキル（Dictionary）
#     equipment: 装備（Dictionary）
#     roll: roll（Variant）
#     variance: ダメージの揺らぎ（Variant）
#   ]
#   戻り値: [result: numbersを妥当性を検査するための結果（Dictionary）]
# }
static func validate_numbers(skill: Dictionary, equipment: Dictionary, roll: Variant, variance: Variant) -> Dictionary:
	return Numbers.normal_attack({"attack": 1, "defense": 0, "target_hp": 1, "equipment": equipment,
		"power": skill.get("power", 1.0), "critical_multiplier": skill.get("critical_multiplier", 1.0),
		"critical_roll": roll, "variance": variance})


# {
#   責務: [_failure: normal・攻撃・契約のfailureを求める]
#   処理: [1: normal・攻撃・契約のfailureを求める]
#   引数: [reason: 理由（String）]
#   戻り値: [result: normal・攻撃・契約のfailureを求めるための結果（Dictionary）]
# }
static func _failure(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
