# {
#   責務: [status_turn_order_probe: 状態補正済み行動順の純粋APIを呼び、入力保持・返却値の独立性と計測結果を観測します]
#   フィールド: []
# }
extends RefCounted

const Contract = preload("res://engine/status_turn_order.gd")


# {
#   責務: [run: 専用要求の区分から行動順の各ケース観測または反復計測へ委譲します]
#   処理: [1: performance区分なら固定八体を計測し、通常区分なら要求一覧の結果を集めます]
#   引数: [payload: casesまたはperformance/iterations/samples/warmupの専用要求（Dictionary）]
#   戻り値: [result: ケース観測のresults、または固定入力による計測結果（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	# 通常ケースと反復計測で同じ純粋APIを使い、検証用の代替計算を作りません。
	if payload.get("performance", false):
		return _measure(payload)
	var results: Array = []
	for entry: Dictionary in payload.get("cases", []):
		results.append(_observe(entry))
	return {"results": results}


# {
#   責務: [_observe: 行動順APIの入力保持・再実行の一致と返却する二つのキー列の非共有を検査します]
#   処理: [
#     1: 専用コピーへ任意の非JSON値を注入し、純粋な計画を二回実行します
#     2: 結果のキー/速度を改変して再計算と比較し、注入を戻して原要求の不変を確認します
#   ]
#   引数: [entry: requestと任意specialのpath/valueを持つ専用ケース（Dictionary）]
#   戻り値: [result: 契約結果・input_preserved・result_independent・lists_independent（Dictionary）]
# }
static func _observe(entry: Dictionary) -> Dictionary:
	var input: Dictionary = entry.duplicate(true)
	var before := JSON.stringify(input)
	var holder: Variant
	var field: Variant
	var prior: Variant
	var had := false
	var cycle: Dictionary = {}
	# 非有限値・Object・循環は要求JSONで表せないため、開発プローブの専用コピーだけに作ります。
	if input.has("special"):
		var special: Dictionary = input["special"]
		holder = input["request"]
		var path: Array = special["path"]
		for index in path.size() - 1:
			holder = holder[int(path[index])] if holder is Array else holder[path[index]]
		field = 1 if special["value"] == "non_string_key" else path.back()
		had = holder.has(field) if holder is Dictionary else true
		prior = holder.get(field) if holder is Dictionary else holder[int(field)]
		var value: Variant = NAN
		match special["value"]:
			"inf": value = INF
			"object": value = RefCounted.new()
			"non_string_key": value = "invalid"
			"cycle":
				cycle["self"] = cycle
				value = cycle
		holder[field] = value
	# 呼出元による返却値の編集が、別の返却列や次回の計画へ伝播しないことを調べます。
	var result := Contract.plan(input.get("request"))
	var original := result.duplicate(true)
	var lists_independent := true
	if result["ok"]:
		var initial: Array = result["initial"].duplicate(true)
		if not result["order"].is_empty():
			result["order"][0]["id"] = "changed"
		lists_independent = initial == result["initial"]
		result["initial"].append({"side": "allies", "id": "changed"})
		result["speeds"]["allies"]["changed"] = -999
	else:
		result["reason"] = "changed"
	var independent := original == Contract.plan(input.get("request"))
	# 循環を解き、注入前の値へ戻してから、契約が要求本体を変更していないか確認します。
	cycle.clear()
	if input.has("special"):
		if had:
			holder[field] = prior
		else:
			holder.erase(field)
	return {"result": original, "input_preserved": before == JSON.stringify(input),
		"result_independent": independent, "lists_independent": lists_independent}


# {
#   責務: [_benchmark_request: 同IDの両陣営・異なる出血状態・端数倍率・同速を持つ固定八体を用意します]
#   処理: [1: 四体ずつの数値snapshotと状態/倍率を作り、生存者の逆順を明示shuffleへ設定します]
#   引数: []
#   戻り値: [result: 全員が生存する独立した五キー要求（Dictionary）]
# }
static func _benchmark_request() -> Dictionary:
	# 同じIDでも陣営ごとの補正を分離し、下限と同速を含む固定の成功経路を測れるようにします。
	var request := {"allies": [], "enemies": [], "statuses": {"allies": {}, "enemies": {}},
		"speed_multipliers": {"allies": {}, "enemies": {}}, "shuffle_order": []}
	for side in ["allies", "enemies"]:
		for index in 4:
			var id := "member_" + str(index)
			request[side].append({"identity": {"id": id, "species_id": "slime", "name": id},
				"stats": {"hp": 30, "mp": 10, "attack": 20, "defense": 51, "speed": [41, 40, 0, 3][index], "magic": 10},
				"hp": 30, "mp": 7, "fled": false, "alive": true})
			request["statuses"][side][id] = ["poison", {"id": "bleeding", "removable": false}, "bleeding",
				{"id": "mod", "metadata": {"deck": [1, {"kept": true}]}}] if side == "allies" else \
				["poison", "sleep", "Bleeding", {"id": "mod", "metadata": {"deck": [1, {"kept": true}]}}]
			request["speed_multipliers"][side][id] = 0.0 if index == 2 else 1.5
			request["shuffle_order"].push_front({"side": side, "id": id})
	return request


# {
#   責務: [_measure: 八体の正常な状態補正と行動順決定を反復し、一計画の所要時間中央値を返します]
#   処理: [1: 固定入力を事前実行後に複数回計測し、最後の計画と原本保持を観測します]
#   引数: [payload: iterations/samples/warmupを持つ反復条件（Dictionary）]
#   戻り値: [result: 中央値・反復条件・固定request・plan・input_preserved（Dictionary）]
# }
static func _measure(payload: Dictionary) -> Dictionary:
	var request := _benchmark_request()
	var before := JSON.stringify(request)
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	# 不正入力の高速拒否だけではなく、全員の状態補正・厳密shuffle検査・安定整列を毎回実行します。
	for index in warmup:
		Contract.plan(request)
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			Contract.plan(request)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
		timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples, "warmup": warmup,
		"request": request.duplicate(true), "plan": Contract.plan(request), "input_preserved": before == JSON.stringify(request)}
