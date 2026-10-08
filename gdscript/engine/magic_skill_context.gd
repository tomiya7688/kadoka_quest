# {
#   責務: [magic_skill_context: 開始時の習得・許可装備・属性耐性を独立保持し、選択した単体魔法を検証します]
#   フィールド: []
# }
extends RefCounted
const Preparation = preload("res://engine/physical_skill_context.gd")
const Quote = preload("res://engine/magic_skill_contract.gd")
const SelfDamageQuote = preload("res://engine/self_damage_magic_contract.gd")
const Resistance = preload("res://engine/elemental_resistance.gd")
const Numbers = preload("res://engine/stat_numbers.gd")

# {
#   責務: [prepare: 新鮮な両陣営とスキル一覧を検証し、個体別の属性耐性を加えます]
#   処理: [
#     1: 既存の個体・習得・許可装備・ID索引の検証を共用します
#     2: 属性耐性を検証して独立コンテキストへ追加します
#   ]
#   引数: [
#     teams: snapshot・skill_ids・equipment・resistancesを持つ再構築済み両陣営（Variant）
#     skills: schema_version=1のスキル一覧（Variant）
#   ]
#   戻り値: [result: 独立したsnapshotsとcontext、または理由付き拒否（Dictionary）]
# }
static func prepare(teams: Variant, skills: Variant) -> Dictionary:
	# 物理スキル選択は呼ばず、既存の開始情報検証だけを共用して検証規則の重複を避ける。
	var checked := Preparation.prepare(teams, skills)
	if not checked["ok"]:
		return checked
	for side in ["allies", "enemies"]:
		for member: Dictionary in teams[side]:
			var traits := Resistance.validate(member.get("resistances"))
			if not traits["ok"]:
				return traits
			checked["context"]["members"][side][member["snapshot"]["identity"]["id"]]["resistances"] = traits["resistances"]
	return checked

# {
#   責務: [select: 習得済みIDの単体魔法と、魔法計算で利用する装備の固定加算を返します]
#   処理: [
#     1: 習得と選択した定義の一意性・対応範囲を確認します
#     2: 選択IDの未対応装備効果と不正数値を拒否します
#   ]
#   引数: [
#     context: prepareで構築した独立情報（Dictionary）
#     actor: 検証済み行動者のsideとid（Dictionary）
#     skill_id: 使用する魔法ID（Variant）
#     self_damage: trueなら自傷付き、falseなら自傷なしの定義だけを選択する設定（bool）
#   ]
#   戻り値: [result: skillとfixed_bonus_damage、または理由付き拒否（Dictionary）]
# }
static func select(context: Dictionary, actor: Dictionary, skill_id: Variant, self_damage: bool = false) -> Dictionary:
	# 行動要求から習得や装備を上書きさせず、開始時の正規情報だけを使う。
	if not skill_id is String or skill_id.is_empty():
		return {"ok": false, "reason": "invalid_skill_id"}
	if skill_id in ["attack", "defend"]:
		return {"ok": false, "reason": "unsupported_action"}
	var member: Dictionary = context["members"][actor["side"]][actor["id"]]
	if skill_id not in member["skill_ids"]:
		return {"ok": false, "reason": "skill_not_learned"}
	# 固定した区分の検証だけを使い、未対応の自傷効果を通常魔法として黙って無視しない。
	var contract: GDScript = SelfDamageQuote if self_damage else Quote
	var selected: Dictionary = contract.prepare({"schema_version": 1, "skills": context["definitions"].get(skill_id, [])}, skill_id)
	if not selected["ok"]:
		return selected
	var equipment: Dictionary = member["equipment"]
	# 選択した魔法の未対応補正は値が無効でも捨てず、実行前に拒否する。
	var modifier: Variant = equipment.get("skill_modifiers", {}).get(skill_id, {})
	if not modifier is Dictionary:
		return {"ok": false, "reason": "invalid_magic_equipment"}
	for field: Variant in modifier:
		if field != "power_multiplier":
			return {"ok": false, "reason": "unsupported_magic_equipment"}
	# 正本Pythonの魔法は物理用power_multiplierを使わない。既知数値として検証だけ行う。
	var power := Numbers.float_value(modifier.get("power_multiplier", 1.0))
	var bonus := Numbers.integer_value(equipment.get("fixed_bonus_damage", 0))
	if not power["ok"] or not bonus["ok"]:
		return {"ok": false, "reason": "invalid_magic_equipment"}
	return {"ok": true, "skill": selected["skill"], "fixed_bonus_damage": bonus["value"]}
