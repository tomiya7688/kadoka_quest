# {
#   責務: [status_stat_contract: 最新状態と補正前数値から防御力・素早さを非破壊で求め、資源や状態を保持しません]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
const Effects = preload("res://engine/status_effect_contract.gd")
const BLEEDING_MULTIPLIER := 0.9


# {
#   責務: [quote_stats: 出血の有無と一時速度倍率から実効防御力・素早さを予測し、元の入力を保持します]
#   処理: [
#     1: 要求キー・補正前の非負整数・一時速度倍率・状態一覧全体を検証します
#     2: 出血が一件以上あれば倍率0.9を一度だけ掛け、最後に整数化と下限制限を行います
#   ]
#   引数: [request: defense/speed/status_effectsと任意speed_multiplierだけを持つ辞書。一時速度倍率の省略値は1です（Variant）]
#   戻り値: [result: ok/scope/defense/speedの独立辞書、またはok=false/reasonだけの拒否（Dictionary）]
# }
static func quote_stats(request: Variant) -> Dictionary:
	# 未対応効果を黙って無視しないよう、guardや攻撃倍率の入力は受け付けません。
	if not request is Dictionary:
		return _reject("invalid_status_stat_request")
	for field in request:
		if field not in ["defense", "speed", "status_effects", "speed_multiplier"]:
			return _reject("unsupported_status_stat_request")
	for field in ["defense", "speed"]:
		if not _valid_number(request.get(field)) or float(request[field]) != floorf(float(request[field])):
			return _reject("invalid_base_" + field)
	var speed_multiplier: Variant = request.get("speed_multiplier", 1.0)
	if not _valid_number(speed_multiplier):
		return _reject("invalid_speed_multiplier")
	if not Effects.valid_effects(request.get("status_effects")):
		return _reject("invalid_status_effects")
	# 一覧を先に全検証し、出血より後ろにある不正値も見逃しません。重複出血は累積しません。
	var status_multiplier := 1.0
	for effect in request["status_effects"]:
		if Effects.effect_id(effect) == "bleeding":
			status_multiplier = BLEEDING_MULTIPLIER
			break
	# Python Combatant.speedと同じ乗算順にし、一時倍率を掛けた段階では切り捨てません。
	var temporary_speed := float(request["speed"]) * float(speed_multiplier)
	if not _valid_number(temporary_speed):
		return _reject("status_stat_precision_exceeded")
	var speed := temporary_speed * status_multiplier
	var defense := float(request["defense"]) * status_multiplier
	return {"ok": true, "scope": "status_stat_quote", "defense": maxi(0, int(defense)), "speed": maxi(1, int(speed))}


# {
#   責務: [_valid_number: 能力値計算を有限・非負・JSON整数精度内の数値へ限定します]
#   処理: [1: boolや文字列を拒否し、数値の符号・有限性・上限を確認します]
#   引数: [value: 補正前数値、一時速度倍率、または途中積の候補（Variant）]
#   戻り値: [result: 0以上9007199254740991以下の有限数値ならtrue（bool）]
# }
static func _valid_number(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value)) \
		and float(value) >= 0 and float(value) <= Numbers.MAX_EXACT_INTEGER


# {
#   責務: [_reject: 状態能力値予測の失敗を、部分的な補正値を含まない辞書へまとめます]
#   処理: [1: 成功結果と区別するok=falseと拒否理由を返します]
#   引数: [reason: 要求・数値・状態一覧を拒否した理由（String）]
#   戻り値: [result: ok=falseとreasonの辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
