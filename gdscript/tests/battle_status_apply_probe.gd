# {
#   責務: [battle_status_apply_probe: 参加者別状態集合の付与/治療・対象分離・拒否・コピー独立性と八体の性能を観測します]
#   フィールド: []
# }
extends RefCounted

const Roster = preload("res://engine/battle_status_state.gd")
const Mutator = preload("res://tests/session_status_probe.gd")


# {
#   責務: [run: 状態集合の独立ケース観測または八体の付与ライフサイクル計測へ委譲します]
#   処理: [1: performance区分を振り分け、通常ケースはそれぞれ新しい状態集合で観測します]
#   引数: [payload: casesまたはiterations/samples/warmupの開発用辞書（Dictionary）]
#   戻り値: [result: ケース観測一覧または性能と実更新結果（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	if payload.get("performance", false):
		return _measure(payload)
	var results: Array = []
	for entry: Dictionary in payload.get("cases", []):
		results.append(_case(entry))
	return {"results": results}


# {
#   責務: [_case: 新規参加者状態集合の開始/操作を観測し、原本と返却値の編集から所有状態を守るか確認します]
#   処理: [1: コピー入力で開始し、初期/要求/返却値を編集して各公開操作の前後状態と独立性を照合します]
#   引数: [entry: snapshots/initial_statuses/steps、任意no_start=trueの専用ケース（Dictionary）]
#   戻り値: [result: 開始・操作・最終状態と入力保持/初期コピー独立性（Dictionary）]
# }
static func _case(entry: Dictionary) -> Dictionary:
	var before := JSON.stringify(entry)
	var input: Dictionary = entry.duplicate(true)
	var roster := Roster.new()
	var started: Dictionary = {}
	if not input.get("no_start", false):
		started = roster.start(input.get("snapshots"), input.get("initial_statuses"))
	var initial := roster.snapshot()
	var original_start := started.duplicate(true)
	# 参加者数値と初期状態の返却/入力を編集しても、保持済み状態は変更できません。
	Mutator._mutate(started)
	Mutator._mutate(input.get("snapshots"))
	Mutator._mutate(input.get("initial_statuses"))
	var initial_independent := initial == roster.snapshot()
	var steps: Array = []
	for step: Dictionary in input.get("steps", []):
		var previous := roster.snapshot()
		var request_before := JSON.stringify(step)
		var result := _invoke(roster, step)
		var request_preserved := request_before == JSON.stringify(step)
		var original_result := result.duplicate(true)
		var after := roster.snapshot()
		Mutator._mutate(result)
		Mutator._mutate(step.get("request"))
		Mutator._mutate(step.get("key"))
		var readback := roster.snapshot()
		Mutator._mutate(readback)
		steps.append({"result": original_result, "before": previous, "after": after,
			"independent": after == roster.snapshot(), "request_preserved": request_preserved})
	return {"started": original_start, "initial": initial, "steps": steps, "snapshot": roster.snapshot(),
		"initial_independent": initial_independent, "input_preserved": before == JSON.stringify(entry)}


# {
#   責務: [_invoke: 専用操作を状態集合の公開APIへ渡し、native不正値はコピー要求だけへ注入します]
#   処理: [1: 任意の非有限/Object/循環を注入して指定APIを呼び、専用循環を解いて結果を返します]
#   引数: [
#     roster: ケースごとの参加者状態集合（RefCounted）
#     step: 操作名・key/requestと任意specialの注入先/値名（Dictionary）
#   ]
#   戻り値: [result: 指定公開APIの結果またはunknown操作の拒否（Dictionary）]
# }
static func _invoke(roster: RefCounted, step: Dictionary) -> Dictionary:
	var key: Variant = step.get("key")
	var request: Variant = step.get("request")
	var cyclic: Dictionary = {}
	if step.has("special"):
		key = key.duplicate(true) if key is Dictionary else key
		request = request.duplicate(true) if request is Dictionary else request
		var special: Dictionary = step["special"]
		var value: Variant = NAN
		match special["value"]:
			"inf": value = INF
			"object": value = RefCounted.new()
			"non_string_key": value = {1: "invalid"}
			"cycle":
				cyclic["self"] = cyclic
				value = cyclic
		match special.get("target", "request"):
			"key": key[special["field"]] = value
			"effect": request["effect"][special["field"]] = value
			_: request[special["field"]] = value
	var result: Dictionary
	match step.get("operation"):
		"start": result = roster.start(step.get("snapshots"), step.get("initial_statuses"))
		"snapshot": result = roster.snapshot()
		"read": result = roster.read(key)
		"cure": result = roster.cure(key, request)
		"prepare_application": result = roster.prepare_application(key, request)
		"quote_application": result = roster.quote_application(key, request)
		"apply": result = roster.apply(key, request)
		_: result = {"ok": false, "reason": "invalid_probe_operation"}
	cyclic.clear()
	return result


