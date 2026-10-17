# {
#   責務: [run_battle_session_probe: Developer-only isolated session protocol probe and amortized cursor-stage microbenchmark.]
#   フィールド: []
# }
extends SceneTree
## Developer-only isolated session protocol probe and amortized cursor-stage microbenchmark.

const Session = preload("res://engine/battle_session.gd")
const Application = preload("res://application/battle_session_application.gd")
const Repository = preload("res://data/content_repository.gd")
const Eligibility = preload("res://engine/actor_eligibility_projection.gd")
const Order = preload("res://engine/turn_order.gd")


# {
#   責務: [_initialize: 専用JSON要求を読み、Sessionケース・開始調停・性能の観測をBase64で出力します]
#   処理: [1: 引数一件を確認し、要求区分を実プローブへ委譲して終了します]
#   引数: []
#   戻り値: [result: なし（void）。要求引数不正は終了コード2、観測後は0です]
# }
func _initialize() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		quit(2)
		return
	var payload: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	var result := {"cases": [], "joined": []}
	if payload.get("performance", false):
		result = _performance(payload)
	else:
		for case: Dictionary in payload.get("cases", []):
			result["cases"].append(_case(case))
		for case: Dictionary in payload.get("joined", []):
			result["joined"].append(_joined(case))
	print("KADOKA_SESSION_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)


# {
#   責務: [_case: 一つの新規Sessionで開始と連続操作を実行し、数値資源/予約と原本保持を観測します]
#   処理: [1: 入力コピーへ任意非有限値を注入し、指定操作と返却値編集後のSessionを記録します]
#   引数: [case: 数値入力・操作列と任意開始/特殊値/返却編集条件（Dictionary）]
#   戻り値: [result: 開始結果・各操作後Session・最終Sessionと原本保持の観測（Dictionary）]
# }
func _case(case: Dictionary) -> Dictionary:
	var session = Session.new()
	var input: Dictionary = case["input"].duplicate(true)
	for special: Dictionary in case.get("special", []):
		var current: Variant = input
		var path: Array = special["path"]
		for index in path.size() - 1:
			current = current[int(path[index])] if current is Array else current[path[index]]
		current[path.back()] = INF if special["value"] == "inf" else NAN
	var before := input.duplicate(true)
	var initialized: Dictionary = session.start(input.get("allies"), input.get("enemies")) if case.get("start", true) else {}
	var copied_initial := initialized.duplicate(true)
	if case.get("mutate_initial", false):
		_mutate(initialized)
	var observations: Array = []
	for action: Dictionary in case.get("actions", []):
		var value := _execute(session, action, input)
		var copied := value.duplicate(true)
		if action.get("mutate_result", false):
			_mutate(value)
		observations.append({"value": copied, "session": session.snapshot()})
	return {"initialized": copied_initial, "observations": observations, "session": session.snapshot(),
		"input_preserved": input == before if case.get("special", []).is_empty() else true}


# {
#   責務: [_execute: 操作名に応じてSessionの開始・予約・資源APIへ委譲します]
#   処理: [1: 現在予約を既定ticketにし、操作を振り分けます。未知操作は拒否します]
#   引数: [
#     session: 観測専用の実Session（RefCounted）
#     action: kind・宛先・量・任意ticket/非有限値の操作要求（Dictionary）
#     input: 開始参加者と明示shuffle_orderの既定条件（Dictionary）
#   ]
#   戻り値: [result: 指定APIの実結果、または未知プローブ操作の理由付き拒否（Dictionary）]
# }
func _execute(session: RefCounted, action: Dictionary, input: Dictionary) -> Dictionary:
	var value: Variant = action.get("value")
	if action.has("special"):
		value = INF if action["special"] == "inf" else NAN
	var pending: Variant = session.snapshot()["pending"]
	var ticket: Variant = action.get("ticket", pending["ticket"] if pending is Dictionary else null)
	match action["kind"]:
		"start": return session.start(action.get("allies", input.get("allies")), action.get("enemies", input.get("enemies")))
		"begin": return session.begin_round(action.get("order", input.get("shuffle_order")))
		"next": return session.next_actor()
		"claim": return session.claim(ticket)
		"finish": return session.finish(ticket)
		"damage": return session.take_damage(action.get("actor"), value)
		"cost": return session.mp_cost(action.get("actor"), value)
		"pay": return session.pay_mp(action.get("actor"), value)
		"flee": return session.flee(action.get("actor"))
		"snapshot": return session.snapshot()
		"heal": return session.heal(action.get("actor"), value)
		"restore": return session.restore_mp(action.get("actor"), value)
		"inspect": return session.inspect_ticket(ticket)
		"eligibility_parity":
			# 所有者からの経路と公開生入力の厳密経路を、同じ最新資源で照合します。
			var teams: Dictionary = session.snapshot()["teams"]
			return {"inspection": session.inspect_ticket(ticket),
				"reference": Order.check_actor(ticket["actor"], teams["allies"], teams["enemies"])}
		"projection":
			# 検証済み投影の読取結果を編集し、供給したキー/生存者ネストの保持を確認します。
			var before := action.duplicate(true)
			var projected := Eligibility.project(action["actor"], action["actor_alive"], action["friends"], action["foes"])
			var copied := projected.duplicate(true)
			_mutate(projected)
			return {"projection": copied, "input_preserved": before == action}
		"drain": return _drain(session, action.get("effects", []))
		"input_mutation":
			input["allies"][0]["identity"]["name"] = "edited caller"
			input["allies"][0]["stats"]["hp"] = 999
			input["shuffle_order"].reverse()
			return {"ok": true}
	return {"ok": false, "reason": "unknown_probe_operation"}


# {
#   責務: [_drain: 最大八体の予約を取得・完了し、指定行動者の直後に資源操作を適用します]
#   処理: [1: 候補をnext/claimし、実行可能時だけafter指定の効果を適用してfinishします]
#   引数: [
#     session: ラウンド進行を観測する実Session（RefCounted）
#     effects: afterで行動者を指定した資源操作列（Array）
#   ]
#   戻り値: [result: 行動者・最新実行可否・適用結果の列と終了後Session（Dictionary）]
# }
func _drain(session: RefCounted, effects: Array) -> Dictionary:
	var entries: Array = []
	for index in 8:
		var offered: Dictionary = session.next_actor()
		if offered.get("status") != "offered":
			break
		var ticket: Dictionary = offered["pending"]["ticket"]
		var claimed: Dictionary = session.claim(ticket)
		if not claimed.get("can_execute", false):
			continue
		var applied: Array = []
		for effect: Dictionary in effects:
			if effect["after"] == ticket["actor"]:
				applied.append(_execute(session, effect, {}))
		var finished: Dictionary = session.finish(ticket)
		assert(finished["ok"])
		entries.append({"actor": ticket["actor"], "eligibility": claimed["eligibility"], "applied": applied})
	return {"entries": entries, "session": session.snapshot()}


# {
#   責務: [_joined: 読取専用RepositoryからのApplication開始を観測し、返却編集と再開始拒否を確認します]
#   処理: [1: KADOKA_CONTENT_ROOTの専用内容を使い、開始結果を編集して再読取/再開始を照合します]
#   引数: [case: 個体レコードの両陣営と明示shuffle_order（Dictionary）]
#   戻り値: [result: 開始コピー・再読取Session・再開始結果と入力保持条件（Dictionary）]
# }
func _joined(case: Dictionary) -> Dictionary:
	var before := case.duplicate(true)
	var application = Application.new(Repository.new(OS.get_environment("KADOKA_CONTENT_ROOT")))
	var value: Dictionary = application.start(case.get("allies"), case.get("enemies"), case.get("shuffle_order"))
	var copied := value.duplicate(true)
	_mutate(value)
	var status: Dictionary = application.snapshot()
	_mutate(status)
	return {"value": copied, "session": application.snapshot(),
		"again": application.start(case.get("allies"), case.get("enemies"), case.get("shuffle_order")),
		"preserved": case == before}


# {
#   責務: [_mutate: 観測用の返却コピーのネストを編集し、内部所有資源との共有を検出します]
#   処理: [1: 配列/辞書を再帰し、hp/mp/round/slot/cursor/speedと個体idを変更します]
#   引数: [value: Sessionから取得した編集可能な公開コピー（Variant）]
#   戻り値: [result: なし（void）。観測用コピーだけを編集します]
# }
func _mutate(value: Variant) -> void:
	if value is Array:
		for entry: Variant in value:
			_mutate(entry)
	elif value is Dictionary:
		for entry: Variant in value.values():
			_mutate(entry)
		for key in ["hp", "mp", "round", "slot", "cursor", "speed"]:
			if value.has(key):
				value[key] = 999
		if value.has("id"):
			value["id"] = "edited output"


# {
#   責務: [_performance: 初期化済み八体Sessionの予約提示から終了までを反復計測します]
#   処理: [1: 開始構築を計測外に置き、事前実行後の複数サンプルから中央値を返します]
#   引数: [payload: iterations/samples/warmupの反復条件（Dictionary）]
#   戻り値: [result: 一行動段階の中央値・反復条件と参加数八体（Dictionary）]
# }
func _performance(payload: Dictionary) -> Dictionary:
	var input := _benchmark_input()
	var session = Session.new()
	session.start(input["allies"], input["enemies"])
	var iterations := int(payload.get("iterations", 20000))
	var samples := int(payload.get("samples", 7))
	var warmup := int(payload.get("warmup", 2000))
	for index in warmup:
		_stage(session, input["shuffle_order"])
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_stage(session, input["shuffle_order"])
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "actors": 8}


