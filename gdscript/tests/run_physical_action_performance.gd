# {
#   責務: [run_physical_action_performance: 開発専用の8体Sessionで単体物理行動の性能と資源適用を測る]
#   フィールド: []
# }
extends SceneTree
const Session = preload("res://engine/battle_session.gd")
const Physical = preload("res://engine/physical_skill_action.gd")
const Order = preload("res://engine/turn_order.gd")

# {
#   責務: [_initialize: 専用要求を読み性能結果を出力する]
#   処理: [
#     1: 開発用JSONの引数を確認する
#     2: 測定結果を出力して終了する
#   ]
#   引数: []
#   戻り値: [result: なし（void）]
# }
func _initialize() -> void:
	# Playerから呼ばない専用入口。利用者data・保存先は参照しない。
	var args := OS.get_cmdline_user_args()
	if args.size() != 1:
		quit(2)
		return
	var payload: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var result := _measure(payload)
	print("KADOKA_PHYSICAL_ACTION_PERFORMANCE=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)

# {
#   責務: [_measure: 8体の開始処理を計測外にし次行動からfinishまでの中央値を測る]
#   処理: [
#     1: 大きな有限資源を持つ専用個体と定義を用意する
#     2: warmup後に複数sampleを測る
#     3: HP減少とMP消費の総量も返す
#   ]
#   引数: [payload: iterations・samples・warmupの要求（Dictionary）]
#   戻り値: [result: 時間と資源検証値（Dictionary）]
# }
func _measure(payload: Dictionary) -> Dictionary:
	# 初期化とI/Oを計測せず、8行動ごとのround準備は実行時間に含める。
	var snapshots := {"allies": [], "enemies": []}
	var prepared := {"allies": [], "enemies": []}
	for side in Order.SIDES:
		for index in 4:
			var member := {"identity": {"id": str(index), "species_id": "slime", "name": "test"},
				"stats": {"hp": 1000000000, "mp": 1000000000, "attack": 10, "defense": 10, "magic": 10, "speed": 1},
				"hp": 1000000000, "mp": 1000000000, "fled": false, "alive": true}
			snapshots[side].append(member)
			prepared[side].append({"snapshot": member, "skill_ids": ["body_bash"], "equipment": {}})
	var order: Array = Order.participants(snapshots["allies"], snapshots["enemies"])["members"]
	var session = Session.new()
	session.start(snapshots["allies"], snapshots["enemies"])
	var action = Physical.new(session)
	var configured: Dictionary = action.start(prepared, {"schema_version": 1, "skills": [
		{"id": "body_bash", "display_name": "たいあたり", "kind": "physical", "power": 1.2, "mp_cost": 3}]})
	assert(configured["ok"])
	var iterations := int(payload["iterations"])
	var samples := int(payload["samples"])
	var warmup := int(payload["warmup"])
	for index in warmup:
		_stage(session, action, order)
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_stage(session, action, order)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	# 時間だけでなく、実行のスキップや資源未適用を性能成功と誤認しない。
	var total_mp: int = 0
	var minimum_hp: int = 1000000000
	for team: Array in session.snapshot()["teams"].values():
		for member: Dictionary in team:
			total_mp += member["mp"]
			minimum_hp = mini(minimum_hp, member["hp"])
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "actors": 8, "minimum_hp": minimum_hp,
		"spent_mp": 8000000000 - total_mp, "expected_spent_mp": (iterations * samples + warmup) * 3}

# {
#   責務: [_stage: 次行動を取得しMP付き単体物理を実適用する]
#   処理: [
#     1: 終端時だけ次roundを準備する
#     2: offeredの個体から敵へ物理行動を解決する
#     3: 実行・MP支払い・HP適用を確認する
#   ]
#   引数: [
#     session: 8体の資源とticketを所有するSession（RefCounted）
#     action: コンテキスト準備済みの物理Action（RefCounted）
#     order: 明示参加順（Array）
#   ]
#   戻り値: [result: なし（void）]
# }
func _stage(session: RefCounted, action: RefCounted, order: Array) -> void:
	# 一時のfresh Sessionで毎回消費を隠さず、同じ資源を減らし続ける。
	if session.snapshot()["phase"] != "round_active":
		session.begin_round(order)
	var offered: Dictionary = session.next_actor()
	var ticket: Dictionary = offered["pending"]["ticket"]
	var target := {"side": "enemies" if ticket["actor"]["side"] == "allies" else "allies", "id": "0"}
	var resolved: Dictionary = action.resolve({"ticket": ticket, "target": target, "skill_id": "body_bash",
		"critical_roll": 0.5, "variance": 1.0})
	assert(resolved["executed"] and resolved["spent_mp"] == 3 and resolved["numbers"]["dealt"] == 7)
