# {
#   責務: [status_cure_contract: 順序付き状態異常一覧と明示判定値から一つの治療を予測し、元の一覧や実資源を変更しません]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
const MAX_JSON_DEPTH := 32


# {
#   責務: [select_candidate: 状態異常の形式を検証し、最初の解除可能な候補と判定値の要否を返します]
#   処理: [
#     1: 状態異常を文字列またはJSON互換辞書の配列として検証します
#     2: 一覧を独立コピーし、解除不可の辞書を飛ばして最初の候補を探します
#   ]
#   引数: [effects: 順序を保持する状態異常一覧。辞書のremovable省略と文字列は解除可能です（Variant）]
#   戻り値: [result: 独立したeffects・candidate_index・roll_required、または理由付き拒否（Dictionary）]
# }
static func select_candidate(effects: Variant) -> Dictionary:
	# 未知IDも治療候補にできますが、状態の付与・継続効果を実装済みとは扱いません。
	if not _valid_effects(effects):
		return _reject("invalid_status_effects")
	var copied: Array = effects.duplicate(true)
	var candidate := -1
	for index in copied.size():
		var effect: Variant = copied[index]
		if effect is String or effect.get("removable", true):
			candidate = index
			break
	return {"ok": true, "effects": copied, "candidate_index": candidate, "roll_required": candidate >= 0}


# {
#   責務: [quote_cure: 外から渡した確率と判定値で最初の解除可能な状態一つの治療結果を予測します]
#   処理: [
#     1: 要求キー・有限確率・状態一覧・任意判定値を検証します
#     2: 候補がある場合だけ判定値を要求し、0〜1に制限した確率未満ならコピーから一つ除きます
#   ]
#   引数: [request: status_effects・cure_chanceと任意のrollだけを持つ辞書。候補があれば確率0でもrollが必要です（Variant）]
#   戻り値: [result: 治療成立・治療名・候補位置・独立した残存一覧、または理由付き拒否。乱数や実更新は行いません（Dictionary）]
# }
static func quote_cure(request: Variant) -> Dictionary:
	# 未対応要求を値がfalse・0・空であっても無視して成功にしません。
	if not request is Dictionary:
		return _reject("invalid_cure_request")
	for field in request:
		if field not in ["status_effects", "cure_chance", "roll"]:
			return _reject("unsupported_cure_request")
	var chance := Numbers.float_value(request.get("cure_chance"))
	if not chance["ok"]:
		return _reject("invalid_cure_chance")
	var selected := select_candidate(request.get("status_effects"))
	if not selected["ok"]:
		return selected
	# 候補なしでも、指定済みの不正判定値は拒否します。nullまたは省略は未指定です。
	var roll: Variant = request.get("roll")
	if roll != null and (not (roll is int or roll is float) or not is_finite(float(roll)) or roll < 0 or roll >= 1):
		return _reject("invalid_cure_roll")
	if selected["roll_required"] and roll == null:
		return _reject("missing_cure_roll")
	var probability := clampf(chance["value"], 0.0, 1.0)
	var effects: Array = selected["effects"]
	var cured := false
	var cured_name: Variant = null
	# 同値では治りません。後続候補への再試行や、複数状態の一括治療は行いません。
	if selected["roll_required"] and roll < probability:
		cured = true
		cured_name = _display_name(effects[selected["candidate_index"]])
		effects.remove_at(selected["candidate_index"])
	return {"ok": true, "scope": "status_cure_quote", "cured": cured, "cured_name": cured_name,
		"candidate_index": selected["candidate_index"], "roll_required": selected["roll_required"],
		"cure_chance": probability, "remaining_status_effects": effects}


# {
#   責務: [_valid_effects: 治療に使うキーの型と、拡張情報を含む一覧全体のJSON互換性を確認します]
#   処理: [
#     1: 配列全体の深さ・有限数値・辞書キーを確認します
#     2: 各状態を文字列または辞書に限定し、id/表示名と解除可否の型を確認します
#   ]
#   引数: [effects: 検証前の状態異常一覧。拡張キーは継続効果を実行せず保持します（Variant）]
#   戻り値: [result: 独立コピー可能な対応一覧ならtrue、それ以外ならfalse（bool）]
# }
static func _valid_effects(effects: Variant) -> bool:
	# JSON以外のObjectや循環・過深なコンテナを独立コピーへ持ち込みません。
	if not effects is Array or not _is_json_value(effects):
		return false
	for effect in effects:
		if effect is String:
			continue
		if not effect is Dictionary:
			return false
		for field in ["id", "display_name"]:
			if effect.has(field) and not effect[field] is String:
				return false
		if effect.has("removable") and not effect["removable"] is bool:
			return false
	return true


# {
#   責務: [_is_json_value: 拡張情報を有限数値と文字列キーのJSON値だけに限定し、再帰深さを制限します]
#   処理: [1: コンテナの子を再帰検証し、非有限・精度超過・Object・循環または32段を超える値を拒否します]
#   引数: [
#     value: 一覧または拡張情報の一つの値（Variant）
#     depth: 一覧を0とする再帰深さ。32を超えた値は拒否します（int）
#   ]
#   戻り値: [result: 対応範囲のJSON値ならtrue、それ以外ならfalse（bool）]
# }
static func _is_json_value(value: Variant, depth: int = 0) -> bool:
	if depth > MAX_JSON_DEPTH:
		return false
	if value == null or value is String or value is bool:
		return true
	if value is int or value is float:
		return is_finite(float(value)) and absf(float(value)) <= Numbers.MAX_EXACT_INTEGER
	# 配列と辞書は子まで検証し、辞書の未知キーも変更せず返せる値に限定します。
	if value is Array:
		for child in value:
			if not _is_json_value(child, depth + 1):
				return false
		return true
	if value is Dictionary:
		for key in value:
			if not key is String or not _is_json_value(value[key], depth + 1):
				return false
		return true
	return false


# {
#   責務: [_display_name: 治療成立時の表示名をPythonと同じ表示名・ID・既定名の優先順で選びます]
#   処理: [1: 文字列状態はそのまま返し、辞書の空文字列は次の候補へ進みます]
#   引数: [effect: 型検証済みの文字列または状態辞書（Variant）]
#   戻り値: [result: 治療した状態名。辞書の表示名とIDが空なら状態異常（String）]
# }
static func _display_name(effect: Variant) -> String:
	if effect is String:
		return effect
	for field in ["display_name", "id"]:
		var name: String = effect.get(field, "")
		if not name.is_empty():
			return name
	return "状態異常"


# {
#   責務: [_reject: 治療予測の拒否を成功結果と区別できる理由付き辞書にします]
#   処理: [1: ok=falseと具体的な拒否理由を返します]
#   引数: [reason: 要求・状態一覧・確率・判定値を拒否した理由（String）]
#   戻り値: [result: ok=falseとreasonの辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
