# {
#   責務: [physical_skill_context: 開始時の個体・習得・許可装備の検証と選択スキルの数値投影]
#   フィールド: []
# }
extends RefCounted
const Quote = preload("res://engine/physical_skill_contract.gd")
const Order = preload("res://engine/turn_order.gd")
const State = preload("res://engine/combatant_state.gd")
const Numbers = preload("res://engine/stat_numbers.gd")
const EQUIPMENT_FIELDS := ["id", "display_name", "description", "category", "allowed_species_ids",
	"stat_multipliers", "resistance_steps", "skill_modifiers", "fixed_bonus_damage"]


# {
#   責務: [prepare: 新鮮な個体・習得・装備とスキル原本を独立コンテキストへ変換する]
#   処理: [
#     1: 両陣営とカタログを検証しID別に索引化する
#     2: 個体を正規化して独立コピーを返す
#   ]
#   引数: [
#     teams: 再構築済み両陣営（Variant）
#     skills: 正規スキル一覧（Variant）
#   ]
#   戻り値: [result: snapshotsとcontextまたは拒否（Dictionary）]
# }
static func prepare(teams: Variant, skills: Variant) -> Dictionary:
	# 未対応定義は削除せず、選択時に個別の対応範囲を確認する。
	if not skills is Dictionary or not skills.get("skills") is Array:
		return _reject("invalid_skill_document")
	var version: Variant = skills.get("schema_version")
	if not (version is int or version is float) or version != 1:
		return _reject("invalid_skill_document")
	if not teams is Dictionary or teams.size() != 2 or not teams.get("allies") is Array or not teams.get("enemies") is Array:
		return _reject("invalid_physical_context")
	# 保有MODスキル数に比例する検索を毎行動に繰り返さず、重複はそのまま検出可能に保持する。
	var definitions: Dictionary = {}
	for definition: Variant in skills["skills"]:
		if definition is Dictionary and definition.get("id") is String:
			var id: String = definition["id"]
			if not definitions.has(id):
				definitions[id] = []
			definitions[id].append(definition)
	var snapshots := {"allies": [], "enemies": []}
	var members := {"allies": {}, "enemies": {}}
	for side in Order.SIDES:
		for member: Variant in teams[side]:
			var checked := _prepare_member(member)
			if not checked["ok"]:
				return checked
			snapshots[side].append(checked["snapshot"])
			members[side][checked["snapshot"]["identity"]["id"]] = checked["member"]
	# 参加数・重複・資源6キーは既存の順序契約と同じ制約で確認する。
	var participants := Order.participants(snapshots["allies"], snapshots["enemies"])
	if not participants["ok"]:
		return participants
	return {"ok": true, "snapshots": snapshots, "context": {"members": members, "definitions": definitions.duplicate(true)}}


# {
#   責務: [_prepare_member: 新鮮な資源と習得・許可装備を検証する]
#   処理: [
#     1: snapshotと習得IDを検証する
#     2: 装備を検証し比較用snapshotを正規化する
#   ]
#   引数: [member: 再構築した個体（Variant）]
#   戻り値: [result: snapshotとmemberまたは拒否（Dictionary）]
# }
static func _prepare_member(member: Variant) -> Dictionary:
	# 習得情報は行動payloadでなく、開始時に受け取る再構築結果へ限定する。
	if not member is Dictionary or not member.get("snapshot") is Dictionary or not member.get("skill_ids") is Array:
		return _reject("invalid_physical_context")
	var snapshot: Dictionary = member["snapshot"]
	var validated := Order.participants([snapshot], [])
	if not validated["ok"]:
		return validated
	for id: Variant in member["skill_ids"]:
		if not id is String or id.is_empty():
			return _reject("invalid_learned_skills")
	if snapshot["hp"] != snapshot["stats"]["hp"] or snapshot["mp"] != snapshot["stats"]["mp"] or snapshot["fled"]:
		return _reject("fresh_physical_context_required")
	var equipment := _equipment(member.get("equipment"), snapshot["identity"]["species_id"])
	if not equipment["ok"]:
		return equipment
	# JSON数値をSessionと同じ整数snapshotへ正規化する。資源の所有は移さない。
	var state = State.new()
	var initialized: Dictionary = state.start(snapshot["identity"], snapshot["stats"])
	if not initialized["ok"]:
		return initialized
	return {"ok": true, "snapshot": state.snapshot(), "member": {
		"skill_ids": member["skill_ids"].duplicate(true), "equipment": equipment["equipment"]}}


