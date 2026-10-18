# {
#   責務: [status_stat_probe: 状態による防御力・速度補正の純粋APIを呼び、値・非変更・独立性・性能を観測します]
#   フィールド: []
# }
extends RefCounted

const Contract = preload("res://engine/status_stat_contract.gd")


# {
#   責務: [run: 専用JSONのケース一覧または性能要求を状態能力値プローブへ振り分けます]
#   処理: [1: 性能区分なら反復計測し、通常区分なら各要求の実結果を返します]
#   引数: [payload: cases、またはperformance/iterations/samples/warmupの専用要求（Dictionary）]
#   戻り値: [result: ケース観測一覧または反復計測結果（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	if payload.get("performance", false):
		return _measure(payload)
	var results: Array = []
	for entry: Dictionary in payload.get("cases", []):
		results.append(_observe(entry))
	return {"results": results}


# {
#   責務: [_observe: 一つの要求を二回予測し、返却値の改変が入力や次の結果へ伝播しないことを確認します]
#   処理: [1: 専用要求コピーへ任意native不正値を入れ、予測後に注入を戻して原要求と比較します]
#   引数: [entry: requestと任意specialを持つ専用ケース（Dictionary）]
#   戻り値: [result: 契約結果・input_preserved・result_independent（Dictionary）]
# }
static func _observe(entry: Dictionary) -> Dictionary:
	var input: Dictionary = entry.duplicate(true)
	var before := JSON.stringify(input)
	var holder: Dictionary = {}
	var field: Variant = ""
	var prior: Variant
	var had := false
	var cycle: Dictionary = {}
	# 非JSON値は保存ファイルでは表せないため、API境界の専用コピーだけへ注入します。
	if input.has("special"):
		var special: Dictionary = input["special"]
		holder = input["request"] if special.get("target", "request") == "request" else input["request"]["status_effects"][0]
		field = 1 if special.get("value") == "non_string_key" else special["field"]
		had = holder.has(field)
		prior = holder.get(field)
		var value: Variant = NAN
		match special["value"]:
			"inf": value = INF
			"object": value = RefCounted.new()
			"non_string_key": value = "invalid"
			"cycle":
				cycle["self"] = cycle
				value = cycle
		holder[field] = value
	var result := Contract.quote_stats(input.get("request"))
	var original := result.duplicate(true)
	result["defense"] = -999
	result["speed"] = -999
	var independent := original == Contract.quote_stats(input.get("request"))
	# 専用循環を解いてから、注入前の要求が契約によって変更されていないか照合します。
	cycle.clear()
	if input.has("special"):
		if had:
			holder[field] = prior
		else:
			holder.erase(field)
	return {"result": original, "input_preserved": before == JSON.stringify(input), "result_independent": independent}


# {
#   責務: [_measure: 出血と一時速度倍率を含む正常な予測を反復し、入力保持と一回の所要時間中央値を返します]
#   処理: [1: 固定入力を事前実行後に複数回測定し、最後の実予測と原本を返します]
#   引数: [payload: iterations/samples/warmupの計測条件（Dictionary）]
#   戻り値: [result: 中央値・反復条件・request・quote・input_preserved（Dictionary）]
# }
static func _measure(payload: Dictionary) -> Dictionary:
	var request := {"defense": 51, "speed": 41, "speed_multiplier": 1.5,
		"status_effects": ["poison", {"id": "bleeding", "removable": false}, "bleeding",
			{"id": "mod", "metadata": {"deck": [1, {"kept": true}]}}]}
	var before := JSON.stringify(request)
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	# 実際に防御力と速度が変わる正常経路を毎回通し、高速な拒否だけの計測を避けます。
	for index in warmup:
		Contract.quote_stats(request)
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			Contract.quote_stats(request)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
		timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples, "warmup": warmup,
		"request": request.duplicate(true), "quote": Contract.quote_stats(request), "input_preserved": before == JSON.stringify(request)}
