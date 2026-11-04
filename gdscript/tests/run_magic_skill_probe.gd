# {
#   責務: [run_magic_skill_probe: 専用要求JSONで魔法・HP回復・速度強化の純粋予測と入力保持・独立コピー・性能を検証します]
#   フィールド: []
# }
extends SceneTree

const Contract = preload("res://engine/magic_skill_contract.gd")
const SelfDamageContract = preload("res://engine/self_damage_magic_contract.gd")
const DrainMpContract = preload("res://engine/drain_mp_skill_contract.gd")
const HealContract = preload("res://engine/heal_skill_contract.gd")
const SpeedBuffContract = preload("res://engine/speed_buff_contract.gd")


# {
#   責務: [_initialize: コマンドラインの専用JSONから、選択したスキル予測の検証結果を出力します]
#   処理: [
#     1: 専用要求JSONをコマンドライン引数のパスから読みます
#     2: 専用JSONで選択したスキル契約のケース検証または性能測定を呼びます
#     3: 観測結果をBase64のJSONとして標準出力へ出します
#   ]
#   引数: []
#   戻り値: [result: なし（void）。要求形式の失敗時は非ゼロで終了します]
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
#   責務: [_run_case: 魔法・HP回復・速度強化の一要求について、拒否・入力保持・結果独立性を検証します]
#   処理: [
#     1: JSONで表せないNaNまたは無限大を専用要求へ注入します
#     2: 専用要求で選択した魔法・HP回復・速度強化の純粋APIを呼びます
#     3: 返却値を改変した後に再実行し、元の定義と予測が変わらないことを確認します
#   ]
#   引数: [request: prepare/quote操作と定義または数値要求。speed_buffだけはchoose_duration操作で期間条件と抽選値も受け付けます。self_damage・drain_mp・heal・speed_buffは各専用契約を選びます（Dictionary）]
#   戻り値: [result: 選択した契約の予測または拒否と、入力保持・結果独立性の観測（Dictionary）]
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
		if result["skill"].has("mp_power"):
			result["skill"]["mp_power"] = -999
		if result["skill"].has("heal_ratio"):
			result["skill"]["heal_ratio"] = -999
		if result["skill"].get("duration") is Array:
			result["skill"]["duration"][0] = -999
	if result.get("duration") is Dictionary:
		result["duration"]["minimum"] = -999
	result["remaining_hp"] = -999
	result["remaining_actor_hp"] = -999
	for field in ["remaining_mp", "remaining_target_mp", "drained_mp", "recovered_mp", "heal_amount", "healed"]:
		result[field] = -999
	return {"result": original, "input_preserved": before == JSON.stringify(request),
		"result_independent": original == _invoke_contract(request)}


# {
#   責務: [_invoke_contract: 専用要求の魔法・HP回復・速度強化区分と操作名から、純粋契約のAPIへ委譲します]
#   処理: [1: 契約区分を一意に確認し、prepareまたは対応する予測APIを呼びます]
#   引数: [request: prepare/quote操作と定義または数値要求。speed_buffだけはchoose_duration操作も選べます。self_damage・drain_mp・heal・speed_buffの複数同時指定は拒否します（Dictionary）]
#   戻り値: [result: 選択した純粋契約の結果、または未対応のプローブ操作名に対する拒否（Dictionary）]
# }
func _invoke_contract(request: Dictionary) -> Dictionary:
	# 未対応のプローブ操作を、成立した予測の結果へ置き換えない。
	if int(request.get("self_damage", false)) + int(request.get("drain_mp", false)) + int(request.get("heal", false)) + int(request.get("speed_buff", false)) > 1:
		return {"ok": false, "reason": "invalid_probe_contract"}
	if request.get("speed_buff", false):
		match request.get("operation"):
			"prepare":
				return SpeedBuffContract.prepare(request.get("document"), request.get("skill_id"))
			"quote":
				return SpeedBuffContract.quote_buff(request.get("definition"), request.get("request"))
			"choose_duration":
				return SpeedBuffContract.choose_duration(request.get("condition"), request.get("request"))
		return {"ok": false, "reason": "invalid_probe_operation"}
	if request.get("heal", false):
		match request.get("operation"):
			"prepare":
				return HealContract.prepare(request.get("document"), request.get("skill_id"))
			"quote":
				return HealContract.quote_heal(request.get("definition"), request.get("request"))
		return {"ok": false, "reason": "invalid_probe_operation"}
	var contract = SelfDamageContract if request.get("self_damage", false) else Contract
	if request.get("drain_mp", false):
		contract = DrainMpContract
	match request.get("operation"):
		"prepare":
			return contract.prepare(request.get("document"), request.get("skill_id"))
		"quote":
			return contract.quote_damage(request.get("definition"), request.get("request"))
	return {"ok": false, "reason": "invalid_probe_operation"}


