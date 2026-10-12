# {
#   責務: [cure_heal_action_benchmark: 八体の実回復/MP消費/毒一件解除を反復し、八行動ごとの新規構築も含めて計測します]
#   フィールド: [
#     _source: 固定八体の開始数値・習得・定義・初期状態（Dictionary）
#     _order: 同速度八体の明示行動順（Array）
#     _session: 現在の八行動バッチで資源/予約/状態を所有するSession（RefCounted）
#     _action: 現在バッチの治療付き専用回復行動（RefCounted）
#     _last: 直近の実行結果の独立辞書（Dictionary）
#     _completed: 実適用と所有資源/状態の一致を確認した行動数（int）
#   ]
# }
extends RefCounted
const Session = preload("res://engine/battle_session.gd")
const Healing = preload("res://engine/heal_skill_action.gd")
var _source := {"snapshots": {"allies": [], "enemies": []}, "teams": {"allies": [], "enemies": []},
	"initial_statuses": {"allies": {}, "enemies": {}}, "skills": {"schema_version": 1, "skills": [
		{"id": "spirit_recover", "display_name": "計測用治療回復", "kind": "heal", "mp_cost": 6,
			"heal_ratio": 0.000000001, "status_cure_chance": 1}]}}
var _order: Array = []
var _session: RefCounted
var _action: RefCounted
var _last: Dictionary = {}
var _completed := 0


# {
#   責務: [_init: 全八体の満資源と解除不可/ネスト付き毒/眠りを持つ固定入力を作ります]
#   処理: [1: 同IDでも陣営を分離し、全員の習得定義と明示初期状態・順序を用意します]
#   引数: []
#   戻り値: [result: なし（void）。利用者コンテンツや保存先は参照しません]
# }
func _init() -> void:
	for side in ["allies", "enemies"]:
		for index in 4:
			var id := str(index)
			var member := {"identity": {"id": id, "species_id": "slime", "name": "test"},
				"stats": {"hp": 1000000000, "mp": 1000000000, "attack": 10, "defense": 10, "magic": 10, "speed": 1},
				"hp": 1000000000, "mp": 1000000000, "fled": false, "alive": true}
			_source["snapshots"][side].append(member)
			_source["teams"][side].append({"snapshot": member, "skill_ids": ["spirit_recover"], "equipment": {}})
			_source["initial_statuses"][side][id] = [{"id": "lock", "removable": false},
				{"id": "poison", "metadata": {"deck": [1, {"kept": true}]}}, "sleep"]
			_order.append({"side": side, "id": id})


# {
#   責務: [measure: 全反復で実HP/MP/治療を確認し、初期化込みの一行動中央値と累積確認数を返します]
#   処理: [1: 完全な八行動バッチ条件を確認し、事前実行と複数サンプルを測定して原本保持を照合します]
#   引数: [payload: iterations/samples/warmupの反復条件。総行動数は八の倍数です（Dictionary）]
#   戻り値: [result: 中央値・回数・実成功数・最終資源/状態と原本保持、または不正反復数の拒否（Dictionary）]
# }
func measure(payload: Dictionary) -> Dictionary:
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	if (iterations * samples + warmup) % 8 != 0:
		return {"ok": false, "reason": "complete_rounds_required"}
	var before := JSON.stringify(_source)
	for index in warmup:
		_stage()
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_stage()
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples, "warmup": warmup,
		"actors": 8, "completed": _completed, "last": _last, "numeric": _session.snapshot(),
		"statuses": _session.statuses(), "input_preserved": before == JSON.stringify(_source)}


# {
#   責務: [_stage: 各個体の実HP一回復・MP六消費・毒一件解除と所有状態を確認します]
#   処理: [1: 八行動ごとに明示状態付き戦闘を新規構築し、現在予約から本人回復を一回実行します]
#   引数: []
#   戻り値: [result: なし（void）。実適用が期待値に一致した行動だけを計上します]
# }
func _stage() -> void:
	if _session == null or _session.snapshot()["phase"] == "round_finished":
		# 毒を解除済みの高速経路で反復せず、八行動ごとの正規構築コストも計測へ含めます。
		_session = Session.new()
		assert(_session.start_with_statuses(_source["snapshots"]["allies"], _source["snapshots"]["enemies"], _source["initial_statuses"])["ok"])
		_action = Healing.new(_session, true)
		assert(_action.start_cure_heal(_source["teams"], _source["skills"], _source["initial_statuses"])["ok"])
		for key: Dictionary in _order:
			_session.take_damage(key, 100000000)
		assert(_session.begin_round(_order)["ok"])
	var offered: Dictionary = _session.next_actor()
	var ticket: Dictionary = offered["pending"]["ticket"]
	_last = _action.resolve({"ticket": ticket, "target": ticket["actor"], "skill_id": "spirit_recover", "roll": 0.0})
	assert(_last["ok"] and _last["executed"] and _last["spent_mp"] == 6 and _last["healed"] == 1 and _last["cure"]["cured"])
	var effects: Array = _session.status(ticket["actor"])["snapshot"]["status_effects"]
	assert(effects == [{"id": "lock", "removable": false}, "sleep"])
	var current: Dictionary = _last["session"]["teams"][ticket["actor"]["side"]][int(ticket["actor"]["id"])]
	if current["hp"] == 900000001 and current["mp"] == 999999994 and _last["cure"]["cured_name"] == "poison":
		_completed += 1
