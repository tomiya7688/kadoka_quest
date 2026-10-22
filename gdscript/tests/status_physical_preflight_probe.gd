# {
#   責務: [status_physical_preflight_probe: 専用開始と付与付き物理の検査/実行・拒否/再試行/独立性を観測します]
#   フィールド: []
# }
extends RefCounted
const Preflight = preload("res://engine/status_physical_skill_preflight.gd")
const Action = preload("res://engine/status_physical_skill_action.gd")
const Failure = preload("res://tests/status_physical_failure_session.gd")
const Session = preload("res://engine/battle_session.gd")
const Application = preload("res://application/battle_session_application.gd")
const Repository = preload("res://data/content_repository.gd")
const Physical = preload("res://engine/physical_skill_action.gd")
const Shared = preload("res://tests/session_status_probe.gd")
const StartProbe = preload("res://tests/cure_heal_action_probe.gd")
const Inputs = preload("res://tests/status_physical_context_probe.gd")
const ActionBenchmark = preload("res://tests/status_physical_action_benchmark.gd")


# {
#   責務: [run: 付与付き物理のケース観測、または八体/千定義の非消費検査/実行性能を専用担当へ渡します]
#   処理: [1: performance指定は計測へ、ケース配列は一件ずつ独立観測へ委譲します]
#   引数: [payload: ケース配列または反復回数を持つ専用要求（Dictionary）]
#   戻り値: [result: ケース結果列、または指定区分の性能/固定入力/保持確認の観測（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	# 固定性能入力と個別の不正/再試行ケースを混ぜず、それぞれ独立に観測します。
	if payload.get("performance", false):
		if payload.get("status_physical_action", false):
			return ActionBenchmark.new().measure(payload)
		return _measure(payload)
	var results: Array = []
	for request: Dictionary in payload.get("cases", []):
		results.append(_case(request, payload.get("status_physical_action", false)))
	return {"results": results}


# {
#   責務: [_case: 専用コピーで戦闘と検査を設定し、各操作前後の資源/状態/guardと返却独立性を記録します]
#   処理: [1: 専用/従来の開始を共用プローブへ委譲し、検査/明示操作後に返却ネストを編集して正本を再照合します]
#   引数: [
#     request: teams/skills/initial_statuses/order、任意joined/records/project_rootとstepsの専用条件（Dictionary）
#     with_action: trueなら非消費検査と共用の開始情報を持つ付与付き行動を観測します（bool）
#   ]
#   戻り値: [result: 開始/設定/操作観測・最終状態・原本保持（Dictionary）]
# }
static func _case(request: Dictionary, with_action: bool = false) -> Dictionary:
	# 元要求とコピーを分離し、ケース間や実セーブへ状態変更を伝播させません。
	var before := JSON.stringify(request)
	var input := request.duplicate(true)
	var joined: bool = input.get("joined", false)
	var session: RefCounted = Application.new(Repository.new(input["project_root"])) if joined else Session.new()
	if input.has("fail_at") and not joined:
		session = Failure.new(input["fail_at"])
	var started := StartProbe._start(session, input, joined)
	var preflight: RefCounted
	var ordinary: RefCounted
	var configured: Dictionary = {}
	# Applicationは専用開始が設定を所有し、純粋Sessionだけがプローブで検査を構築します。
	if not joined:
		preflight = Action.new(session) if with_action else Preflight.new(session)
		ordinary = Physical.new(session)
		if started["ok"]:
			ordinary.start(input["teams"], input["skills"])
			if input.get("configure", true):
				configured = preflight.start(input.get("context", input["teams"]), input["skills"], input.get("action_statuses", input["initial_statuses"]))
			if input.get("begin", true) and configured.get("ok", false):
				session.begin_round(input["order"])
	var steps: Array = []
	for step: Dictionary in input.get("steps", []):
		var numeric: Dictionary = session.snapshot()
		var statuses: Dictionary = session.statuses()
		var guards: Dictionary = session.effects()
		var request_before := JSON.stringify(step)
		var value := _step(session, preflight, ordinary, step, input, joined)
		var request_preserved := request_before == JSON.stringify(step)
		var original := value.duplicate(true)
		var after: Dictionary = session.snapshot()
		var states_after: Dictionary = session.statuses()
		var guards_after: Dictionary = session.effects()
		# 返却値を再帰編集し、内部context/Sessionと共有したネストがないか次の読取でも確認します。
		Shared._mutate(value)
		if value.has("target_status_resistances"):
			value["target_status_resistances"].clear()
			value["equipment"].clear()
			value["actor_resources"]["stats"]["attack"] = -999
			value["eligibility"]["can_act"] = false
		steps.append({"result": original, "numeric": after, "statuses": states_after, "guards": guards_after,
			"request_preserved": request_preserved,
			"unchanged": numeric == after and statuses == states_after and guards == guards_after,
			"independent": after == session.snapshot() and states_after == session.statuses() and guards_after == session.effects()})
	var initial_result := started.duplicate(true)
	Shared._mutate(started)
	var result := {"started": initial_result, "configured": configured, "steps": steps, "numeric": session.snapshot(),
		"statuses": session.statuses(), "input_preserved": before == JSON.stringify(request)}
	if input.has("fail_at"):
		result["calls"] = session.calls.duplicate()
	return result


