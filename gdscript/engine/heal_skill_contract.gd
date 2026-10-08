# {
#   責務: [heal_skill_contract: MP付き単体HP回復の定義を検証し、実資源を変えず回復量と残HP/MPを予測します]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
const MagicContract = preload("res://engine/magic_skill_contract.gd")


# {
#   責務: [prepare: スキル一覧から指定IDの一意なHP回復定義を選び、対応範囲と数値を確認します]
#   処理: [
#     1: 共用の一覧選択で形式不正・ID欠落・重複を拒否します
#     2: HP回復定義を検証し、原本と独立した辞書を返します
#   ]
#   引数: [
#     document: schema_version=1とskills配列を持つ一覧（Variant）
#     skill_id: 選択する空でない文字列ID（Variant）
#   ]
#   戻り値: [result: ok=trueと独立したskill、または理由付き拒否（Dictionary）]
# }
static func prepare(document: Variant, skill_id: Variant) -> Dictionary:
	# 一覧選択だけを共用し、通常魔法の対応範囲をHP回復へ広げない。
	var selected := MagicContract.select_definition(document, skill_id)
	if not selected["ok"]:
		return selected
	return _validate_definition(selected["skill"])


# {
#   責務: [quote_heal: 明示した対象のHP回復と術者の消費後MPを予測します]
#   処理: [
#     1: 定義と現在MP・対象HPの要求を検証します
#     2: MP不足を拒否し、回復前の資源値を数値計算へ渡します
#   ]
#   引数: [
#     definition: kind=healと正のmp_costを持つHP回復定義。heal_ratio省略時は0.15（Variant）
#     request: current_mp・target_hp・target_max_hpだけを持つ辞書（Variant）
#   ]
#   戻り値: [result: 回復上限量・実回復量・残HP/MP、または理由付き拒否。実資源を変更しません（Dictionary）]
# }
static func quote_heal(definition: Variant, request: Variant) -> Dictionary:
	# prepareを省略した直接要求にも、同じ効果・数値の検証を適用する。
	var validated := _validate_definition(definition)
	if not validated["ok"]:
		return validated
	var resources := _validate_request(request)
	if not resources["ok"]:
		return resources
	var skill: Dictionary = validated["skill"]
	if resources["current_mp"] < skill["mp_cost"]:
		return _reject("insufficient_mp")
	return _predict_recovery(skill, resources)


# {
#   責務: [_validate_definition: 単体HP回復だけの定義を確認し、未知効果を値によらず拒否します]
#   処理: [
#     1: 許可キー・ID・表示名・説明・heal区分を確認します
#     2: 有限回復率と正の整数化MP消費を確認し、独立定義へ正規化します
#   ]
#   引数: [definition: 選択または直接指定した回復定義（Variant）]
#   戻り値: [result: 検証済みの独立したskill、または理由付き拒否（Dictionary）]
# }
static func _validate_definition(definition: Variant) -> Dictionary:
	# 治療確率0やfalseも捨てずに拒否し、HP回復だけで治療対応を偽装しない。
	if not definition is Dictionary:
		return _reject("invalid_skill_definition")
	for field in definition:
		if field not in ["id", "display_name", "description", "kind", "heal_ratio", "mp_cost"]:
			return _reject("unsupported_heal_skill")
	if not definition.get("id") is String or definition["id"].is_empty() or definition["id"] in ["attack", "defend"]:
		return _reject("invalid_skill_id")
	if not definition.get("display_name") is String or definition["display_name"].is_empty():
		return _reject("invalid_skill_display_name")
	if definition.has("description") and not definition["description"] is String:
		return _reject("invalid_skill_description")
	if not definition.get("kind") is String or definition["kind"] != "heal":
		return _reject("unsupported_heal_skill")
	# 有限の負/0回復率も最低1へ進める。MP消費はPythonと同じ0方向切捨てを使う。
	var ratio := Numbers.float_value(definition.get("heal_ratio", 0.15))
	var cost := Numbers.integer_value(definition.get("mp_cost"))
	if not ratio["ok"] or not cost["ok"] or cost["value"] <= 0:
		return _reject("invalid_heal_skill_numbers")
	var skill: Dictionary = definition.duplicate(true)
	skill.merge({"heal_ratio": ratio["value"], "mp_cost": cost["value"]}, true)
	return {"ok": true, "skill": skill}


# {
#   責務: [_validate_request: 回復対象のHPと術者MPが非負の正規整数で整合するか確認します]
#   処理: [
#     1: 未対応キーと資源の文字列・bool・小数部分・非有限値・精度超過を拒否します
#     2: 正の最大HPと現在HPの上限を確認します
#   ]
#   引数: [request: current_mp・target_hp・target_max_hpだけを持つ数値要求（Variant）]
#   戻り値: [result: 正規化した資源、または理由付き拒否（Dictionary）]
# }
static func _validate_request(request: Variant) -> Dictionary:
	# HP0は数値として許可するが、死亡対象を選べることや復活を保証しない。
	if not request is Dictionary:
		return _reject("invalid_quote_request")
	for field in request:
		if field not in ["current_mp", "target_hp", "target_max_hp"]:
			return _reject("unsupported_heal_request")
	var resources := {"ok": true}
	for field in ["current_mp", "target_hp", "target_max_hp"]:
		var value: Variant = request.get(field)
		var checked := Numbers.integer_value(value)
		if not (value is int or value is float) or not checked["ok"] or checked["value"] != value or checked["value"] < 0:
			return _reject("invalid_heal_resources")
		resources[field] = checked["value"]
	if resources["target_max_hp"] <= 0 or resources["target_hp"] > resources["target_max_hp"]:
		return _reject("invalid_heal_resources")
	return resources


# {
#   責務: [_predict_recovery: 対象最大HPと回復率から回復上限量を求め、最大HPまでの実回復量を予測します]
#   処理: [
#     1: 最大HPと回復率の積を0方向へ整数化し、最低1の回復上限量を求めます
#     2: 最大HPまでの空き量で実回復を制限し、残HPと消費後MPを返します
#   ]
#   引数: [
#     skill: 検証済みの有限heal_ratioと正のmp_costを持つ定義（Dictionary）
#     resources: 検証済みの現在MP・対象現在HP・対象最大HP（Dictionary）
#   ]
#   戻り値: [result: HP/MP予測、または必要な積の精度超過による拒否（Dictionary）]
# }
static func _predict_recovery(skill: Dictionary, resources: Dictionary) -> Dictionary:
	# 満HPでも回復上限量を返すため、積の検証を省略しない。乱数・魔力・耐性は使わない。
	var amount := Numbers.integer_value(resources["target_max_hp"] * skill["heal_ratio"])
	if not amount["ok"]:
		return _reject("invalid_heal_numbers")
	var limit := maxi(1, amount["value"])
	# 加算前に空き量で制限し、精度上限近傍のHP加算が範囲を超えないようにする。
	var recovered: int = mini(limit, resources["target_max_hp"] - resources["target_hp"])
	return {"ok": true, "scope": "heal_skill_quote", "skill_id": skill["id"],
		"heal_amount": limit, "healed": recovered, "remaining_hp": resources["target_hp"] + recovered,
		"mp_cost": skill["mp_cost"], "remaining_mp": resources["current_mp"] - skill["mp_cost"]}


# {
#   責務: [_reject: 回復予測の失敗を成功結果と区別できる理由付き辞書へ変換します]
#   処理: [1: ok=falseと具体的な拒否理由を返します]
#   引数: [reason: 定義・要求・資源・数値を拒否した理由（String）]
#   戻り値: [result: ok=falseとreasonの辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
