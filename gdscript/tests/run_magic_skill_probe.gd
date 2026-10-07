# {
#   責務: [run_magic_skill_probe: 専用fixtureを読み、魔法スキル契約の結果・入力不変・独立コピー・性能を検証する]
#   フィールド: []
# }
extends SceneTree

const Contract = preload("res://engine/magic_skill_contract.gd")


# {
#   責務: [_initialize: プローブ要求を読み、指定した検証へ委譲して結果を出力する]
#   処理: [
#     1: 専用fixtureを読む
#     2: ケース検証または性能測定を呼ぶ
#     3: 結果を出力する
#   ]
#   引数: []
#   戻り値: [result: なし（void）。失敗時は非ゼロで終了する]
# }
func _initialize() -> void:
	# 外部から指定した専用JSONだけを読み取り、ファイルへは書き込まない。
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		quit(2)
		return
	var payload: Variant = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	if not payload is Dictionary:
		quit(2)
		return
	# 実装の結果を計測値で置き換えず、通常検証と性能要求を分ける。
	var result: Dictionary
	if payload.get("performance", false):
		result = _measure_quote(payload)
	else:
		var results: Array = []
		for request: Dictionary in payload.get("cases", []):
			results.append(_run_case(request))
		result = {"results": results}
	print("KADOKA_MAGIC_SKILL_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)


# {
#   責務: [_run_case: 一つの定義または予測要求について拒否・入力保持・結果独立性を検証する]
#   処理: [
#     1: JSONで表せないNaNまたは無限大を専用要求へ注入する
#     2: 契約を呼ぶ
#     3: 結果改変後に再実行してコピー独立性を確認する
#   ]
#   引数: [request: 操作名prepare/quoteと、対応する定義または予測要求（Dictionary）]
#   戻り値: [result: 契約の結果と不変性の観測（Dictionary）]
# }
func _run_case(request: Dictionary) -> Dictionary:
	# JSONで表せないNaN/Infだけをテストプローブ側で注入する。
	for special: Dictionary in request.get("special", []):
		request[special["target"]][special["field"]] = NAN if special["value"] == "nan" else INF
	var before := JSON.stringify(request)
	var result := _invoke_contract(request)
	var original: Dictionary = result.duplicate(true)
	# 呼出元が返却値を編集しても、再実行や元の定義に影響しないことを観測する。
	if result.get("skill") is Dictionary:
		result["skill"]["power"] = -999
	result["remaining_hp"] = -999
	return {"result": original, "input_preserved": before == JSON.stringify(request),
		"result_independent": original == _invoke_contract(request)}


# {
#   責務: [_invoke_contract: ケースの意味に対応する純粋APIを選んで呼び出す]
#   処理: [1: prepareとquoteの呼出先を選ぶ]
#   引数: [request: ケースの入力（Dictionary）]
#   戻り値: [result: 契約の結果、またはプローブ操作の拒否（Dictionary）]
# }
func _invoke_contract(request: Dictionary) -> Dictionary:
	# 未対応のプローブ操作を、成立した予測の結果へ置き換えない。
	match request.get("operation"):
		"prepare":
			return Contract.prepare(request.get("document"), request.get("skill_id"))
		"quote":
			return Contract.quote_damage(request.get("definition"), request.get("request"))
	return {"ok": false, "reason": "invalid_probe_operation"}


# {
#   責務: [_measure_quote: I/Oと定義選択を除き、固定入力の予測API一回分の中央値を測る]
#   処理: [
#     1: 固定fixtureを検証する
#     2: warmup後に予測を反復する
#     3: 予測結果と中央値を返す
#   ]
#   引数: [payload: iterations/samples/warmup（Dictionary）]
#   戻り値: [result: 時間・反復条件・入力不変と実際の予測結果（Dictionary）]
# }
func _measure_quote(payload: Dictionary) -> Dictionary:
	# 同じ入力を繰り返す。MP/HPを変更するSessionの性能とは区別する。
	var definition := {"id": "weaken", "display_name": "ちからぬき", "kind": "magic", "mp_cost": 5, "power": 0.55, "element": "mental"}
	var request := {"magic": 100, "current_mp": 10, "target_hp": 1000, "target_max_hp": 1000,
		"target_resistances": {"mental": "normal"}, "guard": 0.5, "variance": 1.0}
	var before := JSON.stringify([definition, request])
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	for index in warmup:
		Contract.quote_damage(definition, request)
	# 起動・読み取り・warmupを計測から除外し、各sampleは同じ条件で実行する。
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			Contract.quote_damage(definition, request)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "input_preserved": before == JSON.stringify([definition, request]), "quote": Contract.quote_damage(definition, request),
		"current_mp": request["current_mp"], "target_hp": request["target_hp"]}
