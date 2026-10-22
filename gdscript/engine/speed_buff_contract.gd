# {
#   責務: [speed_buff_contract: 単体速度強化の定義・期間条件・消費後MPを予測し、明示した抽選値から一期間を選びます。乱数の生成と実状態変更は行いません]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
const Selection = preload("res://engine/magic_skill_contract.gd")
const DEFINITION_FIELDS := ["id", "display_name", "description", "kind", "speed_multiplier", "duration", "mp_cost", "target"]


# {
#   責務: [prepare: スキル一覧から指定IDの一意な速度強化定義を選び、対応効果と期間条件を検証します]
#   処理: [1: 共用の一覧選択へ委譲し、成功した定義だけを速度強化の検証へ渡します]
#   引数: [
#     document: schema_version=1とskills配列を持つ一覧（Variant）
#     skill_id: 選択する空でない文字列ID（Variant）
#   ]
#   戻り値: [result: 独立したskill・duration条件・target_policy、または理由付き拒否（Dictionary）]
# }
static func prepare(document: Variant, skill_id: Variant) -> Dictionary:
	# 一覧の重複検査を共用し、通常魔法の対応範囲は拡張しません。
	var selected := Selection.select_definition(document, skill_id)
	if not selected["ok"]:
		return selected
	return validate_definition(selected["skill"])


# {
#   責務: [quote_buff: 速度強化の倍率・期間条件・消費後MPだけを予測し、対象や期間を選択しません]
#   処理: [
#     1: 定義と現在MPだけの要求を検証します
#     2: MP不足を拒否し、倍率・期間条件・対象方針と残MPを返します
#   ]
#   引数: [
#     definition: kind=buffと正のspeed_multiplier・mp_costを持つ単体定義（Variant）
#     request: current_mpだけを持つ辞書。現在MPは非負の正規整数です（Variant）
#   ]
#   戻り値: [result: 抽選前の速度強化予測、または理由付き拒否。実MP・倍率・残り期間は変更しません（Dictionary）]
# }
static func quote_buff(definition: Variant, request: Variant) -> Dictionary:
	# prepareを省略した直接要求にも同じ定義検査を適用します。
	var validated := validate_definition(definition)
	if not validated["ok"]:
		return validated
	if not request is Dictionary:
		return _reject("invalid_quote_request")
	for field in request:
		if field != "current_mp":
			return _reject("unsupported_speed_buff_request")
	var raw_mp: Variant = request.get("current_mp")
	var current_mp := Numbers.integer_value(raw_mp)
	if not (raw_mp is int or raw_mp is float) or not current_mp["ok"] or current_mp["value"] != raw_mp or current_mp["value"] < 0:
		return _reject("invalid_speed_buff_resources")
	var skill: Dictionary = validated["skill"]
	if current_mp["value"] < skill["mp_cost"]:
		return _reject("insufficient_mp")
	# 抽選済みdurationや外部snapshotを受け取らず、定義の制約だけを返します。
	return {"ok": true, "scope": "speed_buff_quote", "skill_id": skill["id"],
		"multiplier": skill["speed_multiplier"], "duration": validated["duration"],
		"target_policy": validated["target_policy"], "mp_cost": skill["mp_cost"],
		"remaining_mp": current_mp["value"] - skill["mp_cost"]}


