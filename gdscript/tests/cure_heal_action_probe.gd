# {
#   責務: [cure_heal_action_probe: 専用Session/Applicationの治療付き回復・拒否/再試行・数値/状態独立性を観測します]
#   フィールド: []
# }
extends RefCounted
const Session = preload("res://engine/battle_session.gd")
const Healing = preload("res://engine/heal_skill_action.gd")
const Application = preload("res://application/battle_session_application.gd")
const Repository = preload("res://data/content_repository.gd")
const Copies = preload("res://tests/session_status_probe.gd")
const Benchmark = preload("res://tests/cure_heal_action_benchmark.gd")


# {
#   責務: [run: ケースごとの新規戦闘観測、または専用八体の実治療計測を振り分けます]
#   処理: [1: performance指定を計測へ委譲し、その他は各ケースを独立に実行します]
#   引数: [payload: 専用ケース一覧または反復条件（Dictionary）]
#   戻り値: [result: ケース観測列または性能/実資源/実治療の結果（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	if payload.get("performance", false):
		return Benchmark.new().measure(payload)
	var results: Array = []
	for request: Dictionary in payload.get("cases", []):
		results.append(_case(request))
	return {"results": results}


# {
#   責務: [_case: コピー入力から独立戦闘を開始し、明示操作と返却値編集後の数値/状態を観測します]
#   処理: [1: 開始・行動処理設定を行い、各操作の独立結果と入力保持を記録します]
#   引数: [request: teams/skills/initial_statuses/order、任意joined/records/project_rootとstepsの専用条件（Dictionary）]
#   戻り値: [result: 開始・行動設定・各操作・最終数値/状態と原本/返却独立性（Dictionary）]
# }
static func _case(request: Dictionary) -> Dictionary:
	var before := JSON.stringify(request)
	var input := request.duplicate(true)
	var joined: bool = input.get("joined", false)
	var session: RefCounted = Application.new(Repository.new(input["project_root"])) if joined else Session.new()
	var started := _start(session, input, joined)
	var configured: Dictionary = {}
	var healing: RefCounted
	var ordinary: RefCounted
	if not joined:
		healing = Healing.new(session, true)
		ordinary = Healing.new(session)
		if started["ok"]:
			configured = healing.start_cure_heal(input.get("context", input["teams"]), input["skills"], input.get("action_statuses", input["initial_statuses"]))
			ordinary.start(input["teams"], input["skills"])
			if configured["ok"]:
				session.begin_round(input["order"])
	var original_started := started.duplicate(true)
	var steps: Array = []
	var ticket: Variant = null
	for step: Dictionary in input.get("steps", []):
		var pending: Variant = session.snapshot()["pending"]
		if pending is Dictionary:
			ticket = pending["ticket"].duplicate(true)
		var value := _step(session, healing, ordinary, step, input, ticket, joined)
		var original := value.duplicate(true)
		var numeric: Dictionary = session.snapshot()
		var statuses: Dictionary = session.statuses()
		# 共用コピー編集ヘルパーで、治療結果・数値/状態のネストと所有正本の共有を検出します。
		Copies._mutate(value)
		steps.append({"result": original, "numeric": numeric, "statuses": statuses,
			"independent": numeric == session.snapshot() and statuses == session.statuses()})
	Copies._mutate(started)
	Copies._mutate(input)
	return {"started": original_started, "configured": configured, "steps": steps,
		"numeric": session.snapshot(), "statuses": session.statuses(), "input_preserved": before == JSON.stringify(request)}