# {
#   責務: [_stage: 次候補の取得・ゼロ資源操作・完了を一行動段階として実行します]
#   処理: [1: 必要時にラウンドを開始し、next→claim→0ダメージ/0MP→finishを実行します]
#   引数: [
#     session: 計測中の開始済み実Session（RefCounted）
#     shuffle_order: 生存する八体の明示順序（Array）
#   ]
#   戻り値: [result: なし（void）。実行可否をassertし、予約を一段階完了します]
# }
func _stage(session: RefCounted, shuffle_order: Array) -> void:
	if session.snapshot()["phase"] != "round_active":
		session.begin_round(shuffle_order)
	var offered: Dictionary = session.next_actor()
	var ticket: Dictionary = offered["pending"]["ticket"]
	var claimed: Dictionary = session.claim(ticket)
	assert(claimed["can_execute"])
	session.take_damage(ticket["actor"], 0)
	session.pay_mp(ticket["actor"], 0)
	session.finish(ticket)


# {
#   責務: [_benchmark_input: 両陣営四体ずつの満資源参加者と明示順序を作ります]
#   処理: [1: 同IDでも陣営を分離し、最大HP100/MP20・速度1〜3の専用参加者を生成します]
#   引数: []
#   戻り値: [result: 八体の六キー数値snapshot列とshuffle_order（Dictionary）]
# }
func _benchmark_input() -> Dictionary:
	var teams := {"allies": [], "enemies": []}
	for side in Order.SIDES:
		for index in 4:
			teams[side].append({"identity": {"id": str(index), "species_id": "slime", "name": "test"},
				"stats": {"hp": 100, "mp": 20, "attack": 10, "defense": 10, "magic": 10, "speed": index % 3 + 1},
				"hp": 100, "mp": 20, "fled": false, "alive": true})
	teams["shuffle_order"] = Order.participants(teams["allies"], teams["enemies"])["members"]
	return teams
