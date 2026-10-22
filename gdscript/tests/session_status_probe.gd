# {
#   責務: [session_status_probe: 専用Session開始・予約付き治療/付与・状態読取・原本独立性・拒否後再試行を実Godotで観測します]
#   フィールド: []
# }
extends RefCounted
const Session = preload("res://engine/battle_session.gd")
const Context = preload("res://engine/cure_heal_skill_context.gd")
const Healing = preload("res://engine/heal_skill_action.gd")
const Benchmark = preload("res://tests/session_status_benchmark.gd")
const ApplyBenchmark = preload("res://tests/session_status_application_benchmark.gd")
const Updates = preload("res://tests/claimed_status_update_probe.gd")


# {
#   責務: [run: 状態保持/予約付き付与のケース一覧と対応する八体計測を専用ヘルパーへ委譲します]
#   処理: [1: performance指定を振り分け、通常ケースをそれぞれ新規Sessionで観測します]
#   引数: [payload: 専用要求JSONを復号したケース一覧または計測条件（Dictionary）]
#   戻り値: [result: ケース観測列または性能と実結果（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	if payload.get("performance", false):
		return ApplyBenchmark.new().measure(payload) if payload.get("session_status_apply", false) else Benchmark.measure(payload)
	var results: Array = []
	for request: Dictionary in payload.get("cases", []):
		results.append(_case(request))
	return {"results": results}


# {
#   責務: [_case: 新規Sessionの開始と連続操作を観測し、呼出元・返却値と所有状態の独立性を検査します]
#   処理: [
#     1: 専用入力をコピーし、任意の非JSON値を初期状態へ注入して開始します
#     2: 各操作の独立した観測を保持し、読取結果を編集して再読取と照合します
#   ]
#   引数: [request: snapshots・initial_statuses・steps、任意legacy/no_start/preparation/specialの専用ケース（Dictionary）]
#   戻り値: [result: 開始・操作・最終数値/状態と原本/返却値独立性の観測（Dictionary）]
# }
static func _case(request: Dictionary) -> Dictionary:
	var before := JSON.stringify(request)
	var input := request.duplicate(true)
	var session = Session.new()
	var prepared: Dictionary = {}
	if input.has("preparation"):
		var preparation: Dictionary = input["preparation"]
		prepared = Context.prepare(preparation["teams"], preparation["skills"], preparation["initial_statuses"])
		if not prepared["ok"]:
			return {"prepared": prepared}
		input["snapshots"] = prepared["snapshots"]
		input["initial_statuses"] = prepared["initial_statuses"]
	# 循環・Object・非有限値は専用コピーだけに作り、製品APIでの拒否を観測します。
	var cyclic: Dictionary = {}
	if input.has("special"):
		var value: Variant = NAN
		match input["special"]:
			"inf": value = INF
			"object": value = RefCounted.new()
			"cycle":
				cyclic["self"] = cyclic
				value = cyclic
		input["initial_statuses"]["allies"]["same"][0]["metadata"] = value
	var started: Dictionary = {}
	if not input.get("no_start", false):
		started = _start(session, input, input.get("legacy", false))
	cyclic.clear()
	var initial_result := started.duplicate(true)
	var initial_preparation := prepared.duplicate(true)
	var healing = Healing.new(session)
	var steps: Array = []
	for step: Dictionary in input.get("steps", []):
		# 製品APIが要求コピーを書き換えていないか、操作の直前/直後で確認します。
		var request_before := JSON.stringify(step)
		var value := _execute(session, healing, step, input)
		var request_preserved := request_before == JSON.stringify(step)
		var original := value.duplicate(true)
		var owned := session.statuses()
		_mutate(value)
		steps.append({"result": original, "independent": owned == session.statuses(),
			"numeric": session.snapshot(), "statuses": session.statuses(), "guards": session.effects(), "request_preserved": request_preserved})
	var owned := session.statuses()
	var single := session.status({"side": "allies", "id": "same"})
	var numeric := session.snapshot()
	var edited := session.statuses()
	_mutate(edited)
	_mutate(single)
	_mutate(started)
	_mutate(input.get("initial_statuses", {}))
	_mutate(input.get("snapshots", {}))
	# 付与要求の効果ネストや指定票を後から編集しても、所有状態/記録へ伝播させません。
	_mutate(input.get("steps", []))
	return {"started": initial_result, "prepared": initial_preparation,
		"steps": steps, "numeric": session.snapshot(), "statuses": session.statuses(),
		"source_independent": owned == session.statuses() and numeric == session.snapshot(),
		"input_preserved": before == JSON.stringify(request)}


