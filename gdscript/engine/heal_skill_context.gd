# {
#   責務: [heal_skill_context: 開始時の習得・許可装備・定義を検証し、使用する単体HP回復スキルを選びます]
#   フィールド: []
# }
extends RefCounted
const Preparation = preload("res://engine/physical_skill_context.gd")
const Quote = preload("res://engine/heal_skill_contract.gd")
const Numbers = preload("res://engine/stat_numbers.gd")

# {
#   責務: [prepare: 満HP/MPで開始する両陣営と習得・許可装備・スキル一覧の独立コピーを作ります]
#   処理: [1: 共用の開始情報検証へ委譲し、定義のID別索引と個体別情報を取得します]
#   引数: [
#     teams: snapshot・skill_ids・equipmentを持つ再構築済みのallies/enemies（Variant）
#     skills: schema_version=1とskills配列を持つスキル一覧（Variant）
#   ]
#   戻り値: [result: 独立したsnapshotsとcontext、または理由付き拒否（Dictionary）]
# }
static func prepare(teams: Variant, skills: Variant) -> Dictionary:
	# 回復は属性耐性を使わず、物理スキルの数値選択ではなく開始情報の検証だけを共用します。
	return Preparation.prepare(teams, skills)

# {
#   責務: [select: 行動者が習得した単体HP回復の定義を選び、選択IDの装備効果を検証します]
#   処理: [
#     1: 習得済みIDの定義が一意で、HP回復だけの対応範囲に収まるか確認します
#     2: 未知の装備効果を拒否し、既知の攻撃用数値は検証だけ行います
#   ]
#   引数: [
#     context: prepareで作った独立した個体情報と定義のID別索引（Dictionary）
#     actor: 現在の予約で検証済みの行動者のsideとid（Dictionary）
#     skill_id: 使用を要求する回復スキルの文字列ID（Variant）
#   ]
#   戻り値: [result: 独立した検証済みskill、または理由付き拒否（Dictionary）]
# }
static func select(context: Dictionary, actor: Dictionary, skill_id: Variant) -> Dictionary:
	# 行動要求から習得情報や定義を上書きせず、開始時に固定した情報だけを使います。
	if not skill_id is String or skill_id.is_empty():
		return {"ok": false, "reason": "invalid_skill_id"}
	if skill_id in ["attack", "defend"]:
		return {"ok": false, "reason": "unsupported_action"}
	var member: Dictionary = context["members"][actor["side"]][actor["id"]]
	if skill_id not in member["skill_ids"]:
		return {"ok": false, "reason": "skill_not_learned"}
	var selected := Quote.prepare({"schema_version": 1, "skills": context["definitions"].get(skill_id, [])}, skill_id)
	if not selected["ok"]:
		return selected
	var equipment: Dictionary = member["equipment"]
	var modifier: Variant = equipment.get("skill_modifiers", {}).get(skill_id, {})
	if not modifier is Dictionary:
		return {"ok": false, "reason": "invalid_heal_equipment"}
	# 未実装の回復補正をfalse・0・空でも捨てず、選択したIDの行動を拒否します。
	for field: Variant in modifier:
		if field != "power_multiplier":
			return {"ok": false, "reason": "unsupported_heal_equipment"}
	# Python正本の回復は攻撃用の倍率・固定加算を使いません。既知数値の不正だけを拒否します。
	var power := Numbers.float_value(modifier.get("power_multiplier", 1.0))
	var bonus := Numbers.integer_value(equipment.get("fixed_bonus_damage", 0))
	if not power["ok"] or not bonus["ok"]:
		return {"ok": false, "reason": "invalid_heal_equipment"}
	return selected
