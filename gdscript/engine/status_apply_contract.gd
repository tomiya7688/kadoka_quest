# {
#   責務: [status_apply_contract: 状態一件の重複・耐性補正・明示判定を純粋予測し、実状態/資源/保存を変更しません]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
const Effects = preload("res://engine/status_effect_contract.gd")
const MULTIPLIERS := {"very_weak": 1.5, "weak": 1.25, "normal": 1.0, "resist": 0.75, "strong": 0.5, "immune": 0.0}


# {
#   責務: [prepare_application: 状態定義と現在一覧を検証し、耐性補正済み確率と判定値の要否を返します]
#   処理: [
#     1: 要求キー・状態一覧・状態定義・有限確率・耐性文字列を検証します
#     2: ID欠落・同ID存在・確率0以下・無効耐性を判定し、独立コピーの候補を返します
#   ]
#   引数: [request: effect/status_effectsと任意resistance_levelだけの辞書。chance省略は0、耐性省略はnormalです（Variant）]
#   戻り値: [result: 独立effects/effect・status_id・apply_chance・roll_required・outcome、または理由付き拒否（Dictionary）]
# }
static func prepare_application(request: Variant) -> Dictionary:
	# 未対応キーはfalse/0/空でも受け入れず、未実装効果の実行要求を隠しません。
	if not request is Dictionary:
		return _reject("invalid_status_apply_request")
	for field in request:
		if field not in ["effect", "status_effects", "resistance_level"]:
			return _reject("unsupported_status_apply_request")
	var effect: Variant = request.get("effect")
	if not effect is Dictionary or not Effects.valid_effects([effect]):
		return _reject("invalid_status_definition")
	if not Effects.valid_effects(request.get("status_effects")):
		return _reject("invalid_status_effects")
	var base := Numbers.float_value(effect.get("chance", 0.0))
	if not base["ok"]:
		return _reject("invalid_status_chance")
	var resistance: Variant = request.get("resistance_level", "normal")
	if not resistance is String:
		return _reject("invalid_status_resistance")
	var identifier: String = Effects.normalized_id(effect.get("id", ""))
	var probability := 0.0
	var outcome := "missing_id"
	# 保持済み状態のIDは正規化せず、新規定義の前後空白だけをPythonと同様に取り除きます。
	if not identifier.is_empty():
		outcome = "ready"
		for current in request["status_effects"]:
			if Effects.effect_id(current) == identifier:
				outcome = "already_present"
				break
		if outcome == "ready":
			if base["value"] <= 0.0:
				outcome = "zero_chance"
			elif resistance in ["absorb", "reflect", "immune"]:
				outcome = "immune"
			else:
				probability = minf(1.0, base["value"] * MULTIPLIERS.get(resistance, 1.0))
	# 新規状態候補からchanceを除き、表示名/解除可否の省略だけを補います。
	var candidate: Dictionary = effect.duplicate(true)
	candidate.erase("chance")
	candidate["id"] = identifier
	if not candidate.has("display_name"):
		candidate["display_name"] = identifier
	if not candidate.has("removable"):
		candidate["removable"] = true
	return {"ok": true, "effects": request["status_effects"].duplicate(true), "effect": candidate,
		"status_id": identifier, "apply_chance": probability, "roll_required": probability > 0.0, "outcome": outcome}


# {
#   責務: [quote_application: 耐性補正後の成功率と明示判定値から状態一件の付与と新しい一覧を予測します]
#   処理: [
#     1: 未知要求を拒否し、準備処理へ定義/一覧/確率/耐性の検査を委譲した後に指定済みrollを検証します
#     2: 判定が必要ならrollを要求し、確率未満の場合だけコピー一覧へ候補を一件追加します
#   ]
#   引数: [request: prepare_applicationの要求と任意roll。rollは0以上1未満の有限数値、null/省略は未指定です（Variant）]
#   戻り値: [result: applied/applied_name・確率・判定要否・outcome・独立resulting_status_effects、または理由付き拒否（Dictionary）]
# }
static func quote_application(request: Variant) -> Dictionary:
	if not request is Dictionary:
		return _reject("invalid_status_apply_request")
	for field in request:
		if field not in ["effect", "status_effects", "resistance_level", "roll"]:
			return _reject("unsupported_status_apply_request")
	var prepared_request: Dictionary = request.duplicate()
	prepared_request.erase("roll")
	var prepared := prepare_application(prepared_request)
	if not prepared["ok"]:
		return prepared
	# 判定不要でも指定済み不正値は拒否します。乱数源は受け取らず生成もしません。
	var roll: Variant = request.get("roll")
	if roll != null and (not (roll is int or roll is float) or not is_finite(float(roll)) or roll < 0 or roll >= 1):
		return _reject("invalid_status_apply_roll")
	if prepared["roll_required"] and roll == null:
		return _reject("missing_status_apply_roll")
	var applied := false
	var name: Variant = null
	var outcome: String = prepared["outcome"]
	var effects: Array = prepared["effects"]
	if prepared["roll_required"]:
		applied = roll < prepared["apply_chance"]
		outcome = "applied" if applied else "roll_failed"
		if applied:
			effects.append(prepared["effect"])
			name = prepared["effect"]["display_name"]
			if name.is_empty():
				name = prepared["status_id"]
	return {"ok": true, "scope": "status_apply_quote", "status_id": prepared["status_id"],
		"apply_chance": prepared["apply_chance"], "roll_required": prepared["roll_required"],
		"applied": applied, "applied_name": name, "outcome": outcome, "resulting_status_effects": effects}


# {
#   責務: [_reject: 状態付与予測の不正入力を、部分結果なしの拒否として返します]
#   処理: [1: ok=falseと具体的な入力拒否理由だけを返します]
#   引数: [reason: 要求/定義/一覧/耐性/確率/判定値を拒否した理由（String）]
#   戻り値: [result: ok=falseとreasonの辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