# {
#   責務: [_step: 検査/行動/設定と専用資源・状態操作を実APIへ渡し、非JSON値は観測コピーだけへ注入します]
#   処理: [1: 現在予約を既定値にして専用検査へ委譲し、その他の操作を共用Session観測へ渡します]
#   引数: [
#     session: 観測先のSessionまたはApplication（RefCounted）
#     preflight: 純粋Sessionの非消費検査または専用行動、Applicationではnull（RefCounted）
#     ordinary: 従来物理行動、Applicationではnull（RefCounted）
#     step: 操作名と個別要求/不正値条件（Dictionary）
#     input: ケースの独立開始入力（Dictionary）
#     joined: Application経由ならtrue（bool）
#   ]
#   戻り値: [result: 製品APIの実結果または共用プローブの未知操作拒否（Dictionary）]
# }
static func _step(session: RefCounted, preflight: RefCounted, ordinary: RefCounted, step: Dictionary, input: Dictionary, joined: bool) -> Dictionary:
	var pending: Variant = session.snapshot()["pending"]
	var ticket: Variant = step.get("ticket", pending["ticket"] if pending is Dictionary else null)
	match step["operation"]:
		"defend_action":
			# Applicationの公開行動を使って実ラウンドを完了し、非公開Sessionの予約APIを迂回しません。
			return session.resolve_basic_defend({"ticket": ticket, "skill_id": "defend"})
		"start": return StartProbe._start(session, step.get("input", input), joined)
		"configure": return preflight.start(step.get("teams", input["teams"]), step.get("skills", input["skills"]), step.get("initial_statuses", input["initial_statuses"]))
		"input_edit":
			Shared._mutate(input.get("teams", {}))
			Shared._mutate(input.get("skills", {}))
			Shared._mutate(input.get("initial_statuses", {}))
			for side in ["allies", "enemies"]:
				for member: Variant in input.get("teams", {}).get(side, []):
					if member is Dictionary:
						member["status_resistances"].clear()
						member["equipment"].clear()
			return {"ok": true}
		"inspect", "ordinary_action", "action":
			var request: Variant = step.get("request", {"ticket": ticket, "target": step.get("target"), "skill_id": step.get("skill_id", "mod_status_hit")})
			if step["operation"] == "action" and not step.has("request"):
				request["critical_roll"] = step.get("critical_roll", 0.5)
				request["variance"] = step.get("variance", 1.0)
				if step.has("status_roll"):
					request["status_roll"] = step["status_roll"]
			for field in step.get("extra", {}):
				request[field] = step["extra"][field]
			if step.has("special"):
				request[step["special"]["field"]] = RefCounted.new() if step["special"]["value"] == "object" else NAN
			if step["operation"] == "ordinary_action":
				return session.resolve_physical_skill(request) if joined else ordinary.resolve(request)
			if step["operation"] == "action":
				return session.resolve_status_physical_skill(request) if joined else preflight.resolve(request)
			return session.inspect_status_physical_skill(request) if joined else preflight.inspect(request)
	# 純粋Sessionの資源/状態の変更は共用プローブへ渡し、製品の内部フィールドを直接編集しません。
	return Shared._execute(session, null, step, input)


# {
#   責務: [_measure: 八体/千定義を開始時だけ準備し、同じ提示予約への成功検査を非消費のまま反復測定します]
#   処理: [1: 共用固定入力からSession/検査を構築し、検査中央値・固定結果・正本/入力の保持を返します]
#   引数: [payload: iterations/samples/warmupの反復条件（Dictionary）]
#   戻り値: [result: 一検査中央値と固定期待値照合用の検査/Session/状態・保持確認（Dictionary）]
# }
static func _measure(payload: Dictionary) -> Dictionary:
	# 計測前の一度だけ八体/千定義を準備し、索引作成を毎検査の時間へ混ぜません。
	var source := Inputs._inputs()
	var before := JSON.stringify(source)
	var teams: Dictionary = source["teams"]
	var session = Session.new()
	var snapshots := {"allies": [], "enemies": []}
	var order: Array = []
	for side in ["allies", "enemies"]:
		for member: Dictionary in teams[side]:
			snapshots[side].append(member["snapshot"])
			order.append({"side": side, "id": member["snapshot"]["identity"]["id"]})
	assert(session.start_with_statuses(snapshots["allies"], snapshots["enemies"], source["statuses"])["ok"])
	var preflight = Preflight.new(session)
	assert(preflight.start(teams, source["skills"], source["statuses"])["ok"])
	assert(session.begin_round(order)["ok"])
	var ticket: Dictionary = session.next_actor()["pending"]["ticket"]
	var request := {"ticket": ticket, "target": {"side": "enemies", "id": "member_0"}, "skill_id": "mod_status_hit"}
	var numeric := session.snapshot()
	var statuses := session.statuses()
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	# 開始時の索引生成/ファイルI/Oを含めず、最新状態読取と成功する専用検査を反復します。
	for index in warmup:
		preflight.inspect(request)
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			preflight.inspect(request)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples, "warmup": warmup,
		"actors": order.size(), "definitions": source["skills"]["skills"].size(), "checked": preflight.inspect(request),
		"numeric": numeric, "statuses": statuses, "input_preserved": before == JSON.stringify(source),
		"session_preserved": numeric == session.snapshot() and statuses == session.statuses()}
