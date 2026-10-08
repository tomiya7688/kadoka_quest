# {
#   責務: [run_magic_action_performance: 専用8体Sessionで通常魔法または自傷魔法の行動性能と資源適用を測ります]
#   フィールド: []
# }
extends SceneTree
const Session = preload("res://engine/battle_session.gd")
const Magic = preload("res://engine/magic_skill_action.gd")
const Order = preload("res://engine/turn_order.gd")

# {
#   責務: [_initialize: 引数の専用JSONを読み、魔法行動の性能結果を標準出力へ返して終了します]
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
	print("KADOKA_MAGIC_ACTION_PERFORMANCE=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)

# {
#   責務: [_measure: 8体の開始処理を計測外にし次行動からfinishまでの中央値を測る]
#   処理: [
#     1: 大きな有限資源を持つ専用個体と定義を用意する
#     2: warmup後に複数sampleを測る
#     3: HP減少とMP消費の総量も返す
#   ]
#   引数: [payload: iterations・samples・warmupと自傷区分self_damageの専用計測条件（Dictionary）]
#   戻り値: [result: 1行動あたりの中央値us・累積MP消費・HP変化・術者の累積HP代償（Dictionary）]
# }
func _measure(payload: Dictionary) -> Dictionary:
	# 初期化とI/Oを計測せず、8行動ごとのround準備は実行時間に含める。
	var snapshots := {"allies": [], "enemies": []}
	var prepared := {"allies": [], "enemies": []}
	var self_damage: bool = payload.get("self_damage", false)
	var skill_id := "metal_burst" if self_damage else "weaken"
	var element := "metal" if self_damage else "mental"
	var mp_cost := 18 if self_damage else 5
	var definition := {"id": skill_id, "display_name": "計測用魔法", "kind": "magic",
		"power": 2.0 if self_damage else 1.0, "element": element, "mp_cost": mp_cost}
	# 標準反復でも全員が生存する専用MOD率を使う。正規率0.1とHP1下限は回帰テストで検証する。
	if self_damage:
		definition["self_damage_ratio"] = 0.000000001
	for side in Order.SIDES:
		for index in 4:
			var member := {"identity": {"id": str(index), "species_id": "slime", "name": "test"},
				"stats": {"hp": 1000000000, "mp": 1000000000, "attack": 10, "defense": 10, "magic": 10, "speed": 1},
				"hp": 1000000000, "mp": 1000000000, "fled": false, "alive": true}
			snapshots[side].append(member)
			prepared[side].append({"snapshot": member, "skill_ids": [skill_id], "equipment": {},
				"resistances": {element: ["normal", "immune", "absorb", "strong"][index]}})
	var order: Array = Order.participants(snapshots["allies"], snapshots["enemies"])["members"]
	var session = Session.new()
	session.start(snapshots["allies"], snapshots["enemies"])
	var action = Magic.new(session, self_damage)
	var configured: Dictionary = action.start(prepared, {"schema_version": 1, "skills": [definition]})
	assert(configured["ok"])
	for key: Dictionary in order:
		session.take_damage(key, 100000000)
	var iterations := int(payload["iterations"])
	var samples := int(payload["samples"])
	var warmup := int(payload["warmup"])
	var total_self_dealt := 0
	for index in warmup:
		total_self_dealt += _stage(session, action, order, self_damage)
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			total_self_dealt += _stage(session, action, order, self_damage)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	# 時間だけでなく、実行のスキップや資源未適用を性能成功と誤認しない。
	var total_mp: int = 0
	var minimum_hp: int = 1000000000
	var hp_changed := true
	for team: Array in session.snapshot()["teams"].values():
		for member: Dictionary in team:
			total_mp += member["mp"]
			minimum_hp = mini(minimum_hp, member["hp"])
			var id := int(member["identity"]["id"])
			if id == 1:
				hp_changed = hp_changed and (member["hp"] < 900000000 if self_damage else member["hp"] == 900000000)
			elif id == 2:
				hp_changed = hp_changed and member["hp"] > 900000000
			else:
				hp_changed = hp_changed and member["hp"] < 900000000
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "actors": 8, "minimum_hp": minimum_hp,
		"spent_mp": 8000000000 - total_mp, "expected_spent_mp": (iterations * samples + warmup) * mp_cost,
		"self_dealt": total_self_dealt, "expected_self_dealt": (iterations * samples + warmup) if self_damage else 0,
		"hp_changed": hp_changed}

# {
#   責務: [_stage: 次行動を取得しMP付き単体魔法を実適用する]
#   処理: [
#     1: 終端時だけ次roundを準備する
#     2: offeredの個体から敵へ魔法行動を解決する
#     3: 実行・MP支払い・HP適用を確認する
#   ]
#   引数: [
#     session: 8体の資源とticketを所有するSession（RefCounted）
#     action: コンテキスト準備済みの魔法Action（RefCounted）
#     order: 陣営sideと個体idで表す専用8体の明示参加順（Array）
#     self_damage: trueなら自傷専用入口、falseなら通常魔法の入口を検証する設定（bool）
#   ]
#   戻り値: [result: 今回の術者の実HP代償。通常魔法では0（int）]
# }
func _stage(session: RefCounted, action: RefCounted, order: Array, self_damage: bool) -> int:
	# 一時のfresh Sessionで毎回消費を隠さず、同じ資源を減らし続ける。
	if session.snapshot()["phase"] != "round_active":
		session.begin_round(order)
	var offered: Dictionary = session.next_actor()
	var ticket: Dictionary = offered["pending"]["ticket"]
	var target := {"side": "enemies" if ticket["actor"]["side"] == "allies" else "allies", "id": ticket["actor"]["id"]}
	var resolved: Dictionary = action.resolve({"ticket": ticket, "target": target, "skill_id": "metal_burst" if self_damage else "weaken",
		"variance": 1.0})
	var expected: int = ([20, 0, -10, 12] if self_damage else [10, 0, -5, 6])[int(target["id"])]
	assert(resolved["executed"] and resolved["spent_mp"] == (18 if self_damage else 5) and resolved["numbers"]["dealt"] == expected)
	# 自傷の省略や実減少の誤用を検出し、HP代償1の累積値を返す。
	if self_damage:
		assert(resolved["numbers"]["self_damage"] == 1 and resolved["numbers"]["self_dealt"] == 1)
	return resolved["numbers"].get("self_dealt", 0)
