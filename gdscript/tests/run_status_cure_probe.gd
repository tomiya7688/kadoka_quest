# {
#   責務: [run_status_cure_probe: 専用JSONから治療/付与/能力値/行動順予測・個体/Session状態・回復準備/実行を起動し、拒否/独立性/性能を観測します]
#   フィールド: []
# }
extends SceneTree

const StatusStatProbe = preload("res://tests/status_stat_probe.gd")
const StatusTurnProbe = preload("res://tests/status_turn_order_probe.gd")
const StatusPhysicalPreflightProbe = preload("res://tests/status_physical_preflight_probe.gd")
const StatusPhysicalContextProbe = preload("res://tests/status_physical_context_probe.gd")
const StatusPhysicalProbe = preload("res://tests/status_physical_probe.gd")
const RosterApplyProbe = preload("res://tests/battle_status_apply_probe.gd")
const ApplyProbe = preload("res://tests/status_apply_probe.gd")
const Contract = preload("res://engine/status_cure_contract.gd")
const CureHealContract = preload("res://engine/cure_heal_skill_contract.gd")
const StatusStateProbe = preload("res://tests/combatant_status_probe.gd")
const ContextProbe = preload("res://tests/cure_heal_context_probe.gd")
const SessionStatusProbe = preload("res://tests/session_status_probe.gd")
const CureActionProbe = preload("res://tests/cure_heal_action_probe.gd")


# {
#   責務: [_initialize: 専用要求JSONを読み、治療/付与/能力値/行動順補正・個体状態・準備選択・Session保持の観測を標準出力へ返します]
#   処理: [1: 要求区分に応じた専用ヘルパーへ委譲し、Base64のJSONを出力します]
#   引数: []
#   戻り値: [result: なし（void）。引数またはJSON形式不正は終了コード2です]
# }
func _initialize() -> void:
	# 利用者セーブや正規data/assetsへの書き込み先を持たず、専用要求を読みます。
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		quit(2)
		return
	var payload: Variant = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	if not payload is Dictionary:
		quit(2)
		return
	var result: Dictionary
	if payload.get("status_turn_order", false):
		result = StatusTurnProbe.run(payload)
	elif payload.get("status_physical_action", false):
		result = StatusPhysicalPreflightProbe.run(payload)
	elif payload.get("status_stats", false):
		result = StatusStatProbe.run(payload)
	elif payload.get("status_physical_preflight", false):
		result = StatusPhysicalPreflightProbe.run(payload)
	elif payload.get("status_physical_context", false):
		result = StatusPhysicalContextProbe.run(payload)
	elif payload.get("status_physical", false):
		result = StatusPhysicalProbe.run(payload)
	elif payload.get("session_status_apply", false):
		result = SessionStatusProbe.run(payload)
	elif payload.get("roster_status_apply", false):
		result = RosterApplyProbe.run(payload)
	elif payload.get("status_apply", false):
		result = ApplyProbe.run(payload)
	elif payload.get("cure_action", false):
		result = CureActionProbe.run(payload)
	elif payload.get("session_status", false):
		result = SessionStatusProbe.run(payload)
	elif payload.get("cure_context", false):
		result = ContextProbe.run(payload)
	elif payload.get("status_state", false):
		result = StatusStateProbe.run(payload)
	elif payload.get("performance", false):
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
#   引数: [request: 治療単体select/quoteまたはcure_heal=trueのprepare/quote区分と入力、任意のspecial注入条件（Dictionary）]
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
			request[special.get("target", "request")][special["field"]] = value
	var before := JSON.stringify(request)
	var result := _invoke_contract(request)
	var original := result.duplicate(true)
	# 定義や数値結果の編集も原本へ伝播しないことを確認します。
	if result.get("skill") is Dictionary:
		result["skill"]["status_cure_chance"] = -999
	for field in ["remaining_hp", "remaining_mp"]:
		if result.has(field):
			result[field] = -999
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
#   責務: [_invoke_contract: ケースの操作名と明示区分を、治療単体または治療付き回復の純粋APIへ委譲します]
#   処理: [1: cure_heal=trueならprepare/quoteまたは専用の不正循環定義検証、その他は治療単体select/quoteへ委譲します]
#   引数: [request: 操作名・任意cure_heal区分と対応APIへ渡す入力（Dictionary）]
#   戻り値: [result: 純粋契約の結果、またはプローブの操作名拒否（Dictionary）]
# }
func _invoke_contract(request: Dictionary) -> Dictionary:
	if request.get("cure_heal", false):
		match request.get("operation"):
			"prepare":
				return CureHealContract.prepare(request.get("document"), request.get("skill_id"))
			"quote":
				return CureHealContract.quote_heal(request.get("definition"), request.get("request"))
			"quote_cyclic_definition":
				return _quote_cyclic_definition(request)
		return {"ok": false, "reason": "invalid_probe_operation"}
	match request.get("operation"):
		"select":
			return Contract.select_candidate(request.get("effects"))
		"quote":
			return Contract.quote_cure(request.get("request"))
	return {"ok": false, "reason": "invalid_probe_operation"}


