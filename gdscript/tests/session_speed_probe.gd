# {
#   責務: [session_speed_probe: 参加者速度集合・Session・Applicationの開始と独立読取・行動順を保存なしで観測します]
#   フィールド: []
# }
extends RefCounted
const Roster = preload("res://engine/battle_speed_state.gd")
const Session = preload("res://engine/battle_session.gd")
const Application = preload("res://application/battle_session_application.gd")
const Repository = preload("res://data/content_repository.gd")
const Shared = preload("res://tests/session_status_probe.gd")


# {
#   責務: [run: 速度保持接続の各ケースを独立した所有者で実行します]
#   処理: [1: ケースごとに開始/操作とコピー保持を観測します]
#   引数: [payload: cases配列を含む専用要求（Dictionary）]
#   戻り値: [result: 各ケースの観測results（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	var results: Array = []
	for request: Dictionary in payload["cases"]:
		results.append(_case(request))
	return {"results": results}


# {
#   責務: [_case: 専用コピーから開始し、操作結果と元入力・速度状態の非共有を記録します]
#   処理: [1: コピーに不正な非JSON値を注入し、各製品APIの結果と読取編集後の保持を照合します]
#   引数: [request: mode/snapshotsまたはrecords・初期状態/倍率・stepsの専用条件（Dictionary）]
#   戻り値: [result: 開始/各操作/最終状態と入力保持の観測（Dictionary）]
# }
static func _case(request: Dictionary) -> Dictionary:
	var before := JSON.stringify(request)
	var input := request.duplicate(true)
	var mode: String = input.get("mode", "session")
	var owner: RefCounted
	match mode:
		"collection": owner = Roster.new()
		"application": owner = Application.new(Repository.new(input["project_root"]))
		_: owner = Session.new()
	# 非有限値とエンジンObjectをJSONの代用品へ変換せず、APIへ直接渡して拒否を観測します。
	if input.has("special"):
		var value: Variant = NAN
		match input["special"]:
			"inf": value = INF
			"object": value = RefCounted.new()
		input["initial_speed_multipliers"]["enemies"]["same"] = value
	var started: Dictionary = {} if input.get("no_start", false) else _start(owner, input, mode)
	var initial := started.duplicate(true)
	var steps: Array = []
	for step: Dictionary in input.get("steps", []):
		var old := _view(owner, mode)
		var step_before := JSON.stringify(step)
		var result: Dictionary
		match step["operation"]:
			"edit_step_ticket":
				_mutate(input["steps"][int(step["index"])]["ticket"])
				result = {"ok": true}
			"speed_apply": result = _apply_speed(owner, step, mode)
			"start": result = _start(owner, step.get("input", input), mode)
			"speed": result = owner.read(step.get("actor")) if mode == "collection" else owner.speed(step.get("actor"))
			"speeds": result = owner.snapshot() if mode == "collection" else owner.speeds()
			"multipliers": result = owner.multipliers()
			"defend_action":
				var ticket: Dictionary = owner.snapshot()["pending"]["ticket"]
				result = owner.resolve_basic_defend({"ticket": ticket, "skill_id": "defend"})
			_: result = Shared._execute(owner, null, step, input)
		var after := _view(owner, mode)
		var copied := result.duplicate(true)
		_mutate(result)
		steps.append({"result": copied, "state": after, "unchanged": old == after,
			"independent": after == _view(owner, mode), "request_preserved": step_before == JSON.stringify(step)})
	# 初期入力と三キー読取を編集しても、速度所有者や数値資源へ変更を伝播させません。
	var owned := _view(owner, mode)
	var single: Dictionary = owner.read({"side": "allies", "id": "same"}) if mode == "collection" else owner.speed({"side": "allies", "id": "same"})
	_mutate(single)
	_mutate(started)
	_mutate(input)
	var edited := _view(owner, mode)
	_mutate(edited)
	return {"started": initial, "steps": steps, "state": _view(owner, mode),
		"source_independent": owned == _view(owner, mode), "input_preserved": before == JSON.stringify(request)}


