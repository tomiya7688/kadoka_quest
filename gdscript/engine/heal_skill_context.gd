# {
#   責務: [heal_skill_context: 回復の開始情報・習得・許可装備を共用検証し、専用入口ごとの回復定義を選びます]
#   フィールド: []
# }
extends RefCounted
const Preparation = preload("res://engine/physical_skill_context.gd")
const Quote = preload("res://engine/heal_skill_contract.gd")
const CureQuote = preload("res://engine/cure_heal_skill_contract.gd")
const Order = preload("res://engine/turn_order.gd")
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
#   処理: [1: 共用の習得/装備検証へ、治療付き定義を拒否するHP回復契約を指定します]
#   引数: [
#     context: prepareで作った独立した個体情報と定義のID別索引（Dictionary）
#     actor: 現在の予約で検証済みの行動者のsideとid（Dictionary）
#     skill_id: 使用を要求する回復スキルの文字列ID（Variant）
#   ]
#   戻り値: [result: 独立した検証済みskill、または理由付き拒否（Dictionary）]
# }
static func select(context: Dictionary, actor: Dictionary, skill_id: Variant) -> Dictionary:
	return _select(context, actor, skill_id, Quote)


# {
#   責務: [select_cure_heal: 習得済みの治療付き回復定義を、HP回復と共用の装備検証で選びます]
#   処理: [1: 共用の習得/装備検証へ、治療確率を必須にする専用定義契約を指定します]
#   引数: [
#     context: prepareの個体情報と定義索引。開始情報の原本とは独立しています（Variant）
#     actor: 選択する参加者のsideとidだけを持つ辞書（Variant）
#     skill_id: 選択を要求する治療付き回復スキルID（Variant）
#   ]
#   戻り値: [result: 独立した検証済みskill、または理由付き拒否。HP/MPは変更しません（Dictionary）]
# }
static func select_cure_heal(context: Variant, actor: Variant, skill_id: Variant) -> Dictionary:
	return _select(context, actor, skill_id, CureQuote)


# {
#   責務: [_select: 開始情報の習得と選択IDの装備効果を検証し、指定された回復契約へ定義検証を委譲します]
#   処理: [
#     1: 開始情報・参加者・習得済みIDを確認し、専用契約で一意な定義を選びます
#     2: 未知装備効果と不正な攻撃用数値を拒否し、回復の検証済み定義だけを返します
#   ]
#   引数: [
#     context: 開始情報の個体別索引と定義索引（Variant）
#     actor: 陣営sideと個体idで指定する参加者（Variant）
#     skill_id: 選択する回復スキルID（Variant）
#     definition_contract: HP回復または治療付き回復の専用定義検証スクリプト。公開要求から指定しません（GDScript）
#   ]
#   戻り値: [result: 独立skill、または資源と開始情報を保持した拒否（Dictionary）]
# }
static func _select(context: Variant, actor: Variant, skill_id: Variant, definition_contract: GDScript) -> Dictionary:
	# 行動要求から習得情報や定義を上書きせず、開始時に固定した情報だけを使います。
	if not context is Dictionary or not context.get("members") is Dictionary or not context.get("definitions") is Dictionary:
		return {"ok": false, "reason": "invalid_heal_context"}
	if not Order.valid_key(actor):
		return {"ok": false, "reason": "invalid_actor_key"}
	var side: Variant = context["members"].get(actor["side"])
	if not side is Dictionary or not side.get(actor["id"]) is Dictionary:
		return {"ok": false, "reason": "actor_missing"}
	if not skill_id is String or skill_id.is_empty():
		return {"ok": false, "reason": "invalid_skill_id"}
	if skill_id in ["attack", "defend"]:
		return {"ok": false, "reason": "unsupported_action"}
	var member: Dictionary = side[actor["id"]]
	if not member.get("skill_ids") is Array or not member.get("equipment") is Dictionary:
		return {"ok": false, "reason": "invalid_heal_context"}
	if skill_id not in member["skill_ids"]:
		return {"ok": false, "reason": "skill_not_learned"}
	var selected: Dictionary = definition_contract.prepare({"schema_version": 1, "skills": context["definitions"].get(skill_id, [])}, skill_id)
	if not selected["ok"]:
		return selected
	var equipment: Dictionary = member["equipment"]
	var modifiers: Variant = equipment.get("skill_modifiers", {})
	if not modifiers is Dictionary:
		return {"ok": false, "reason": "invalid_heal_equipment"}
	var modifier: Variant = modifiers.get(skill_id, {})
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