# {
#   責務: [validate_definition: 速度だけを強化するMP付き単体定義を検証し、数値と期間を正規化します]
#   処理: [
#     1: 未対応キー・区分・文字列・対象方針を拒否します
#     2: 正の倍率と整数化MP消費を確認し、期間条件の検証へ委譲します
#     3: 原本から独立した定義と期間条件を返します
#   ]
#   引数: [definition: 選択または直接指定した速度強化定義（Variant）]
#   戻り値: [result: 正規化したskillとduration条件・target_policy、または理由付き拒否（Dictionary）]
# }
static func validate_definition(definition: Variant) -> Dictionary:
	# 攻撃強化や全体指定をfalse/0でも拒否し、未対応効果を省略して成功にしません。
	if not definition is Dictionary:
		return _reject("invalid_skill_definition")
	for field in definition:
		if field not in DEFINITION_FIELDS:
			return _reject("unsupported_speed_buff_skill")
	if not definition.get("id") is String or definition["id"].is_empty() or definition["id"] in ["attack", "defend"]:
		return _reject("invalid_skill_id")
	if not definition.get("display_name") is String or definition["display_name"].is_empty():
		return _reject("invalid_skill_text")
	if definition.has("description") and not definition["description"] is String:
		return _reject("invalid_skill_text")
	if not definition.get("kind") is String or definition["kind"] != "buff":
		return _reject("unsupported_speed_buff_skill")
	if definition.has("target") and (not definition["target"] is String or definition["target"] != "self"):
		return _reject("unsupported_speed_buff_target")
	# 0倍率はPythonの速度分岐へ入らないため拒否し、負倍率も低水準の速度所有者へ流しません。
	var multiplier := Numbers.float_value(definition.get("speed_multiplier"))
	var cost := Numbers.integer_value(definition.get("mp_cost"))
	if not multiplier["ok"] or multiplier["value"] <= 0 or not cost["ok"] or cost["value"] <= 0:
		return _reject("invalid_speed_buff_numbers")
	var duration := _duration_condition(definition.get("duration"))
	if not duration["ok"]:
		return duration
	var skill: Dictionary = definition.duplicate(true)
	skill.merge({"speed_multiplier": multiplier["value"], "mp_cost": cost["value"], "duration": duration["value"]}, true)
	return {"ok": true, "skill": skill, "duration": duration["condition"],
		"target_policy": "self" if definition.has("target") else "lowest_speed_multiplier"}


# {
#   責務: [_duration_condition: 期間の省略・単値・二要素範囲を、抽選しない正規期間と上下限へ変換します]
#   処理: [
#     1: nullは無期限、配列は二要素だけに限定します
#     2: Pythonと同じ0方向切捨て・最低一・上限補正で正規期間と条件を返します
#   ]
#   引数: [raw: null・有限数値・整数文字列、または同じ型の二要素配列（Variant）]
#   戻り値: [result: ok/value/condition、または不正期間の拒否。conditionはmode/minimum/maximumです（Dictionary）]
# }
static func _duration_condition(raw: Variant) -> Dictionary:
	# 不正な期間を無期限へ読み替えず、利用者が修正できる失敗として返します。
	if raw == null:
		return {"ok": true, "value": null, "condition": {"mode": "untimed", "minimum": null, "maximum": null}}
	if raw is Array and raw.size() != 2:
		return _reject("invalid_speed_buff_duration")
	var is_range := raw is Array
	var low := Numbers.integer_value(raw[0] if is_range else raw)
	var high := Numbers.integer_value(raw[1] if is_range else raw)
	if not low["ok"] or not high["ok"]:
		return _reject("invalid_speed_buff_duration")
	var minimum := maxi(1, low["value"])
	var maximum := maxi(minimum, high["value"])
	return {"ok": true, "value": [minimum, maximum] if is_range else minimum,
		"condition": {"mode": "range" if is_range else "fixed", "minimum": minimum, "maximum": maximum}}


# {
#   責務: [choose_duration: quote_buffが返した期間条件と、乱数の所有者が一回だけ引いた明示値から、付与する一期間を選びます]
#   処理: [
#     1: 期間条件のmode・上下限の組み合わせを再検証します
#     2: duration_rollだけを持つ要求を検証し、範囲では必須、固定・無期限では指定なしを要求します
#     3: 無期限はnull、固定期間は下限、範囲は上下限内の明示値を期間として返します
#   ]
#   引数: [
#     condition: quote_buffのduration条件。mode・minimum・maximumだけを持つ辞書です（Variant）
#     request: 範囲の場合だけduration_rollを持つ辞書。duration_rollは上下限を含む範囲の正規整数です（Variant）
#   ]
#   戻り値: [result: modeと付与期間duration（無期限はnull）、または理由付き拒否。乱数・倍率・残り期間・MPは変更しません（Dictionary）]
# }
static func choose_duration(condition: Variant, request: Variant) -> Dictionary:
	# 外部で編集された期間条件を信用せず、quote_buffが返す三形式だけを受け付けます。
	var checked := _checked_condition(condition)
	if not checked["ok"]:
		return checked
	if not request is Dictionary:
		return _reject("invalid_duration_request")
	for field in request:
		if field != "duration_roll":
			return _reject("unsupported_duration_request")
	# Pythonは範囲だけrandintを呼ぶため、固定・無期限の明示値は乱数の余分な消費として拒否します。
	var mode: String = checked["mode"]
	if mode != "range":
		if request.has("duration_roll"):
			return _reject("unexpected_speed_buff_duration_roll")
		return {"ok": true, "scope": "speed_buff_duration", "mode": mode,
			"duration": null if mode == "untimed" else checked["minimum"]}
	if not request.has("duration_roll"):
		return _reject("missing_speed_buff_duration_roll")
	# 範囲外の値を上下限へ丸めず、乱数の所有者が引き直さずに済む正しい値だけを採用します。
	var roll := _exact_integer(request["duration_roll"])
	if not roll["ok"] or roll["value"] < checked["minimum"] or roll["value"] > checked["maximum"]:
		return _reject("invalid_speed_buff_duration_roll")
	return {"ok": true, "scope": "speed_buff_duration", "mode": mode, "duration": roll["value"]}


