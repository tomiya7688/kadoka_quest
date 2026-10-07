# {
#   責務: [elemental_resistance: 種族の属性耐性へ許可済み装備の耐性段階を加え、戦闘用の独立辞書を作ります]
#   フィールド: []
# }
extends RefCounted
const Numbers = preload("res://engine/stat_numbers.gd")
const SCALE := ["weak", "normal", "strong", "immune", "absorb"]

# {
#   責務: [prepare: 種族と許可済み装備から属性耐性を再構築します]
#   処理: [
#     1: 耐性辞書と段階補正の形式を検証します
#     2: 補正を段階表の範囲へ丸めて独立コピーへ反映します
#   ]
#   引数: [
#     species: 正規種族定義（Variant）
#     equipment: 種族許可を確認済みの装備定義または未装備の空辞書（Variant）
#   ]
#   戻り値: [result: ok=trueとresistances、またはok=falseとreason（Dictionary）]
# }
static func prepare(species: Variant, equipment: Variant) -> Dictionary:
	# ＋選択は正本Pythonでも属性耐性を変更しないため、ここでは装備補正だけを適用する。
	if not species is Dictionary or not equipment is Dictionary:
		return {"ok": false, "reason": "invalid_resistance_definition"}
	var base := validate(species.get("resistances", {}))
	if not base["ok"]:
		return base
	var steps: Variant = equipment.get("resistance_steps", {})
	if not steps is Dictionary:
		return {"ok": false, "reason": "invalid_resistance_steps"}
	var resistances: Dictionary = base["resistances"]
	# 不明な耐性名は補正時だけnormalを基準にし、未補正の名前は予測の既知判定用に保持する。
	for element: Variant in steps:
		if not element is String or element.is_empty():
			return {"ok": false, "reason": "invalid_resistance_steps"}
		var amount := Numbers.integer_value(steps[element])
		if not amount["ok"]:
			return {"ok": false, "reason": "invalid_resistance_steps"}
		var index := SCALE.find(resistances.get(element, "normal"))
		if index < 0:
			index = 1
		resistances[element] = SCALE[clampi(index + amount["value"], 0, SCALE.size() - 1)]
	return {"ok": true, "resistances": resistances}

# {
#   責務: [validate: 属性名と耐性名が文字列の辞書を検証し、独立コピーを返します]
#   処理: [1: 不正なキー・値を拒否し、未知の文字列耐性はそのまま保持します]
#   引数: [value: 戦闘へ渡す属性耐性辞書（Variant）]
#   戻り値: [result: ok=trueとresistances、または理由付き拒否（Dictionary）]
# }
static func validate(value: Variant) -> Dictionary:
	# 空辞書は全属性の省略を表し、魔法予測ではnormalとして扱う。
	if not value is Dictionary:
		return {"ok": false, "reason": "invalid_resistances"}
	for element: Variant in value:
		if not element is String or element.is_empty() or not value[element] is String:
			return {"ok": false, "reason": "invalid_resistances"}
	return {"ok": true, "resistances": value.duplicate(true)}