# {
#   責務: [_start: 速度集合・Session・Applicationの実開始APIへケースの初期条件を渡します]
#   処理: [1: 集合は倍率だけ、Session/Applicationは状態と任意初期倍率を渡し、legacy指定は従来入口を使います]
#   引数: [
#     owner: 観測する新規所有者または開始失敗後の所有者（RefCounted）
#     input: snapshotsまたはrecordsと初期状態/倍率の専用コピー（Dictionary）
#     mode: collection/session/applicationの開始先区分（String）
#   ]
#   戻り値: [result: 製品APIが返す開始結果（Dictionary）]
# }
static func _start(owner: RefCounted, input: Dictionary, mode: String) -> Dictionary:
	var multipliers: Variant = input.get("initial_speed_multipliers")
	if mode == "collection":
		return owner.start(input.get("snapshots"), multipliers)
	var teams: Dictionary = input["records"] if mode == "application" else input["snapshots"]
	if mode == "application":
		if input.get("legacy", false):
			return owner.start(teams["allies"], teams["enemies"], input["order"])
		return owner.start_with_statuses(teams["allies"], teams["enemies"], input["order"], input.get("initial_statuses"), multipliers)
	if input.get("legacy", false):
		return owner.start(teams.get("allies"), teams.get("enemies"))
	return owner.start_with_statuses(teams.get("allies"), teams.get("enemies"), input.get("initial_statuses"), multipliers)


# {
#   責務: [_apply_speed: コピー要求を速度集合または取得済み予約付きSessionの実APIへ渡します]
#   処理: [1: 不正native値は要求コピーだけへ注入し、指定対象と現在票を製品APIへ渡します]
#   引数: [
#     owner: 実行する速度集合またはSession（RefCounted）
#     step: target/requestと任意ticket/update_special/special_fieldの観測条件（Dictionary）
#     mode: collection/session/applicationの区分。Applicationの低水準操作は拒否します（String）
#   ]
#   戻り値: [result: 実付与結果またはApplication低水準操作の観測側拒否（Dictionary）]
# }
static func _apply_speed(owner: RefCounted, step: Dictionary, mode: String) -> Dictionary:
	# 乱数や生存状態をプローブ側で補完せず、native不正値だけを専用コピーへ作ります。
	var request: Variant = step.get("request")
	if step.has("update_special"):
		request = request.duplicate(true)
		var value: Variant = NAN
		match step["update_special"]:
			"inf": value = INF
			"object": value = RefCounted.new()
		request[step.get("special_field", "multiplier")] = value
	if mode == "collection":
		return owner.apply_multiplier(step.get("target"), request)
	if mode == "application":
		return {"ok": false, "reason": "low_level_session_required"}
	var pending: Variant = owner.snapshot()["pending"]
	var ticket: Variant = step.get("ticket", pending["ticket"] if pending is Dictionary else null)
	return owner.apply_speed_multiplier(ticket, step.get("target"), request)


# {
#   責務: [_view: 所有者の全速度と、存在する場合の数値/状態/防御を独立読取として集めます]
#   処理: [1: 集合は速度だけ、Session/Applicationは公開読取APIのコピーを返します]
#   引数: [
#     owner: 実APIを呼ぶ速度集合または戦闘所有者（RefCounted）
#     mode: collection/session/applicationの観測区分（String）
#   ]
#   戻り値: [result: speedsと任意numeric/statuses/guardsの観測（Dictionary）]
# }
static func _view(owner: RefCounted, mode: String) -> Dictionary:
	# 戦闘以外の集合に数値資源APIを要求せず、各区分の公開読取だけで保持を比較します。
	if mode == "collection":
		return {"speeds": owner.snapshot()}
	return {"speeds": owner.speeds(), "numeric": owner.snapshot(), "statuses": owner.statuses(), "guards": owner.effects()}


# {
#   責務: [_mutate: 速度倍率を含む返却値と専用入力のネストを編集し、参照共有を検出します]
#   処理: [1: 辞書のスカラーと配列を再帰編集し、所有者を直接変更せずに独立性を検査します]
#   引数: [value: 循環を含まない専用入力または返却コピー（Variant）]
#   戻り値: [result: なし（void）。渡されたコピーだけを編集します]
# }
static func _mutate(value: Variant) -> void:
	if value is Dictionary:
		for field in value.keys():
			if value[field] is Dictionary or value[field] is Array:
				_mutate(value[field])
			else:
				value[field] = "edited"
	elif value is Array:
		for entry in value:
			_mutate(entry)
		value.clear()