# {
#   責務: [_quote_cyclic_definition: 型不正なdescriptionへ循環辞書を注入し、深いコピー前の拒否を検証します]
#   処理: [1: 要求原本を変えず循環定義を作り、純粋予測を呼び、専用循環を解いて結果を返します]
#   引数: [request: JSONから読み取った正常定義と回復要求（Dictionary）]
#   戻り値: [result: descriptionの型不正による理由付き拒否（Dictionary）]
# }
func _quote_cyclic_definition(request: Dictionary) -> Dictionary:
	# JSONファイルに循環を保存せず、直接APIの不正型を検証する専用プローブだけで作ります。
	var cyclic: Dictionary = {}
	cyclic["self"] = cyclic
	var definition: Dictionary = request["definition"].duplicate()
	definition["description"] = cyclic
	var result := CureHealContract.quote_heal(definition, request.get("request"))
	cyclic.clear()
	return result


# {
#   責務: [_measure_quote: 治療単体または最大HP制限付き治療回復一回の中央値を、入力を変えない固定ケースで測ります]
#   処理: [
#     1: 解除不可2件と毒・眠りを用意し、最初の解除可能な毒を明示判定で治療します
#     2: 起動・I/O・事前実行を除いて同じAPIを反復し、中央値と実際の予測を返します
#   ]
#   引数: [payload: iterations・samples・warmupと任意cure_heal=trueの計測区分（Dictionary）]
#   戻り値: [result: 時間中央値・条件・入力保持・治療成立結果と、回復付きならHP/MP結果（Dictionary）]
# }
func _measure_quote(payload: Dictionary) -> Dictionary:
	# 候補なしの高速な経路ではなく、解除不可を飛ばしてネスト付き候補を治す経路を測ります。
	var request := {"status_effects": [
		{"id": "lock_a", "removable": false, "metadata": {"deck": ["a"]}},
		{"id": "lock_b", "removable": false},
		{"id": "poison", "display_name": "毒", "metadata": {"deck": ["b", {"kept": true}]}}, "sleep"],
		"cure_chance": 0.03, "roll": 0.02}
	var definition := {"id": "spirit_recover", "display_name": "精霊回復", "kind": "heal",
		"mp_cost": 4, "heal_ratio": 0.03, "status_cure_chance": 0.03}
	var quote: Callable = Contract.quote_cure
	var arguments: Array = [request]
	if payload.get("cure_heal", false):
		request.erase("cure_chance")
		request.merge({"current_mp": 10, "target_hp": 990, "target_max_hp": 1000})
		quote = CureHealContract.quote_heal
		arguments = [definition, request]
	var before := JSON.stringify([definition, request])
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	for index in warmup:
		quote.callv(arguments)
	# タイマー内ではAPIのみを呼び、一覧の再生成やファイル出力を測りません。
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			quote.callv(arguments)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "input_preserved": before == JSON.stringify([definition, request]), "quote": quote.callv(arguments),
		"original_effects": request["status_effects"].duplicate(true), "original_definition": definition.duplicate(true),
		"original_request": request.duplicate(true)}