# {
#   責務: [_checked_condition: 期間条件が無期限・最低一の固定・最低一の昇順範囲のいずれかであることを確認します]
#   処理: [
#     1: 辞書のキーがmode・minimum・maximumだけであることを確認します
#     2: 無期限は上下限null、固定は同値、範囲は下限以上の上限であることを確認します
#   ]
#   引数: [condition: 再検証する期間条件（Variant）]
#   戻り値: [result: ok=trueとmode・正規整数のminimum/maximum、または不正条件の拒否（Dictionary）]
# }
static func _checked_condition(condition: Variant) -> Dictionary:
	# 未知キーや欠けたキーを持つ条件は、別契約の値の取り違えとして拒否します。
	if not condition is Dictionary or condition.size() != 3:
		return _reject("invalid_speed_buff_duration_condition")
	for field in ["mode", "minimum", "maximum"]:
		if not condition.has(field):
			return _reject("invalid_speed_buff_duration_condition")
	var mode: Variant = condition["mode"]
	if mode is String and mode == "untimed":
		if condition["minimum"] != null or condition["maximum"] != null:
			return _reject("invalid_speed_buff_duration_condition")
		return {"ok": true, "mode": "untimed", "minimum": null, "maximum": null}
	if not (mode is String and mode in ["fixed", "range"]):
		return _reject("invalid_speed_buff_duration_condition")
	# 期間付き強化の上下限は、quote_buffの補正結果と同じ最低一・下限以上の上限に限定します。
	var minimum := _exact_integer(condition["minimum"])
	var maximum := _exact_integer(condition["maximum"])
	if not minimum["ok"] or not maximum["ok"] or minimum["value"] < 1 or maximum["value"] < minimum["value"]:
		return _reject("invalid_speed_buff_duration_condition")
	if mode == "fixed" and maximum["value"] != minimum["value"]:
		return _reject("invalid_speed_buff_duration_condition")
	return {"ok": true, "mode": mode, "minimum": minimum["value"], "maximum": maximum["value"]}


# {
#   責務: [_exact_integer: 期間条件と抽選値に使う、小数部分のない有限の数値型だけを整数へ変換します]
#   処理: [1: bool・文字列・小数部分・非有限値・精度上限超過を拒否し、整数値を返します]
#   引数: [value: JSON由来の整数または整数値float（Variant）]
#   戻り値: [result: ok=trueと整数value、または ok=false（Dictionary）]
# }
static func _exact_integer(value: Variant) -> Dictionary:
	# 定義の期間文字列は_duration_conditionで正規化済みのため、抽選段階では数値型だけを受け付けます。
	if not (value is int or value is float):
		return {"ok": false}
	var converted := Numbers.integer_value(value)
	if not converted["ok"] or converted["value"] != value:
		return {"ok": false}
	return converted


# {
#   責務: [_reject: 速度強化予測の失敗を、部分成功を含まない理由付き辞書で返します]
#   処理: [1: ok=falseと具体的な拒否理由を返します]
#   引数: [reason: 定義・期間・要求・MPを拒否した理由（String）]
#   戻り値: [result: ok=falseとreasonだけの辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