# {
#   責務: [_cycle: 八体で新規開始し、一体への準備/予測/実付与と重複/全体読取を実行します]
#   処理: [1: enemies/member_2だけへ出血を追加し、同ID再付与が重ならず他の七体が保持される観測を返します]
#   引数: [
#     snapshots: 同IDの両陣営各四体の固定六キー数値参加者（Dictionary）
#     statuses: 八体の固定初期状態（Dictionary）
#     request: 基礎確率0.4/weak耐性/roll0.49の固定出血要求（Dictionary）
#   ]
#   戻り値: [result: 開始/準備/予測/対象読取/実付与/重複/全体状態の観測（Dictionary）]
# }
static func _cycle(snapshots: Dictionary, statuses: Dictionary, request: Dictionary) -> Dictionary:
	# 反復ごとに八体を新規開始し、重複だけでなく実際の一件追加を毎回測ります。
	var roster := Roster.new()
	var started := roster.start(snapshots, statuses)
	var key := {"side": "enemies", "id": "member_2"}
	var preparation := request.duplicate()
	preparation.erase("roll")
	var prepared := roster.prepare_application(key, preparation)
	var prediction := roster.quote_application(key, request)
	var after_quote := roster.read(key)
	var applied := roster.apply(key, request)
	var repeated := roster.apply(key, preparation)
	return {"started": started, "prepared": prepared, "prediction": prediction, "after_quote": after_quote,
		"applied": applied, "repeated": repeated, "single": roster.read(key), "statuses": roster.snapshot()}


# {
#   責務: [_measure: 八体の新規保持から対象一体の付与/重複/読取までを原本非変更で反復測定します]
#   処理: [1: 固定八体を用意し、起動/I/O/事前実行を除く中央値と最後の実更新結果を返します]
#   引数: [payload: iterations/samples/warmupの計測条件（Dictionary）]
#   戻り値: [result: microseconds・actors8・条件・原本保持と固定入力/実観測（Dictionary）]
# }
static func _measure(payload: Dictionary) -> Dictionary:
	var snapshots := {"allies": [], "enemies": []}
	var statuses := {"allies": {}, "enemies": {}}
	var effects: Array = [{"id": "lock", "removable": false}, "poison",
		{"id": "mod", "metadata": {"deck": [1, {"kept": true}]}}]
	for side in ["allies", "enemies"]:
		for index in 4:
			var id := "member_" + str(index)
			snapshots[side].append({"identity": {"id": id, "species_id": "slime", "name": id},
				"stats": {"hp": 100, "mp": 100, "attack": 10, "defense": 10, "magic": 10, "speed": 10},
				"hp": 100, "mp": 100, "alive": true, "fled": false})
			statuses[side][id] = effects.duplicate(true)
	var request := {"effect": {"id": "bleeding", "display_name": "出血", "chance": 0.4,
		"metadata": {"deck": ["a", {"kept": true}]}}, "resistance_level": "weak", "roll": 0.49}
	var before := JSON.stringify([snapshots, statuses, request])
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	for index in warmup:
		_cycle(snapshots, statuses, request)
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_cycle(snapshots, statuses, request)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	var result := _cycle(snapshots, statuses, request)
	result.merge({"microseconds": timings[timings.size() / 2], "actors": 8, "iterations": iterations,
		"samples": samples, "warmup": warmup, "input_preserved": before == JSON.stringify([snapshots, statuses, request]),
		"original_snapshots": snapshots.duplicate(true), "original_statuses": statuses.duplicate(true),
		"original_request": request.duplicate(true)})
	return result
