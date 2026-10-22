# {
#   責務: [run_magic_action_performance: 専用8体Sessionで通常/自傷/吸MP魔法または単体HP回復の行動性能と累積資源適用を測ります]
#   フィールド: []
# }
extends SceneTree
const Session = preload("res://engine/battle_session.gd")
const Magic = preload("res://engine/magic_skill_action.gd")
const Heal = preload("res://engine/heal_skill_action.gd")
const Order = preload("res://engine/turn_order.gd")

# {
#   責務: [_initialize: 専用JSONを読み、魔法または単体HP回復の性能結果を標準出力へ返して終了します]
#   処理: [
#     1: 専用JSONのパスが一つ渡されたか確認します
#     2: 専用8体での実行結果をBase64付き標準出力へ出し、終了します
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
#   責務: [_measure: 専用8体の初期構築を計測外にし、次行動取得から予約完了までの1行動の中央値を測ります]
#   処理: [
#     1: 指定区分の定義と大きな有限資源を持つ専用8体を用意します
#     2: 事前実行後に複数サンプルの実行時間を測ります
#     3: HP変化・累積MPと区分専用の代償/回復上限の一致を確認します
#   ]
#   引数: [payload: iterations・samples・warmupと排他的なself_damage/drain_mp/healの計測条件。吸MPは全反復数を8の倍数にします（Dictionary）]
#   戻り値: [result: 1行動の中央値us・累積MP純減・HP変化・術者HP代償・MP適用一致、または不正区分/反復数の拒否（Dictionary）]
# }
func _measure(payload: Dictionary) -> Dictionary:
	# 初期化とI/Oを計測せず、8行動ごとのround準備は実行時間に含める。
	var snapshots := {"allies": [], "enemies": []}
	var prepared := {"allies": [], "enemies": []}
	var self_damage: bool = payload.get("self_damage", false)
	var drain_mp: bool = payload.get("drain_mp", false)
	var heal: bool = payload.get("heal", false)
	if int(self_damage) + int(drain_mp) + int(heal) > 1:
		return {"ok": false, "reason": "invalid_magic_mode"}
	# 吸MPの累積上限を8体の完全なラウンドで比較し、未完了の標本を成功扱いしません。
	var total_steps: int = int(payload["iterations"]) * int(payload["samples"]) + int(payload["warmup"])
	if drain_mp and (total_steps < 8 or total_steps % 8 != 0):
		return {"ok": false, "reason": "complete_rounds_required"}
	var skill_id := "metal_burst" if self_damage else "weaken"
	var element := "metal" if self_damage else "mental"
	var mp_cost := 18 if self_damage else 5
	var definition := {"id": skill_id, "display_name": "計測用魔法", "kind": "magic",
		"power": 2.0 if self_damage else 1.0, "element": element, "mp_cost": mp_cost}
	# 標準反復でも全員が生存する専用MOD率を使う。正規率0.1とHP1下限は回帰テストで検証する。
	if self_damage:
		definition["self_damage_ratio"] = 0.000000001
	elif drain_mp:
		skill_id = "possess"
		definition.merge({"id": skill_id, "kind": "drain_mp", "mp_power": 0.7}, true)
	elif heal:
		# 全反復で実HPを回復し続ける有限MOD率を使います。正規率と満HPでのMP消費は回帰テストで検証します。
		skill_id = "small_heal"
		mp_cost = 6
		definition = {"id": skill_id, "display_name": "計測用回復", "kind": "heal", "heal_ratio": 0.000000001, "mp_cost": mp_cost}
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
	var action: RefCounted = Heal.new(session) if heal else Magic.new(session, self_damage, drain_mp)
	var configured: Dictionary = action.start(prepared, {"schema_version": 1, "skills": [definition]})
	assert(configured["ok"])
	for key: Dictionary in order:
		session.take_damage(key, 100000000)
	var iterations := int(payload["iterations"])
	var samples := int(payload["samples"])
	var warmup := int(payload["warmup"])
	var total_self_dealt := 0
	for index in warmup:
		total_self_dealt += _stage(session, action, order, self_damage, drain_mp, heal)
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			total_self_dealt += _stage(session, action, order, self_damage, drain_mp, heal)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	# 時間だけでなく、実行のスキップや資源未適用を性能成功と誤認しない。
	var total_mp: int = 0
	var minimum_hp: int = 1000000000
	var hp_changed := true
	var mp_applied := true
	var current: Dictionary = session.snapshot()["teams"]
	for side in Order.SIDES:
		var team: Array = current[side]
		for member: Dictionary in team:
			total_mp += member["mp"]
			minimum_hp = mini(minimum_hp, member["hp"])
			var id := int(member["identity"]["id"])
			if heal:
				# 端数ラウンドでも各個体の実行回数を求め、累積HP/MPを独立に確認します。
				var ordinal: int = id + (4 if side == "enemies" else 0)
				var count: int = total_steps / 8 + (1 if ordinal < total_steps % 8 else 0)
				hp_changed = hp_changed and member["hp"] == 900000000 + count
				mp_applied = mp_applied and member["mp"] == 1000000000 - count * mp_cost
				continue
			if drain_mp:
				# 通常/強耐性の味方2体だけ、初回の満タン回復で各2MPを失います。その後は全員が1ラウンド5MPずつ純減します。
				var cap_loss := 2 if side == "allies" and id in [0, 3] else 0
				mp_applied = mp_applied and member["mp"] == 1000000000 - (total_steps / 8) * mp_cost - cap_loss
			if id == 1:
				hp_changed = hp_changed and (member["hp"] < 900000000 if self_damage else member["hp"] == 900000000)
			elif id == 2:
				hp_changed = hp_changed and member["hp"] > 900000000
			else:
				hp_changed = hp_changed and member["hp"] < 900000000
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "actors": 8, "minimum_hp": minimum_hp,
		"spent_mp": 8000000000 - total_mp, "expected_spent_mp": total_steps * mp_cost + (4 if drain_mp else 0),
		"self_dealt": total_self_dealt, "expected_self_dealt": (iterations * samples + warmup) if self_damage else 0,
		"hp_changed": hp_changed, "mp_applied": mp_applied}