# {
#   責務: [_start: コピー要求の数値参加者と初期状態を従来または専用開始入口へ渡します]
#   処理: [1: legacyなら状態を渡さず、専用開始なら明示初期状態を追加します]
#   引数: [
#     session: 観測専用Session（RefCounted）
#     input: snapshotsとinitial_statusesの専用要求（Dictionary）
#     legacy: 従来入口を使うか（bool）
#   ]
#   戻り値: [result: Sessionの実開始結果（Dictionary）]
# }
static func _start(session: RefCounted, input: Dictionary, legacy: bool) -> Dictionary:
	var snapshots: Dictionary = input["snapshots"]
	return session.start(snapshots.get("allies"), snapshots.get("enemies")) if legacy else session.start_with_statuses(
		snapshots.get("allies"), snapshots.get("enemies"), input.get("initial_statuses"))


# {
#   責務: [_execute: 指定した状態読取/更新・再開始・ラウンド/資源操作をSession APIへ委譲します]
#   処理: [1: 専用操作名に対応するAPIを呼び、行動予約は指定がなければ現在の予約を渡します]
#   引数: [
#     session: 実Session（RefCounted）
#     healing: 通常回復行動（RefCounted）
#     step: 操作名と条件（Dictionary）
#     input: 初期条件と任意準備情報（Dictionary）
#   ]
#   戻り値: [result: 指定APIの実結果または未知操作の拒否（Dictionary）]
# }
static func _execute(session: RefCounted, healing: RefCounted, step: Dictionary, input: Dictionary) -> Dictionary:
	var pending: Variant = session.snapshot()["pending"]
	var ticket: Variant = step.get("ticket", pending["ticket"] if pending is Dictionary else null)
	match step["operation"]:
		"apply_status", "apply_cure": return Updates.invoke(session, ticket, step)
		"statuses": return session.statuses()
		"status": return session.status(step.get("actor"))
		"start": return _start(session, step.get("input", input), step.get("legacy", false))
		"begin": return session.begin_round(step.get("order"))
		"next": return session.next_actor()
		"claim": return session.claim(ticket)
		"finish": return session.finish(ticket)
		"damage": return session.take_damage(step.get("actor"), step.get("value"))
		"pay": return session.pay_mp(step.get("actor"), step.get("value"))
		"heal": return session.heal(step.get("actor"), step.get("value"))
		"flee": return session.flee(step.get("actor"))
		"defend": return session.apply_defend(ticket, step.get("value"))
		"heal_start": return healing.start(input["preparation"]["teams"], input["preparation"]["skills"])
		"heal_action": return healing.resolve({"ticket": ticket, "target": step.get("actor"), "skill_id": step.get("skill_id")})
	return {"ok": false, "reason": "invalid_probe_operation"}


# {
#   責務: [_mutate: ネストした読取値や専用入力を編集し、Session所有状態との共有を検出します]
#   処理: [1: 辞書/配列を再帰してmetadataの内側まで編集し、配列へ識別文字列を追加します]
#   引数: [value: 循環を含まない観測用入力または返却値（Variant）]
#   戻り値: [result: なし（void）。観測対象のコピーだけを編集します]
# }
static func _mutate(value: Variant) -> void:
	if value is Dictionary:
		for field in value:
			_mutate(value[field])
		if value.has("id"):
			value["id"] = "changed"
	elif value is Array:
		for item in value:
			_mutate(item)
		value.append("changed")
