# {
#   責務: [magic_numbers: 魔力・威力・属性耐性・揺らぎから単体魔法のHP変化を予測します。入力は変更しません]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
const AttackNumbers = preload("res://engine/attack_numbers.gd")
const RESISTANCE_MULTIPLIERS := {"absorb": -0.5, "immune": 0.0, "strong": 0.6, "normal": 1.0, "weak": 1.4}


# {
#   責務: [predict: 検証済み数値からダメージ・無効・吸収回復を分けて予測します]
#   処理: [
#     1: 入力数値と対象資源を検証します
#     2: 選択属性の耐性を解決します
#     3: 耐性別のHP変化を計算します
#   ]
#   引数: [request: magic/power/element/target_hp/target_max_hp/varianceと任意の耐性・装備追加値を持つ辞書（Dictionary）]
#   戻り値: [result: HP予測と耐性の観測値、またはok=falseとreason（Dictionary）]
# }
static func predict(request: Dictionary) -> Dictionary:
	# 上位契約と分離し、HP計算へMP支払い・乱数生成・保存を持ち込まない。
	var values := _validate_numbers(request)
	if not values["ok"]:
		return values
	var resistances: Variant = request.get("target_resistances", {})
	var element: Variant = request.get("element")
	if not resistances is Dictionary or not element is String or element.is_empty():
		return _reject("invalid_magic_resistance")
	var resistance: Variant = resistances.get(element, "normal")
	if not resistance is String:
		return _reject("invalid_magic_resistance")
	# 未知の耐性文字列はPython互換の等倍へフォールバックし、既知かどうかも公開する。
	var multiplier: float = RESISTANCE_MULTIPLIERS.get(resistance, 1.0)
	var raw := Numbers.integer_value(values["magic"] * values["power"] * multiplier)
	if not raw["ok"]:
		return _reject("invalid_magic_numbers")
	var result: Dictionary
	if resistance == "immune":
		# 無効時は揺らぎと装備追加値を適用せず、対象HPを保持する。
		result = {"ok": true, "effect": "immune", "damage": 0, "dealt": 0,
			"healed": 0, "remaining_hp": values["target_hp"], "raw_damage": 0}
	elif resistance == "absorb":
		result = _predict_absorption(values, raw["value"])
	else:
		# 魔法には防御倍率を掛けず、整数化後の装備追加値を通常ダメージへだけ足す。
		var combined := Numbers.integer_value(float(raw["value"]) + values["fixed_bonus_damage"])
		if not combined["ok"]:
			return _reject("invalid_magic_numbers")
		result = AttackNumbers.finish_damage({"kind": "magic", "damage": combined["value"],
			"guard": 1.0, "variance": values["variance"], "target_hp": values["target_hp"]})
		if not result["ok"]:
			return _reject("invalid_magic_numbers")
		result.merge({"effect": "damage", "healed": 0}, true)
	if not result["ok"]:
		return result
	# 防御状態にかかわらず魔法の適用倍率は1。会心・物理防御力は使わない。
	result.merge({"resistance_kind": resistance, "resistance_multiplier": multiplier,
		"resistance_known": RESISTANCE_MULTIPLIERS.has(resistance), "element": element,
		"applied_guard": 1.0, "variance": values["variance"]}, true)
	return result


# {
#   責務: [_validate_numbers: 有限数値・揺らぎ範囲・対象HPの整合性を検証します]
#   処理: [
#     1: 魔力と装備追加値を整数化します
#     2: 威力と揺らぎを検証します
#     3: 現在HPと最大HPを検証します
#   ]
#   引数: [request: 魔法ダメージ予測へ渡す数値辞書（Dictionary）]
#   戻り値: [result: 正規化した数値、または理由付き拒否（Dictionary）]
# }
static func _validate_numbers(request: Dictionary) -> Dictionary:
	# bool・非有限値・精度上限超過は暗黙に数値へ変換しない。
	var result := {"ok": true}
	for field in ["magic", "fixed_bonus_damage"]:
		var checked := Numbers.integer_value(request.get(field, 0 if field == "fixed_bonus_damage" else null))
		if not checked["ok"]:
			return _reject("invalid_magic_numbers")
		result[field] = checked["value"]
	for field in ["power", "variance", "guard"]:
		var checked := Numbers.float_value(request.get(field, 1.0 if field == "guard" else null))
		if not checked["ok"]:
			return _reject("invalid_magic_numbers")
		result[field] = checked["value"]
	if result["variance"] < 0.92 or result["variance"] > 1.08:
		return _reject("invalid_magic_numbers")
	# 資源の小数切捨てで不正なHPを隠さず、最大HP以上への回復を禁止する。
	for field in ["target_hp", "target_max_hp"]:
		var value: Variant = request.get(field)
		var checked := Numbers.integer_value(value)
		if not (value is int or value is float) or not checked["ok"] or checked["value"] != value:
			return _reject("invalid_target_hp")
		result[field] = checked["value"]
	if result["target_max_hp"] <= 0 or result["target_hp"] < 0 or result["target_hp"] > result["target_max_hp"]:
		return _reject("invalid_target_hp")
	return result


# {
#   責務: [_predict_absorption: 吸収耐性による回復を最低1と最大HP上限に従って予測します]
#   処理: [
#     1: 負の生ダメージの絶対値へ揺らぎを掛けます
#     2: 回復を最大HPで制限します
#     3: HP増加を負のdealtで返します
#   ]
#   引数: [
#     values: 検証済みの対象HP・最大HP・揺らぎを持つ辞書（Dictionary）
#     raw_damage: 魔力×威力×吸収倍率を0方向へ切り捨てた整数（int）
#   ]
#   戻り値: [result: 回復予測、または計算の精度超過による拒否（Dictionary）]
# }
static func _predict_absorption(values: Dictionary, raw_damage: int) -> Dictionary:
	# Pythonと同じく、装備追加値を足さず絶対値を取ってから整数化する。
	var adjusted := Numbers.integer_value(absf(float(raw_damage)) * values["variance"])
	if not adjusted["ok"]:
		return _reject("invalid_magic_numbers")
	var recovery := maxi(1, adjusted["value"])
	# 加算の精度超過を避け、最大HPまでの空き量で先に回復を制限する。
	var healed := mini(recovery, values["target_max_hp"] - values["target_hp"])
	return {"ok": true, "effect": "absorb", "raw_damage": raw_damage, "damage": 0,
		"recovery": recovery, "healed": healed, "dealt": -healed, "remaining_hp": values["target_hp"] + healed}


# {
#   責務: [_reject: 数値や耐性の不正を、成功と区別できる結果として返します]
#   処理: [1: ok=falseと拒否理由を組み立てます]
#   引数: [reason: 数値または耐性を拒否した理由（String）]
#   戻り値: [result: 理由付き拒否辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	# 原本を補修したり、未成立のHP変化を成功として報告したりしない。
	return {"ok": false, "reason": reason}