# {
#   責務: [_stage: 専用Sessionの次行動を取得し、選択区分の魔法または本人回復と実HP/MP変化を確認します]
#   処理: [
#     1: ラウンド終端の場合だけ次の確定順を準備します
#     2: 提示された個体から同IDの敵へ専用魔法、または本人へ単体HP回復を実行します
#     3: 消費MP・実HP効果と、吸MPなら敵喪失/術者回復/実資源の一致を確認します
#   ]
#   引数: [
#     session: 8体の資源とticketを所有するSession（RefCounted）
#     action: 指定区分の開始情報を設定済みの魔法行動または単体HP回復行動（RefCounted）
#     order: 陣営sideと個体idで表す専用8体の明示参加順（Array）
#     self_damage: trueなら術者HP代償を検証し、falseなら自傷効果を検証しない設定（bool）
#     drain_mp: trueなら吸MP専用入口の敵MP喪失・術者MP回復も検証する設定（bool）
#     heal: trueなら単体HP回復の本人対象・MP支払いと実HP回復を検証する設定（bool）
#   ]
#   戻り値: [result: 今回の術者の実HP代償。通常魔法では0（int）]
# }
func _stage(session: RefCounted, action: RefCounted, order: Array, self_damage: bool, drain_mp: bool, heal: bool) -> int:
	# 一時のfresh Sessionで毎回消費を隠さず、同じ資源を減らし続ける。
	if session.snapshot()["phase"] != "round_active":
		session.begin_round(order)
	var offered: Dictionary = session.next_actor()
	var ticket: Dictionary = offered["pending"]["ticket"]
	if heal:
		var recovered: Dictionary = action.resolve({"ticket": ticket, "target": ticket["actor"], "skill_id": "small_heal"})
		# 予測だけの成功・満HPによる早期終了・MP非消費を性能成功と扱いません。
		assert(recovered["executed"] and recovered["spent_mp"] == 6 and recovered["healed"] == 1)
		return 0
	var target := {"side": "enemies" if ticket["actor"]["side"] == "allies" else "allies", "id": ticket["actor"]["id"]}
	var skill_id := "metal_burst" if self_damage else "weaken"
	if drain_mp:
		skill_id = "possess"
	var resolved: Dictionary = action.resolve({"ticket": ticket, "target": target, "skill_id": skill_id,
		"variance": 1.0})
	var expected: int = ([20, 0, -10, 12] if self_damage else [10, 0, -5, 6])[int(target["id"])]
	assert(resolved["executed"] and resolved["spent_mp"] == (18 if self_damage else 5) and resolved["numbers"]["dealt"] == expected)
	# 自傷の省略や実減少の誤用を検出し、HP代償1の累積値を返す。
	if self_damage:
		assert(resolved["numbers"]["self_damage"] == 1 and resolved["numbers"]["self_dealt"] == 1)
	if drain_mp:
		# 予測値を足し上げるだけではなく、予約取得直前の資源から独立にMP差分を求めます。
		var index := int(target["id"])
		var previous_actor: Dictionary = offered["eligibility"]["friends"][index]
		var previous_target: Dictionary = offered["eligibility"]["foes"][index]
		var drained := 7 if index in [0, 3] else 0
		var recovered: int = mini(drained, 1000000000 - (int(previous_actor["mp"]) - 5))
		assert(resolved["drained_mp"] == drained and resolved["recovered_mp"] == recovered)
		var actual_actor: Dictionary = resolved["session"]["teams"][ticket["actor"]["side"]][index]
		var actual_target: Dictionary = resolved["session"]["teams"][target["side"]][index]
		assert(actual_actor["mp"] == previous_actor["mp"] - 5 + recovered)
		assert(actual_target["mp"] == previous_target["mp"] - drained)
	return resolved["numbers"].get("self_dealt", 0)
