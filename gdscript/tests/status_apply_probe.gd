# {
#   責務: [status_apply_probe: 状態付与予測の拒否・入力保持・コピー独立性と反復性能を開発用要求から観測します]
#   フィールド: []
# }
extends RefCounted

const Contract = preload("res://engine/status_apply_contract.gd")


# {
#   責務: [run: 専用付与要求をケース観測または性能測定へ委譲します]
#   処理: [1: performance指定なら計測し、それ以外はケースを順番に観測します]
#   引数: [payload: casesまたはiterations/samples/warmupを持つ開発用辞書（Dictionary）]
#   戻り値: [result: ケース結果一覧または時間/入力保持/実予測結果（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	if payload.get("performance", false):
		return _measure(payload)
	var results: Array = []
	for entry: Dictionary in payload.get("cases", []):
		results.append(_run_case(entry))
	return {"results": results}


# {
#   責務: [_run_case: 一件の付与準備/予測に非JSON不正値を注入し、入力保持と返却値の独立性を確認します]
#   処理: [
#     1: 指定したnative不正値を専用ケースへ設定します
#     2: APIを呼び、返却値のネスト編集後も原本と再実行結果が不変か観測します
#   ]
#   引数: [entry: operation・requestと任意specialの注入先/値名を持つ辞書（Dictionary）]
#   戻り値: [result: API結果とinput_preserved/result_independent（Dictionary）]
# }
static func _run_case(entry: Dictionary) -> Dictionary:
	var request: Variant = entry.get("request")
	# 循環はファイルに保存せず、専用API呼び出し前だけ生成して終了時に解きます。
	if entry.get("special") is String and entry["special"] == "cycle":
		var original_request := JSON.stringify(request)
		var cyclic: Dictionary = {}
		cyclic["self"] = cyclic
		request["effect"]["metadata"] = cyclic
		var rejected := Contract.quote_application(request)
		var preserved := cyclic.size() == 1 and is_same(cyclic["self"], cyclic)
		var independent := rejected == Contract.quote_application(request)
		cyclic.clear()
		request["effect"].erase("metadata")
		return {"result": rejected, "input_preserved": preserved and original_request == JSON.stringify(request),
			"result_independent": independent}
	for special: Dictionary in entry.get("special", []):
		var value: Variant = NAN
		match special["value"]:
			"inf": value = INF
			"object": value = RefCounted.new()
			"non_string_key": value = {1: "invalid"}
			"next_below_one": value = 1.0 - pow(2.0, -53.0)
		if special.get("target", "request") == "request":
			request[special["field"]] = value
		else:
			request["effect"][special["field"]] = value
	var before := JSON.stringify(request)
	var result := _invoke(entry.get("operation", "quote"), request)
	var original := result.duplicate(true)
	# 返却一覧と候補を編集し、深いコピー不足が元要求へ伝播しないか確認します。
	for field in ["effects", "effect", "resulting_status_effects"]:
		if result.has(field):
			_mutate(result[field])
	return {"result": original, "input_preserved": before == JSON.stringify(request),
		"result_independent": original == _invoke(entry.get("operation", "quote"), request)}


# {
#   責務: [_invoke: プローブ操作名を純粋準備または純粋付与予測へ委譲します]
#   処理: [1: prepare/quote以外を拒否し、対応する契約APIの結果を返します]
#   引数: [
#     operation: 開発ケースの操作名（String）
#     request: 製品契約へそのまま渡す明示要求（Variant）
#   ]
#   戻り値: [result: 契約結果またはinvalid_probe_operationの拒否（Dictionary）]
# }
static func _invoke(operation: String, request: Variant) -> Dictionary:
	match operation:
		"prepare": return Contract.prepare_application(request)
		"quote": return Contract.quote_application(request)
	return {"ok": false, "reason": "invalid_probe_operation"}


# {
#   責務: [_mutate: 返却データの各ネストを編集し、原本への共有参照を検出する材料を作ります]
#   処理: [1: 子コンテナまで編集し、辞書/配列へchanged値を加えます]
#   引数: [value: 契約から返された独立コピーを検査する値（Variant）]
#   戻り値: [result: なし（void）。渡された返却値だけを編集します]
# }
static func _mutate(value: Variant) -> void:
	if value is Dictionary:
		for key in value:
			_mutate(value[key])
		value["changed"] = true
	elif value is Array:
		for child in value:
			_mutate(child)
		value.append("changed")


# {
#   責務: [_measure: 重複しないネスト付き状態一件の付与予測を、原本を変更せず反復測定します]
#   処理: [
#     1: 四件の既存状態と0.4の基礎確率/weak耐性/roll0.49の新規出血を準備します
#     2: 起動/I/O/事前実行を除き予測APIのみを反復し、中央値と実予測を返します
#   ]
#   引数: [payload: iterations/samples/warmupの測定条件（Dictionary）]
#   戻り値: [result: 一予測のmicroseconds中央値・条件・元要求と予測結果（Dictionary）]
# }
static func _measure(payload: Dictionary) -> Dictionary:
	var request := {"status_effects": [
		{"id": "lock", "removable": false}, "poison", "sleep",
		{"id": "mod", "metadata": {"deck": [1, {"kept": true}]}}],
		"effect": {"id": "bleeding", "display_name": "出血", "chance": 0.4,
			"metadata": {"deck": ["a", {"kept": true}]}},
		"resistance_level": "weak", "roll": 0.49}
	var before := JSON.stringify(request)
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	for index in warmup:
		Contract.quote_application(request)
	var timings: Array = []
	# 毎回の付与成功を予測し、重複拒否だけの高速経路を測りません。
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			Contract.quote_application(request)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations,
		"samples": samples, "warmup": warmup, "input_preserved": before == JSON.stringify(request),
		"original_request": request.duplicate(true), "quote": Contract.quote_application(request)}
