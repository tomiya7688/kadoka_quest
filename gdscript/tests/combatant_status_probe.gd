# {
#   責務: [combatant_status_probe: 共用起動プローブから状態一覧の所有・予測非変更・一件更新・拒否・性能を観測します]
#   フィールド: []
# }
extends RefCounted

const StatusState = preload("res://engine/combatant_status_state.gd")


# {
#   責務: [run: 状態保持専用のケース観測またはライフサイクル計測を選び、ファイルI/Oなしで返します]
#   処理: [1: performance=trueなら計測、その他は各ケースの独立状態所有者を観測します]
#   引数: [payload: JSON由来のケース一覧または反復条件（Dictionary）]
#   戻り値: [result: ケース観測一覧または性能結果（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	if payload.get("performance", false):
		return _measure(payload)
	var results: Array = []
	for request: Dictionary in payload.get("cases", []):
		results.append(_run_case(request))
	return {"results": results}


# {
#   責務: [_run_case: 一つの状態所有者で開始・連続操作を実行し、原本保持と返却値の独立性を観測します]
#   処理: [
#     1: 専用コピーの初期一覧へ任意の非JSON値を注入し、開始を検証します
#     2: 入力/返却一覧の編集が所有状態に伝播しないことを確認して各操作を観測します
#   ]
#   引数: [request: effects・任意initialize=falseとstart/quote/cure/snapshotのsteps配列（Dictionary）]
#   戻り値: [result: 開始/操作結果と原本保持・独立性の観測（Dictionary）]
# }
static func _run_case(request: Dictionary) -> Dictionary:
	var before := JSON.stringify(request)
	var copied: Dictionary = request.duplicate(true)
	var effects: Variant = copied.get("effects")
	# 原本JSONへ非有限値や循環を保存せず、検証専用のコピーだけへ注入します。
	var cyclic: Dictionary = {}
	if copied.has("special_effect"):
		var special: Dictionary = copied["special_effect"]
		var value: Variant = NAN if special["value"] == "nan" else INF
		if special["value"] == "object":
			value = RefCounted.new()
		if special["value"] == "cycle":
			cyclic["self"] = cyclic
			value = cyclic
		effects[special.get("index", 0)][special["field"]] = value
	var state := StatusState.new()
	var started: Variant = state.start(effects) if copied.get("initialize", true) else null
	cyclic.clear()
	var initial := state.snapshot()
	_mutate_effects(effects)
	_mutate_result(started)
	var initial_independent := state.snapshot() == initial
	var observations: Array = []
	for step: Dictionary in copied.get("steps", []):
		observations.append(_observe_step(state, step))
	return {"started": {"ok": true, "snapshot": initial} if started is Dictionary and started.get("ok", false) else started,
		"initial_independent": initial_independent, "input_preserved": before == JSON.stringify(request),
		"steps": observations, "snapshot": state.snapshot()}


# {
#   責務: [_observe_step: 一操作の前後状態と独立結果を取得し、返却値を編集して所有状態保持を確認します]
#   処理: [1: 操作を実行し、独立結果を保存して返却値/読み取りsnapshotを編集し、所有状態を再照合します]
#   引数: [
#     state: ケースごとに独立した状態一覧の所有者（RefCounted）
#     step: start/quote/cure/snapshotの操作と入力、任意specialによる要求値注入（Dictionary）
#   ]
#   戻り値: [result: 操作結果・前後snapshotと返却値の独立性（Dictionary）]
# }
static func _observe_step(state: RefCounted, step: Dictionary) -> Dictionary:
	var before: Dictionary = state.snapshot()
	var result := _invoke(state, step)
	var original := result.duplicate(true)
	var after: Dictionary = state.snapshot()
	_mutate_result(result)
	var readback: Dictionary = state.snapshot()
	_mutate_result(readback)
	return {"result": original, "before": before, "after": after, "result_independent": state.snapshot() == after}


