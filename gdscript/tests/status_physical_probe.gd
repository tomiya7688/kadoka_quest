# {
#   責務: [status_physical_probe: 付与付き物理の定義/準備/予測と入力独立性を、専用ケースと反復性能で観測します]
#   フィールド: []
# }
extends RefCounted

const Contract = preload("res://engine/status_physical_skill_contract.gd")
const Copies = preload("res://tests/session_status_probe.gd")


# {
#   責務: [run: 専用ケースごとの純粋契約観測または固定一予測の性能測定へ委譲します]
#   処理: [1: performanceなら計測し、その他は独立したケースを順に観測します]
#   引数: [payload: casesまたはiterations/samples/warmupを持つ開発用要求（Dictionary）]
#   戻り値: [result: ケース観測または性能/固定原本/実予測（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	# 起動/I/Oは共用入口へ任せ、ここでは純粋APIの観測だけを担当します。
	if payload.get("performance", false):
		return _measure(payload)
	var results: Array = []
	for entry: Dictionary in payload.get("cases", []):
		results.append(_case(entry))
	return {"results": results}


# {
#   責務: [_case: 専用コピーへnative不正値を注入し、要求不変と返却ネストの独立性を検査します]
#   処理: [1: 注入前のコピーを保持し、API/返却編集/再呼出しの後に注入を戻して原本と照合します]
#   引数: [entry: operation/definition/request/document/skill_idと任意specialの専用ケース（Dictionary）]
#   戻り値: [result: API結果とinput_preserved/result_independent（Dictionary）]
# }
static func _case(entry: Dictionary) -> Dictionary:
	var input: Dictionary = entry.duplicate(true)
	var before := JSON.stringify(input)
	var holder: Dictionary = {}
	var field := ""
	var had := false
	var prior: Variant
	var cycle: Dictionary = {}
	# JSONへ保存できない値は要求コピーだけに作り、循環は観測後に解きます。
	if input.has("special"):
		var special: Dictionary = input["special"]
		field = special["field"]
		var definition: Dictionary = input["document"]["skills"][0] if input.get("operation") == "prepare" else input["definition"]
		holder = input["request"] if special.get("target", "effect") == "request" else definition["status_effect"]
		had = holder.has(field)
		prior = holder.get(field)
		var value: Variant = NAN
		match special["value"]:
			"inf": value = INF
			"object": value = RefCounted.new()
			"non_string_key": value = {1: "invalid"}
			"cycle":
				cycle["self"] = cycle
				value = cycle
		holder[field] = value
	var result := _invoke(input)
	var original := result.duplicate(true)
	Copies._mutate(result)
	var independent := original == _invoke(input)
	cycle.clear()
	if not field.is_empty():
		if had:
			holder[field] = prior
		else:
			holder.erase(field)
	return {"result": original, "input_preserved": before == JSON.stringify(input), "result_independent": independent}


# {
#   責務: [_invoke: 専用操作を付与付き物理の定義準備/判定準備/結果予測へ渡します]
#   処理: [1: 対応する三入口へ委譲し、未知の操作は拒否します]
#   引数: [input: operationと対応する定義/要求を持つ専用ケース（Dictionary）]
#   戻り値: [result: 指定契約の結果またはinvalid_probe_operation（Dictionary）]
# }
static func _invoke(input: Dictionary) -> Dictionary:
	match input.get("operation"):
		"prepare": return Contract.prepare(input.get("document"), input.get("skill_id"))
		"prepare_quote": return Contract.prepare_quote(input.get("definition"), input.get("request"))
		"quote": return Contract.quote_damage(input.get("definition"), input.get("request"))
	return {"ok": false, "reason": "invalid_probe_operation"}


# {
#   責務: [_measure: 非致死の物理ダメージと出血成功の純粋予測を、固定原本を変更せず反復測定します]
#   処理: [1: 事前実行後に複数サンプルを測り、中央値と最後の実予測/固定入力/原本保持を返します]
#   引数: [payload: iterations/samples/warmupの計測条件（Dictionary）]
#   戻り値: [result: 一予測の中央値・回数・固定原本・統合予測・入力保持（Dictionary）]
# }
static func _measure(payload: Dictionary) -> Dictionary:
	var definition := {"id": "mod_status_hit", "display_name": "計測用付与打撃", "kind": "physical", "mp_cost": 3,
		"status_effect": {"id": "bleeding", "display_name": "出血", "chance": 0.4,
			"metadata": {"deck": ["a", {"kept": true}]}}}
	var request := {"attack": 100, "defense": 50, "target_hp": 1000, "current_mp": 100,
		"critical_roll": 0.5, "variance": 1.0, "status_resistance_level": "weak", "status_roll": 0.49,
		"status_effects": [{"id": "lock", "removable": false}, "poison", {"id": "mod", "metadata": {"deck": [1]}}]}
	var before := JSON.stringify([definition, request])
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	# 致死/重複/拒否だけの高速経路で反復せず、毎回非致死ダメージと一件成功を予測します。
	for index in warmup:
		Contract.quote_damage(definition, request)
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			Contract.quote_damage(definition, request)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples, "warmup": warmup,
		"definition": definition.duplicate(true), "request": request.duplicate(true), "quote": Contract.quote_damage(definition, request),
		"input_preserved": before == JSON.stringify([definition, request])}