# {
#   責務: [_start: 保存個体または数値参加者を、従来/明示状態付きの開始入口へ渡します]
#   処理: [1: Applicationは保存レコード、純粋Sessionは六キーsnapshotを対応開始へ渡します]
#   引数: [
#     session: ケース専用SessionまたはApplication（RefCounted）
#     input: 開始参加者・明示順/状態と任意legacy区分（Dictionary）
#     joined: 保存個体からApplication開始するか（bool）
#   ]
#   戻り値: [result: 実開始結果または拒否（Dictionary）]
# }
static func _start(session: RefCounted, input: Dictionary, joined: bool) -> Dictionary:
	if joined:
		var records: Dictionary = input["records"]
		return session.start(records["allies"], records["enemies"], input["order"]) if input.get("legacy", false) else session.start_with_statuses(
			records["allies"], records["enemies"], input["order"], input.get("initial_statuses"))
	var teams := {"allies": [], "enemies": []}
	for side in ["allies", "enemies"]:
		for member: Dictionary in input["teams"][side]:
			teams[side].append(member["snapshot"])
	return session.start(teams["allies"], teams["enemies"]) if input.get("legacy", false) else session.start_with_statuses(
		teams["allies"], teams["enemies"], input.get("initial_statuses"))


# {
#   責務: [_step: 明示された回復・予約・資源操作を製品APIへ渡し、専用コピーにだけ非JSON値を注入します]
#   処理: [1: 現在または指定行動票を使って操作を振り分け、回復要求の不正値を専用ケースで生成します]
#   引数: [
#     session: 観測先のSessionまたはApplication（RefCounted）
#     healing: 純粋Sessionの治療付き行動。Applicationではnull（RefCounted）
#     ordinary: 純粋Sessionの従来回復行動。Applicationではnull（RefCounted）
#     step: 操作名と個別条件（Dictionary）
#     input: 開始条件と再開始時の既定入力（Dictionary）
#     ticket: 直近に提示された独立行動票（Variant）
#     joined: Application経由で実行するか（bool）
#   ]
#   戻り値: [result: 対象製品APIの実結果または未知操作の拒否（Dictionary）]
# }
static func _step(session: RefCounted, healing: RefCounted, ordinary: RefCounted, step: Dictionary,
	input: Dictionary, ticket: Variant, joined: bool) -> Dictionary:
	var active: Variant = step.get("ticket", ticket)
	match step["operation"]:
		"next": return session.next_actor()
		"begin": return session.begin_round(step.get("order", input["order"]))
		"start": return _start(session, step.get("input", input), joined)
		"status": return session.status(step.get("target"))
		"statuses": return session.statuses()
		"input_edit":
			# 開始情報を途中で編集しても、Session/行動の正本に伝播しないことを観測します。
			for field in ["teams", "skills", "initial_statuses"]:
				Copies._mutate(input[field])
			return {"ok": true}
		"claim": return session.claim(active)
		"finish": return session.finish(active)
		"damage": return session.take_damage(step.get("target"), step.get("value"))
		"pay": return session.pay_mp(step.get("target"), step.get("value"))
		"flee": return session.flee(step.get("target"))
		"apply_cure": return session.apply_status_cure(active, step.get("target"), step.get("request"))
		"configure": return healing.start_cure_heal(input["teams"], input["skills"], input["initial_statuses"])
		"ordinary_start_cure": return ordinary.start_cure_heal(input["teams"], input["skills"], input["initial_statuses"])
		"cure_start_ordinary": return healing.start(input["teams"], input["skills"])
		"action", "ordinary_action":
			var request: Variant = step.get("request", {"ticket": active, "target": step.get("target"), "skill_id": step.get("skill_id", "spirit_recover")})
			if step.has("roll"):
				request["roll"] = step["roll"]
			for field in step.get("extra", {}):
				request[field] = step["extra"][field]
			if step.has("special"):
				request["roll"] = RefCounted.new() if step["special"] == "object" else (NAN if step["special"] == "nan" else INF)
			if step["operation"] == "ordinary_action":
				return session.resolve_heal_skill(request) if joined else ordinary.resolve(request)
			return session.resolve_cure_heal_skill(request) if joined else healing.resolve(request)
	return {"ok": false, "reason": "invalid_probe_operation"}
