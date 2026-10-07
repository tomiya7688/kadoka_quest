# {
#   責務: [stat_numbers: stat_numbersは、JSONで整数を正確に表せる範囲でPython互換の有限数値変換と偶数丸めを行います。]
#   フィールド: []
# }
extends RefCounted
## stat_numbersは、JSONで整数を正確に表せる範囲でPython互換の有限数値変換と偶数丸めを行います。

const MAX_EXACT_INTEGER := 9007199254740991


# {
#   責務: [integer_value: 有限数値をPythonのintと同じ0方向の切捨てで整数化します]
#   処理: [1: 入力の型・有限性・精度上限を検証し、対応する変換を行います]
#   引数: [value: 整数・小数・整数文字列として検証する入力（Variant）]
#   戻り値: [result: 成功時はok=trueと整数value、不正または精度超過時はok=false（Dictionary）]
# }
static func integer_value(value: Variant) -> Dictionary:
	# 整数文字列は小数表記と区別し、JSONの整数精度上限を超えないか確認する。
	if value is String:
		var text: String = value.strip_edges()
		if not text.is_valid_int() or absf(text.to_float()) > MAX_EXACT_INTEGER:
			return {"ok": false}
		return {"ok": true, "value": text.to_int()}
	if not (value is int or value is float) or not is_finite(float(value)):
		return {"ok": false}
	if absf(float(value)) > MAX_EXACT_INTEGER:
		return {"ok": false}
	return {"ok": true, "value": int(value)}


# {
#   責務: [float_value: 有限数値または数値文字列を小数へ変換します]
#   処理: [1: 入力の型・有限性・精度上限を検証し、対応する変換を行います]
#   引数: [value: 有限の小数として検証する入力（Variant）]
#   戻り値: [result: 成功時はok=trueと小数value、不正または精度超過時はok=false（Dictionary）]
# }
static func float_value(value: Variant) -> Dictionary:
	# 数値文字列を変換してから、bool・非有限値・精度上限超過を拒否する。
	if value is String:
		var text: String = value.strip_edges()
		if not text.is_valid_float():
			return {"ok": false}
		value = text.to_float()
	if not (value is int or value is float) or not is_finite(float(value)):
		return {"ok": false}
	if absf(float(value)) > MAX_EXACT_INTEGER:
		return {"ok": false}
	return {"ok": true, "value": float(value)}


# {
#   責務: [rounded_integer: 有限小数をPythonのroundと同じ偶数丸めで整数化します]
#   処理: [1: 入力の型・有限性・精度上限を検証し、対応する変換を行います]
#   引数: [value: 最も近い整数へ丸める有限小数（float）]
#   戻り値: [result: 成功時はok=trueと整数value、不正または精度超過時はok=false（Dictionary）]
# }
static func rounded_integer(value: float) -> Dictionary:
	# 非有限値と精度上限超過は、丸める前に拒否する。
	if not is_finite(value) or absf(value) > MAX_EXACT_INTEGER:
		return {"ok": false}
	# ちょうど0.5の値は、隣接する二つの整数のうち偶数へ丸める。
	var lower := floorf(value)
	var fraction := value - lower
	var rounded: int = int(lower)
	if fraction > 0.5 or (fraction == 0.5 and rounded % 2 != 0):
		rounded += 1
	return {"ok": true, "value": rounded}