# {
#   責務: [_invoke: ケース操作を状態保持の公開APIへ委譲し、専用要求コピーへ非有限値を注入します]
#   処理: [1: start/snapshot/quote/cureを振り分け、未知操作はプローブの拒否理由を返します]
#   引数: [
#     state: 初期化状態と順序付き一覧を持つ所有者（RefCounted）
#     step: 操作名と対応入力（Dictionary）
#   ]
#   戻り値: [result: 公開APIの結果、または未知操作の拒否（Dictionary）]
# }
static func _invoke(state: RefCounted, step: Dictionary) -> Dictionary:
	if step.get("operation") == "start":
		return state.start(step.get("effects"))
	if step.get("operation") == "snapshot":
		return state.snapshot()
	var request: Variant = step.get("request")
	if step.has("special"):
		request = request.duplicate(true)
		request[step["special"]["field"]] = NAN if step["special"]["value"] == "nan" else INF
	match step.get("operation"):
		"quote":
			return state.quote_cure(request)
		"cure":
			return state.cure(request)
	return {"ok": false, "reason": "invalid_probe_operation"}


# {
#   責務: [_mutate_result: 観測専用の返却辞書内の状態一覧を編集し、所有者との共有を検出します]
#   処理: [1: snapshot内と治療結果の一覧へ同じ編集検査を適用します]
#   引数: [result: 編集して独立性を確かめる観測用返却値（Variant）]
#   戻り値: [result: なし（void）]
# }
static func _mutate_result(result: Variant) -> void:
	if not result is Dictionary:
		return
	if result.get("snapshot") is Dictionary:
		_mutate_result(result["snapshot"])
	for field in ["status_effects", "remaining_status_effects"]:
		_mutate_effects(result.get(field))


# {
#   責務: [_mutate_effects: 専用配列とネスト情報を編集し、原本/返却値が所有一覧と共有されていないか確認します]
#   処理: [1: 状態IDとmetadata.deckを編集し、外側の一覧へ要素を追加します]
#   引数: [effects: 観測用の状態配列。配列以外は編集しません（Variant）]
#   戻り値: [result: なし（void）]
# }
static func _mutate_effects(effects: Variant) -> void:
	if not effects is Array:
		return
	for effect in effects:
		if effect is Dictionary:
			effect["id"] = "changed"
			if effect.get("metadata") is Dictionary and effect["metadata"].get("deck") is Array:
				effect["metadata"]["deck"].append("changed")
	effects.append("changed")


# {
#   責務: [_cycle: 新しい状態所有者で4件の開始・予測・一件更新・読み取りまでを実行します]
#   処理: [1: 初期化から予測前後のsnapshotと治療後snapshotを取得し、独立した計測観測を返します]
#   引数: [
#     effects: 解除不可2件・毒・眠りの固定状態一覧（Array）
#     request: 治療確率0.03と判定値0.02の固定要求（Dictionary）
#   ]
#   戻り値: [result: 開始・予測・治療結果と前後一覧（Dictionary）]
# }
static func _cycle(effects: Array, request: Dictionary) -> Dictionary:
	# 各反復で候補を新規初期化し、治療済み/候補なしの速い経路へ偏らせません。
	var state := StatusState.new()
	var started := state.start(effects)
	var predicted := state.quote_cure(request)
	var after_quote := state.snapshot()
	var applied := state.cure(request)
	return {"started": started, "prediction": predicted, "after_quote": after_quote,
		"quote": applied, "after": state.snapshot()}


# {
#   責務: [_measure: 新しい4状態の開始・予測・一件治療・読み取りライフサイクルの中央値を測ります]
#   処理: [1: 起動/I/O/事前実行を除く反復の中央値と、最後の実更新結果・原本保持を返します]
#   引数: [payload: iterations・samples・warmupの計測条件（Dictionary）]
#   戻り値: [result: 一回中央値と、開始/予測/治療/読み取りが成立した観測（Dictionary）]
# }
static func _measure(payload: Dictionary) -> Dictionary:
	var effects: Array = [{"id": "lock_a", "removable": false, "metadata": {"deck": ["a"]}},
		{"id": "lock_b", "removable": false},
		{"id": "poison", "display_name": "毒", "metadata": {"deck": ["b", {"kept": true}]}}, "sleep"]
	var request := {"cure_chance": 0.03, "roll": 0.02}
	var before := JSON.stringify([effects, request])
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	for index in warmup:
		_cycle(effects, request)
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_cycle(effects, request)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	var result := _cycle(effects, request)
	result.merge({"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "input_preserved": before == JSON.stringify([effects, request]),
		"original_effects": effects.duplicate(true)})
	return result