# {
#   責務: [_measure_quote: I/Oと定義選択を除き、固定入力で魔法・HP回復・速度強化の予測一回の中央値を測ります]
#   処理: [
#     1: 契約の種類に対応する固定定義と数値要求を用意します
#     2: 事前実行後に同じ予測APIを反復して計測します
#     3: 実際の数値予測・元資源の保持・一回分の時間中央値を返します
#   ]
#   引数: [payload: iterations・samples・warmupと一意な契約区分。speed_buffは速度強化を選びます（Dictionary）]
#   戻り値: [result: 時間・反復条件・入力不変と実際の予測結果（Dictionary）]
# }
func _measure_quote(payload: Dictionary) -> Dictionary:
	# 同じ入力を繰り返す。MP/HPを変更するSessionの性能とは区別する。
	if int(payload.get("self_damage", false)) + int(payload.get("drain_mp", false)) + int(payload.get("heal", false)) + int(payload.get("speed_buff", false)) > 1:
		return {"ok": false, "reason": "invalid_probe_contract"}
	var definition := {"id": "weaken", "display_name": "ちからぬき", "kind": "magic", "mp_cost": 5, "power": 0.55, "element": "mental"}
	var request := {"magic": 100, "current_mp": 10, "target_hp": 1000, "target_max_hp": 1000,
		"target_resistances": {"mental": "normal"}, "guard": 0.5, "variance": 1.0}
	# 魔法区分ごとに計測条件だけを変え、予測の測定ループと入力保持検査は共用する。
	var contract = SelfDamageContract if payload.get("self_damage", false) else Contract
	if payload.get("self_damage", false):
		definition = {"id": "metal_burst", "display_name": "メタルバースト", "kind": "magic",
			"mp_cost": 18, "power": 2.0, "element": "metal", "self_damage_ratio": 0.1}
		request.merge({"current_mp": 20, "actor_hp": 100, "actor_max_hp": 200,
			"target_resistances": {"metal": "normal"}}, true)
	if payload.get("drain_mp", false):
		contract = DrainMpContract
		definition = {"id": "possess", "display_name": "とりつく", "kind": "drain_mp",
			"mp_cost": 5, "power": 0.25, "element": "mental", "mp_power": 0.14}
		request.merge({"actor_max_mp": 30, "target_mp": 80}, true)
	# 反復ループと診断を共用し、HP回復区分だけがquote_healを呼ぶ。
	var quote: Callable = contract.quote_damage
	if payload.get("heal", false):
		quote = HealContract.quote_heal
		definition = {"id": "small_heal", "display_name": "小回復", "kind": "heal", "mp_cost": 6, "heal_ratio": 0.22}
		request = {"current_mp": 10, "target_hp": 900, "target_max_hp": 1000}
	if payload.get("speed_buff", false):
		quote = SpeedBuffContract.quote_buff
		definition = {"id": "piora", "display_name": "ピオラ", "kind": "buff", "speed_multiplier": 1.5,
			"duration": [3, 6], "mp_cost": 5}
		request = {"current_mp": 10}
	var before := JSON.stringify([definition, request])
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	for index in warmup:
		quote.call(definition, request)
	# 起動・読み取り・warmupを計測から除外し、各sampleは同じ条件で実行する。
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			quote.call(definition, request)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "input_preserved": before == JSON.stringify([definition, request]), "quote": quote.call(definition, request),
		"current_mp": request["current_mp"], "target_hp": request.get("target_hp"), "actor_hp": request.get("actor_hp"),
		"actor_max_mp": request.get("actor_max_mp"), "target_mp": request.get("target_mp")}
