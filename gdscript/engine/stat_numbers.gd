# {
#   責務: [stat_numbers: Python-compatible finite integer conversion and ties-to-even rounding, within JSON precision.]
#   フィールド: []
# }
extends RefCounted
## Python-compatible finite integer conversion and ties-to-even rounding, within JSON precision.

const MAX_EXACT_INTEGER := 9007199254740991


# {
#   責務: [integer_value: stat・numbersのinteger・値を求める]
#   処理: [1: stat・numbersのinteger・値を求める]
#   引数: [value: 値（Variant）]
#   戻り値: [result: stat・numbersのinteger・値を求めるための結果（Dictionary）]
# }
static func integer_value(value: Variant) -> Dictionary:
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
#   責務: [float_value: stat・numbersのfloat・値を求める]
#   処理: [1: stat・numbersのfloat・値を求める]
#   引数: [value: 値（Variant）]
#   戻り値: [result: stat・numbersのfloat・値を求めるための結果（Dictionary）]
# }
static func float_value(value: Variant) -> Dictionary:
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
#   責務: [rounded_integer: stat・numbersのrounded・integerを求める]
#   処理: [1: stat・numbersのrounded・integerを求める]
#   引数: [value: 値（float）]
#   戻り値: [result: stat・numbersのrounded・integerを求めるための結果（Dictionary）]
# }
static func rounded_integer(value: float) -> Dictionary:
	if not is_finite(value) or absf(value) > MAX_EXACT_INTEGER:
		return {"ok": false}
	var lower := floorf(value)
	var fraction := value - lower
	var rounded: int = int(lower)
	if fraction > 0.5 or (fraction == 0.5 and rounded % 2 != 0):
		rounded += 1
	return {"ok": true, "value": rounded}
