# {
#   責務: [run_basic_defend_performance: 開発者専用で8体中1防御/攻撃と8段階ごとの終端解除を実Godotで計測する]
#   フィールド: []
# }
extends "res://tests/run_normal_attack_probe.gd"


# {
#   責務: [_performance: 定義I/Oと初期構築を除いた8体中1行動段階の中央値を返す]
#   処理: [
#     1: 高HPの8体と独立Actionを構築する
#     2: warmup後に4防御と4攻撃を巡回し8段階ごとの終端解除も償却計測する
#     3: 実HP減少・防御適用・guard解除を検査する
#   ]
#   引数: [payload: iterations/samples/warmup（Dictionary）]
#   戻り値: [result: 時間と効果・資源の観測値（Dictionary）]
# }
func _performance(payload: Dictionary) -> Dictionary:
	var teams := {"allies": [], "enemies": []}
	var prepared := {"allies": [], "enemies": []}
	for side in Order.SIDES:
		for index in 4:
			var member := {"identity": {"id": str(index), "species_id": "slime", "name": "test"},
				"stats": {"hp": 1000000000, "mp": 20, "attack": 10, "defense": 10, "magic": 10, "speed": 10},
				"hp": 1000000000, "mp": 20, "fled": false, "alive": true}
			teams[side].append(member)
			prepared[side].append({"snapshot": member, "equipment": {"fixed_bonus_damage": 3}})
	var order: Array = Order.participants(teams["allies"], teams["enemies"])["members"]
	var session = Session.new()
	var started: Dictionary = session.start(teams["allies"], teams["enemies"])
	var attack = Attack.new(session)
	var defend = Defend.new(session)
	var skills := {"schema_version": 1, "skills": [{"id": "attack", "kind": "physical"},
		{"id": "defend", "kind": "defend", "damage_multiplier": 0.5, "mp_cost": 0}]}
	var configured: Dictionary = attack.start(prepared, skills)
	var guarded: Dictionary = defend.start(skills)
	assert(started["ok"] and configured["ok"] and guarded["ok"])
	var iterations := int(payload.get("iterations", 20000))
	var samples := int(payload.get("samples", 7))
	var warmup := int(payload.get("warmup", 2000))
	for index in warmup:
		_guard_stage(session, attack, defend, order)
	var timings: Array = []
	for sample in samples:
		var started_at := Time.get_ticks_usec()
		for index in iterations:
			_guard_stage(session, attack, defend, order)
		timings.append(float(Time.get_ticks_usec() - started_at) / iterations)
	timings.sort()
	var minimum_hp := 1000000000
	for team: Array in session.snapshot()["teams"].values():
		for member: Dictionary in team:
			minimum_hp = mini(minimum_hp, member["hp"])
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "actors": 8, "minimum_hp": minimum_hp, "effects": session.effects(),
		"phase": session.snapshot()["phase"]}


# {
#   責務: [_guard_stage: 4防御→4攻撃の巡回中1行動を進め末尾で全guardを解除する]
#   処理: [
#     1: 必要時だけ固定shuffleでbegin_roundし1候補を取得する
#     2: 味方は防御し敵は同IDの味方を攻撃する
#     3: 物理guard適用と末尾での解除を確認する
#   ]
#   引数: [
#     session: 8体資源とguardの所有者（RefCounted）
#     attack: 明示通常攻撃Action（RefCounted）
#     defend: 明示基本防御Action（RefCounted）
#     order: 同速の味方4体→敵4体の順列（Array）
#   ]
#   戻り値: [result: なし（void）。HPをリセットせずラウンドを進める]
# }
func _guard_stage(session: RefCounted, attack: RefCounted, defend: RefCounted, order: Array) -> void:
	if session.snapshot()["phase"] != "round_active":
		var planned: Dictionary = session.begin_round(order)
		assert(planned["ok"])
	var offered: Dictionary = session.next_actor()
	var ticket: Dictionary = offered["pending"]["ticket"]
	var value: Dictionary
	if ticket["actor"]["side"] == "allies":
		value = defend.resolve({"ticket": ticket, "skill_id": "defend"})
		assert(value["applied_guard"] == 0.5)
	else:
		value = attack.resolve({"ticket": ticket, "target": {"side": "allies", "id": ticket["actor"]["id"]},
			"skill_id": "attack", "critical_roll": 0.5, "variance": 1.0})
		assert(value["numbers"]["applied_guard"] == 0.5 and value["numbers"]["dealt"] == 4)
	assert(value["executed"])
	if session.snapshot()["phase"] == "round_finished":
		for side in Order.SIDES:
			for multiplier: float in session.effects()["teams"][side].values():
				assert(multiplier == 1.0)
