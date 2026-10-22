# {
#   責務: [speed_multiplier_benchmark: 速度所有者の新規開始・再付与・期間なし強化・三回経過の実更新を反復計測します]
#   フィールド: []
# }
extends RefCounted

const SpeedState = preload("res://engine/combatant_speed_state.gd")
const INITIAL := 1.2
const APPLICATIONS := [{"multiplier": 1.5, "duration": 2}, {"multiplier": 1.3, "duration": 3}, {"multiplier": 1.4}]


# {
#   責務: [run: 固定した七操作の全結果を照合しながら、一ライフサイクルの中央値を測定します]
#   処理: [
#     1: 固定入力の基準観測と反復条件を用意し、事前実行します
#     2: 各計測回も新しい所有者で七操作を実行し、全反復の観測一致と実行件数を確認します
#     3: 中央値・固定入力・全操作の結果と反復条件を返します
#   ]
#   引数: [payload: iterations/samples/warmupを指定する専用計測辞書（Dictionary）]
#   戻り値: [result: microseconds/trace/input/条件/操作件数/一致フラグの計測辞書（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	var reference := _cycle()
	var successful := true
	var completed := 0
	# 事前実行も実更新を行い、失敗した高速経路を正常なライフサイクルとして扱いません。
	for _index in warmup:
		successful = _cycle() == reference and successful
		completed += 7
	var timings: Array = []
	for _sample in samples:
		var started := Time.get_ticks_usec()
		for _index in iterations:
			successful = _cycle() == reference and successful
			completed += 7
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[int(samples / 2)], "trace": reference,
		"input": {"initial": INITIAL, "applications": APPLICATIONS.duplicate(true), "ticks": 3},
		"iterations": iterations, "samples": samples, "warmup": warmup,
		"operations_completed": completed, "all_traces_match": successful}


# {
#   責務: [_cycle: 新しい一所有者で、倍率と期間の独立最大値・期間なし復元先・期限切れを実更新します]
#   処理: [1: 初期倍率1.2から三付与と三回経過を行い、七操作の結果を順番に返します]
#   引数: []
#   戻り値: [result: start/apply三回/elapse三回の実API結果列（Array）]
# }
static func _cycle() -> Array:
	# 所有者を毎回新規作成し、開始済み拒否や期限切れ後のno-opだけの計測にならないようにします。
	var state := SpeedState.new()
	var trace: Array = [state.start(INITIAL)]
	for request in APPLICATIONS:
		trace.append(state.apply_multiplier(request))
	for _index in 3:
		trace.append(state.elapse_round())
	return trace
