# {
#   責務: [run_status_cure_probe: 専用JSONで治療予測のPython比較・厳密拒否・入力保持・独立コピー・性能を観測します]
#   フィールド: []
# }
extends SceneTree

const Contract = preload("res://engine/status_cure_contract.gd")


# {
#   責務: [_initialize: 専用要求JSONだけを読み、治療予測の観測を標準出力へ返します]
#   処理: [1: 要求ファイルを読み、ケース検証または反復計測を実行してBase64のJSONを出力します]
#   引数: []
#   戻り値: [result: なし（void）。引数またはJSON形式不正は終了コード2です]
# }
func _initialize() -> void:
	# 利用者セーブ・正規data/assetsへの出力先を持たず、指定JSONだけを読みます。
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		quit(2)
		return
	var payload: Variant = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	if not payload is Dictionary:
		quit(2)
		return
	var result: Dictionary
	if payload.get("performance", false):
		result = _measure_quote(payload)
	else:
		var results: Array = []
		for request: Dictionary in payload.get("cases", []):
			results.append(_run_case(request))
		result = {"results": results}
	print("KADOKA_STATUS_CURE_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)


# {
#   責務: [_run_case: 一つの候補選択または治療予測について入力保持と深い独立コピーを観測します]
#   処理: [
#     1: JSONで保持できない非有限値・Object・1の直前の小数を専用ケースだけへ注入します
#     2: 契約を実行し、返却一覧のネストを改変して原本と再実行結果の不変を確認します
#   ]
#   引数: [request: select/quote区分とeffectsまたはrequest、任意のspecial注入条件（Dictionary）]
#   戻り値: [result: 予測または拒否と、入力保持・結果独立性の観測（Dictionary）]
# }
func _run_case(request: Dictionary) -> Dictionary:
	# 非JSON値はプローブで作り、製品API側で受理できることにしません。
	for special: Dictionary in request.get("special", []):
		var value: Variant = NAN if special["value"] == "nan" else INF
		if special["value"] == "object":
			value = RefCounted.new()
		if special["value"] == "next_below_one":
			value = 1.0 - pow(2.0, -53.0)
		if special.has("status_index"):
			request["request"]["status_effects"][special["status_index"]][special["field"]] = value
		else:
			request["request"][special["field"]] = value
	var before := JSON.stringify(request)
	var result := _invoke_contract(request)
	var original := result.duplicate(true)
	# 戻り値の辞書・ネスト・一覧を編集し、元の状態辞書へ影響しないことを確認します。
	for field in ["effects", "remaining_status_effects"]:
		for effect in result.get(field, []):
			if effect is Dictionary:
				effect["id"] = "changed"
				if effect.get("metadata") is Dictionary and effect["metadata"].get("deck") is Array:
					effect["metadata"]["deck"].append("changed")
		if result.has(field):
			result[field].append("changed")
	return {"result": original, "input_preserved": before == JSON.stringify(request),
		"result_independent": original == _invoke_contract(request)}


# {
#   責務: [_invoke_contract: ケースの操作名を対応する候補選択または治療予測APIへ委譲します]
#   処理: [1: selectなら候補選択、quoteなら治療予測を呼び、他の操作名は拒否します]
#   引数: [request: 操作名と対応APIへ渡す独立した入力（Dictionary）]
#   戻り値: [result: 純粋契約の結果、またはプローブの操作名拒否（Dictionary）]
# }
func _invoke_contract(request: Dictionary) -> Dictionary:
	match request.get("operation"):
		"select":
			return Contract.select_candidate(request.get("effects"))
		"quote":
			return Contract.quote_cure(request.get("request"))
	return {"ok": false, "reason": "invalid_probe_operation"}


# {
#   責務: [_measure_quote: コピーと検証を含む治療予測一回の中央値を、元一覧を変えない固定ケースで測ります]
#   処理: [
#     1: 解除不可2件と毒・眠りを用意し、最初の解除可能な毒を明示判定で治療します
#     2: 起動・I/O・事前実行を除いて同じAPIを反復し、中央値と実際の予測を返します
#   ]
#   引数: [payload: iterations・samples・warmupの反復条件（Dictionary）]
#   戻り値: [result: 時間中央値・条件・元一覧の保持と治療成立結果（Dictionary）]
# }
func _measure_quote(payload: Dictionary) -> Dictionary:
	# 候補なしの高速な経路ではなく、解除不可を飛ばしてネスト付き候補を治す経路を測ります。
	var request := {"status_effects": [
		{"id": "lock_a", "removable": false, "metadata": {"deck": ["a"]}},
		{"id": "lock_b", "removable": false},
		{"id": "poison", "display_name": "毒", "metadata": {"deck": ["b", {"kept": true}]}}, "sleep"],
		"cure_chance": 0.03, "roll": 0.02}
	var before := JSON.stringify(request)
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	for index in warmup:
		Contract.quote_cure(request)
	# タイマー内ではAPIのみを呼び、一覧の再生成やファイル出力を測りません。
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			Contract.quote_cure(request)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "input_preserved": before == JSON.stringify(request), "quote": Contract.quote_cure(request),
		"original_effects": request["status_effects"].duplicate(true)}