# {
#   責務: [_equipment: 非空装備の種族許可と効果の外形を確認する]
#   処理: [1: 未対応効果と不正許可リストを拒否する]
#   引数: [
#     definition: 選択された装備（Variant）
#     species: 装備する種族（String）
#   ]
#   戻り値: [result: equipmentまたは拒否（Dictionary）]
# }
static func _equipment(definition: Variant, species: String) -> Dictionary:
	# 空辞書は再構築済みの未装備・不明ID・装備不可であり、補正を加えない。
	if not definition is Dictionary:
		return _reject("invalid_physical_equipment")
	if definition.is_empty():
		return {"ok": true, "equipment": {}}
	for field: Variant in definition:
		if field not in EQUIPMENT_FIELDS:
			return _reject("unsupported_physical_equipment")
	var allowed: Variant = definition.get("allowed_species_ids")
	if not allowed is Array:
		return _reject("invalid_equipment_permission")
	for id: Variant in allowed:
		if not id is String:
			return _reject("invalid_equipment_permission")
	if species not in allowed:
		return _reject("equipment_not_allowed")
	if not definition.get("skill_modifiers", {}) is Dictionary:
		return _reject("invalid_physical_equipment")
	return {"ok": true, "equipment": definition.duplicate(true)}


# {
#   責務: [select: 習得と正規定義から指定スキルの数値を投影する]
#   処理: [
#     1: 習得と選択定義を検証する
#     2: 選択IDの装備効果だけを投影する
#   ]
#   引数: [
#     context: prepare済み情報（Dictionary）
#     actor: 検証済みsideとid（Dictionary）
#     skill_id: スキルID（Variant）
#   ]
#   戻り値: [result: skillと装備数値または拒否（Dictionary）]
# }
static func select(context: Dictionary, actor: Dictionary, skill_id: Variant) -> Dictionary:
	# 未習得と通常攻撃への偽装を、行動権取得前に区別する。
	if not skill_id is String or skill_id.is_empty():
		return _reject("invalid_skill_id")
	if skill_id in ["attack", "defend"]:
		return _reject("unsupported_action")
	var member: Dictionary = context["members"][actor["side"]][actor["id"]]
	if skill_id not in member["skill_ids"]:
		return _reject("skill_not_learned")
	var selected := Quote.prepare({"schema_version": 1, "skills": context["definitions"].get(skill_id, [])}, skill_id)
	if not selected["ok"]:
		return selected
	# 他IDの補正を流用せず、選択IDの未知効果はfalseや空でも拒否する。
	var definition: Dictionary = member["equipment"]
	var modifier: Variant = definition.get("skill_modifiers", {}).get(skill_id, {})
	if not modifier is Dictionary:
		return _reject("invalid_physical_equipment")
	for field: Variant in modifier:
		if field != "power_multiplier":
			return _reject("unsupported_physical_equipment")
	var power := Numbers.float_value(modifier.get("power_multiplier", 1.0))
	var bonus := Numbers.integer_value(definition.get("fixed_bonus_damage", 0))
	if not power["ok"] or not bonus["ok"]:
		return _reject("invalid_physical_equipment")
	return {"ok": true, "skill": selected["skill"], "equipment": {
		"power_multiplier": power["value"], "fixed_bonus_damage": bonus["value"]}}


# {
#   責務: [_reject: 失敗を判別可能な理由で返す]
#   処理: [1: plainな失敗結果を作る]
#   引数: [reason: 呼出元が扱う理由（String）]
#   戻り値: [result: ok=falseの辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	# 初期化や選択の失敗を呼出側が理由で判別できるようにする。
	return {"ok": false, "reason": reason}
