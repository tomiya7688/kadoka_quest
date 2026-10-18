# {
#   責務: [status_physical_action_benchmark: 八体/千定義の新規構築込みで、MP消費・物理ダメージ・実付与・完了を反復測定します]
#   フィールド: [
#     _source: 固定八体・千定義・初期状態/耐性/装備を持つ共用入力（Dictionary）
#     _order: 同IDの両陣営を別キーで並べた固定八行動順（Array）
#     _session: 現在バッチの戦闘資源所有者（RefCounted）
#     _action: 現在バッチの専用物理行動（RefCounted）
#     _position: 現在バッチで完了した行動数（int）
#     _completed: 固定期待値と再送拒否を確認した累積行動数（int）
#     _last: 最後に実行した専用行動の結果（Dictionary）
#   ]
# }
extends RefCounted
const Inputs = preload("res://tests/status_physical_context_probe.gd")
const Session = preload("res://engine/battle_session.gd")
const Action = preload("res://engine/status_physical_skill_action.gd")
var _source := Inputs._inputs()
var _order: Array = []
var _session: RefCounted
var _action: RefCounted
var _position := 8
var _completed := 0
var _last: Dictionary = {}


# {
#   責務: [_init: 八体の固定入力から、陣営と個体IDを区別した行動順だけを準備します]
#   処理: [1: 固定された両陣営の個体順を保持し、sourceを変更せずside/idの列を作ります]
#   引数: []
#   戻り値: [result: なし（void）。Sessionは各八行動の直前に構築します]
# }
func _init() -> void:
	for side in ["allies", "enemies"]:
		for member: Dictionary in _source["teams"][side]:
			_order.append({"side": side, "id": member["snapshot"]["identity"]["id"]})


# {
#   責務: [measure: 初期構築込みの一行動中央値と、全反復の実更新/再送拒否・原本保持を返します]
#   処理: [1: 八行動の完全バッチ条件を検証し、事前実行と複数サンプルの正常な実行時間を測定します]
#   引数: [payload: iterations/samples/warmupの測定条件。反復/事前実行は八の倍数にしてください（Dictionary）]
#   戻り値: [result: 中央値・確認数・最後の行動/最終資源と状態・固定原本、または条件拒否（Dictionary）]
# }
func measure(payload: Dictionary) -> Dictionary:
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	if iterations % 8 != 0 or warmup % 8 != 0:
		return {"ok": false, "reason": "complete_rounds_required"}
	var before := JSON.stringify([_source, _order])
	for index in warmup:
		_stage()
	# 起動/I/Oは含めず、八行動ごとの新規Session/定義索引構築と更新確認は測定へ含めます。
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_stage()
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples, "warmup": warmup,
		"actors": 8, "definitions": _source["skills"]["skills"].size(), "completed": _completed,
		"last": _last, "numeric": _session.snapshot(), "statuses": _session.statuses(),
		"original_source": _source.duplicate(true), "original_order": _order.duplicate(true),
		"input_preserved": before == JSON.stringify([_source, _order])}


# {
#   責務: [_stage: 最新予約で一体へ18ダメージと出血を実適用し、3MP消費と完了後の再送拒否を確認します]
#   処理: [1: 八行動ごとに新規構築し、固定結果と再送後の状態不変が一致した行動だけを数えます]
#   引数: []
#   戻り値: [result: なし（void）。確認済み累積行動数と最後の結果を保持します]
# }
func _stage() -> void:
	if _position == 8:
		_start_batch()
	var ticket: Dictionary = _session.next_actor()["pending"]["ticket"]
	var target := {"side": "enemies" if ticket["actor"]["side"] == "allies" else "allies", "id": ticket["actor"]["id"]}
	var request := {"ticket": ticket, "target": target, "skill_id": "mod_status_hit", "critical_roll": 0.5,
		"variance": 1.0, "status_roll": 0.49}
	_last = _action.resolve(request)
	var numeric: Dictionary = _session.snapshot()
	var statuses: Dictionary = _session.statuses()
	var repeated: Dictionary = _action.resolve(request)
	# 高速な拒否や重複付与だけを成功件数にせず、各反復の実更新と一回完了を確認します。
	var verified: bool = _last.get("ok", false) and _last.get("executed", false) and _last.get("spent_mp") == 3 \
		and _last.get("dealt") == 18 and _last.get("numbers", {}).get("physical", {}).get("remaining_mp") == 97 \
		and _last.get("numbers", {}).get("physical", {}).get("remaining_hp") == 82 \
		and _last.get("applied_status", {}).get("applied", false) and _last.get("applied_status", {}).get("apply_chance") == 0.5 \
		and not repeated.get("ok", true) and numeric == _session.snapshot() and statuses == _session.statuses()
	if verified:
		_completed += 1
	_position += 1


# {
#   責務: [_start_batch: 固定原本から新しい八体のSessionと専用行動を構築し、全員未付与の初回ラウンドを始めます]
#   処理: [1: 満資源/明示状態と千定義を専用開始へ渡し、成功後にバッチ位置を0へ戻します]
#   引数: []
#   戻り値: [result: なし（void）。前バッチの消費済み資源や付与済み状態を再利用しません]
# }
func _start_batch() -> void:
	var snapshots := {"allies": [], "enemies": []}
	for side in ["allies", "enemies"]:
		for member: Dictionary in _source["teams"][side]:
			snapshots[side].append(member["snapshot"])
	_session = Session.new()
	assert(_session.start_with_statuses(snapshots["allies"], snapshots["enemies"], _source["statuses"])["ok"])
	_action = Action.new(_session)
	assert(_action.start(_source["teams"], _source["skills"], _source["statuses"])["ok"])
	assert(_session.begin_round(_order)["ok"])
	_position = 0
