extends RefCounted
## Python-compatible finite integer conversion and ties-to-even rounding, within JSON precision.

const MAX_EXACT_INTEGER := 9007199254740991


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


static func rounded_integer(value: float) -> Dictionary:
	if not is_finite(value) or absf(value) > MAX_EXACT_INTEGER:
		return {"ok": false}
	var lower := floorf(value)
	var fraction := value - lower
	var rounded: int = int(lower)
	if fraction > 0.5 or (fraction == 0.5 and rounded % 2 != 0):
		rounded += 1
	return {"ok": true, "value": rounded}
