# {
#   責務: [session_status_benchmark: 八体の明示状態付きSession開始・一体読取・全状態読取を毎反復で実行して計測します]
#   フィールド: []
# }
extends RefCounted
const Session = preload("res://engine/battle_session.gd")


# {
#   責務: [measure: 毎反復で新規Sessionを開始し、中央値と成功結果・入力/数値資源保持を返します]
#   処理: [1: 八体分の固定入力を用意し、事前実行後に複数サンプルを測定して実結果を照合します]
#   引数: [payload: iterations/samples/warmupの専用計測条件（Dictionary）]
#   戻り値: [result: 時間・回数・実開始/読取結果・原本保持条件（Dictionary）]
# }
static func measure(payload: Dictionary) -> Dictionary:
	var snapshots := {"allies": [], "enemies": []}
	var statuses := {"allies": {}, "enemies": {}}
	for side in ["allies", "enemies"]:
		for index in 4:
			var id := "member_" + str(index)
			var stats := {"hp": 100, "mp": 100, "attack": 10, "defense": 10, "speed": 10, "magic": 10}
			snapshots[side].append({"identity": {"id": id, "species_id": "slime", "name": id},
				"stats": stats, "hp": 100, "mp": 100, "alive": true, "fled": false})
			statuses[side][id] = [{"id": "lock", "removable": false},
				{"id": "poison", "metadata": {"deck": [1, {"kept": true}]}}, "sleep"]
	var before := JSON.stringify([snapshots, statuses])
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	for index in warmup:
		_lifecycle(snapshots, statuses)
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_lifecycle(snapshots, statuses)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	var result := _lifecycle(snapshots, statuses)
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples, "warmup": warmup,
		"actors": 8, "started": result["started"], "single": result["single"], "statuses": result["statuses"],
		"numeric": result["numeric"], "original_snapshots": snapshots, "original_statuses": statuses,
		"input_preserved": before == JSON.stringify([snapshots, statuses])}


# {
#   責務: [_lifecycle: 新規Sessionの実開始と個別/全体読取を実行し、観測結果を返します]
#   処理: [1: 八体の数値と明示状態を専用開始へ渡し、数値/状態の公開コピーを取得します]
#   引数: [
#     snapshots: 両陣営の満資源参加者（Dictionary）
#     statuses: 全参加者の初期状態（Dictionary）
#   ]
#   戻り値: [result: 実開始・個別/全体状態読取と数値snapshot（Dictionary）]
# }
static func _lifecycle(snapshots: Dictionary, statuses: Dictionary) -> Dictionary:
	var session = Session.new()
	var started: Dictionary = session.start_with_statuses(snapshots["allies"], snapshots["enemies"], statuses)
	return {"started": started, "single": session.status({"side": "allies", "id": "member_0"}),
		"statuses": session.statuses(), "numeric": session.snapshot()}
