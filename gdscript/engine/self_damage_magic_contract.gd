# {
#   責務: [self_damage_magic_contract: 自傷付き単体魔法の敵HP・術者HP・残MPを、入力を変更せず予測します]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
const MagicContract = preload("res://engine/magic_skill_contract.gd")


# {
#   責務: [prepare: 指定IDの一意な自傷付き単体魔法定義を検証して返します]
#   処理: [
#     1: 一覧から定義を選択します
#     2: 魔法の対応範囲と自傷率を検証します
#   ]
#   引数: [
#     document: schema_version=1とskills配列を持つスキル一覧（Variant）
#     skill_id: 選択するスキルID（Variant）
#   ]
#   戻り値: [result: ok=trueと独立したskill、またはok=falseとreason（Dictionary）]
# }
static func prepare(document: Variant, skill_id: Variant) -> Dictionary:
	# ID選択は通常魔法と共用するが、自傷を通常魔法の対応範囲へ加えない。
	var selected := MagicContract.select_definition(document, skill_id)
	if not selected["ok"]:
		return selected
	var validated := _validate_definition(selected["skill"])
	if not validated["ok"]:
		return validated
	return {"ok": true, "skill": validated["skill"]}


# {
#   責務: [quote_damage: 自傷付き魔法を使用した場合の対象HP・術者HP・残MPを予測します]
#   処理: [
#     1: 自傷付き定義と生存術者のHPを検証します
#     2: 通常魔法の契約で対象HPとMPを予測します
#     3: 術者HPの代償予測を結果へ加えます
#   ]
#   引数: [
#     definition: kind=magic、正のmp_cost、有限self_damage_ratioを持つ単体スキル定義（Variant）
#     request: 通常魔法の数値要求にactor_hpとactor_max_hpを加えた辞書（Variant）
#   ]
#   戻り値: [result: ok=trueと敵HP/術者HP/MP予測、または理由付き拒否。実資源は変更しません（Dictionary）]
# }
static func quote_damage(definition: Variant, request: Variant) -> Dictionary:
	# prepareを省略した呼出しにも、同じ定義と入力の検証を適用する。
	var validated := _validate_definition(definition)
	if not validated["ok"]:
		return validated
	var actor_cost := _predict_actor_cost(request, validated["ratio"], validated["enabled"])
	if not actor_cost["ok"]:
		return actor_cost
	# 対応する自傷フィールドだけを分離し、未知の効果や要求キーは通常契約で拒否する。
	var skill: Dictionary = validated["skill"].duplicate(true)
	skill.erase("self_damage_ratio")
	var magic_request: Dictionary = request.duplicate(true)
	magic_request.erase("actor_hp")
	magic_request.erase("actor_max_hp")
	var result := MagicContract.quote_damage(skill, magic_request)
	if not result["ok"]:
		return result
	# Python正本は通常・無効・吸収の対象効果の後で自傷し、術者HPを最低1にする。
	result.merge(actor_cost, true)
	result["scope"] = "self_damage_magic_quote"
	return result


# {
#   責務: [_validate_definition: 通常魔法の対応範囲に自傷率だけを加え、独立した定義を作ります]
#   処理: [
#     1: 必須の自傷率を有限数値として検証します
#     2: 自傷以外の定義を通常魔法の契約で検証します
#     3: 元の自傷率表現を保持します
#   ]
#   引数: [definition: 検証する自傷付き単体魔法定義（Variant）]
#   戻り値: [result: 検証済みskill・数値ratio・自傷の有効性enabled、または理由付き拒否（Dictionary）]
# }
static func _validate_definition(definition: Variant) -> Dictionary:
	# 欠落・bool・非有限値を暗黙に0へ補修しない。
	if not definition is Dictionary or not definition.has("self_damage_ratio"):
		return _reject("invalid_self_damage_ratio")
	var original_ratio: Variant = definition["self_damage_ratio"]
	var ratio := Numbers.float_value(original_ratio)
	if not ratio["ok"]:
		return _reject("invalid_self_damage_ratio")
	var base_definition: Dictionary = definition.duplicate(true)
	base_definition.erase("self_damage_ratio")
	var validated := MagicContract.prepare({"schema_version": 1, "skills": [base_definition]}, base_definition.get("id"))
	if not validated["ok"]:
		return validated
	# Pythonでは数値0は自傷なし、文字列"0"は真となり最低1の代償が発生する。
	validated["skill"]["self_damage_ratio"] = original_ratio
	validated.merge({"ratio": ratio["value"], "enabled": original_ratio is String or ratio["value"] != 0.0}, true)
	return validated


# {
#   責務: [_predict_actor_cost: 生存術者の最大HPから代償を計算し、実HP減少をHP1の下限で制限します]
#   処理: [
#     1: 術者の現在HPと最大HPが正規整数で整合するか検証します
#     2: 自傷率が有効なら最大HPに掛け、最低1の代償量を計算します
#     3: HP1を残した結果と実減少量を返します
#   ]
#   引数: [
#     request: actor_hpとactor_max_hpを持つ予測要求（Variant）
#     ratio: 有限性と精度を検証済みの自傷率（float）
#     enabled: 元の自傷率がPythonの真偽判定で有効かどうか（bool）
#   ]
#   戻り値: [result: self_damage・self_dealt・remaining_actor_hp等、または理由付き拒否（Dictionary）]
# }
static func _predict_actor_cost(request: Variant, ratio: float, enabled: bool) -> Dictionary:
	# 死亡者の復活を予測に混ぜず、文字列や小数部分のある資源も拒否する。
	if not request is Dictionary:
		return _reject("invalid_quote_request")
	var values := {}
	for field in ["actor_hp", "actor_max_hp"]:
		var value: Variant = request.get(field)
		var checked := Numbers.integer_value(value)
		if not (value is int or value is float) or not checked["ok"] or checked["value"] != value or checked["value"] <= 0:
			return _reject("invalid_actor_hp")
		values[field] = checked["value"]
	if values["actor_hp"] > values["actor_max_hp"]:
		return _reject("invalid_actor_hp")
	# 計算上の代償とHP下限で制限した実減少を分け、未対応の精度超過を拒否する。
	var self_damage := 0
	if enabled:
		var cost := Numbers.integer_value(values["actor_max_hp"] * ratio)
		if not cost["ok"]:
			return _reject("invalid_self_damage_numbers")
		self_damage = maxi(1, cost["value"])
	var remaining: int = maxi(1, values["actor_hp"] - self_damage)
	return {"ok": true, "self_damage": self_damage, "self_dealt": values["actor_hp"] - remaining,
		"remaining_actor_hp": remaining, "self_damage_ratio": ratio, "self_damage_enabled": enabled}


# {
#   責務: [_reject: 不正な自傷率や術者HPを、成立した予測と区別できる結果へ変換します]
#   処理: [1: ok=falseと拒否理由を返します]
#   引数: [reason: 定義・術者資源・精度検証の拒否理由（String）]
#   戻り値: [result: ok=falseとreasonを持つ辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	# 入力を変更して成功へ補修せず、呼出元へ失敗理由を渡す。
	return {"ok": false, "reason": reason}
