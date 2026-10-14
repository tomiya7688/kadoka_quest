# {
#   責務: [session_status_application_benchmark: 八行動ごとに新規Sessionを構築し、予約取得/実付与/再判定拒否/完了を反復測定します]
#   フィールド: [
#     _source: 固定八体の数値/初期状態と付与要求（Dictionary）
#     _order: 同速度の八体を陣営/IDで並べた固定順（Array）
#     _session: 現在の八行動バッチのSession（RefCounted）
#     _position: 現在バッチで完了した行動数（int）
#     _completed: 実付与と他の状態/数値不変を確認した累積行動数（int）
#     _last: 最後の付与・再判定拒否・個別読取・完了結果（Dictionary）
#   ]
# }
extends RefCounted
const Session = preload("res://engine/battle_session.gd")
var _source := {"snapshots": {"allies": [], "enemies": []}, "statuses": {"allies": {}, "enemies": {}},
	"request": {"effect": {"id": "bleeding", "display_name": "出血", "chance": 0.4,
		"metadata": {"deck": ["a", {"kept": true}]}}, "resistance_level": "weak", "roll": 0.49}}
var _order: Array = []
var _session: RefCounted
var _position := 8
var _completed := 0
var _last: Dictionary = {}


# {
#   責務: [_init: 同IDの両陣営各四体を満資源で用意し、三件の状態を各個体へ独立に設定します]
#   処理: [1: 数値/初期状態/順序を固定し、各行動が別の敵対象を更新する入力を作ります]
#   引数: []
#   戻り値: [result: なし（void）。正規コンテンツや利用者保存先は読み書きしません]
# }
func _init() -> void:
	# 同IDも陣営ごとに分離し、実追加前の一覧を毎バッチで再利用可能な固定原本にします。
	for side in ["allies", "enemies"]:
		for index in 4:
			var id := "member_" + str(index)
			_source["snapshots"][side].append({"identity": {"id": id, "species_id": "slime", "name": id},
				"stats": {"hp": 100, "mp": 100, "attack": 10, "defense": 10, "magic": 10, "speed": 10},
				"hp": 100, "mp": 100, "alive": true, "fled": false})
			_source["statuses"][side][id] = [{"id": "lock", "removable": false}, "poison",
				{"id": "mod", "metadata": {"deck": [1, {"kept": true}]}}]
			_order.append({"side": side, "id": id})


# {
#   責務: [measure: 初期構築込みの一付与判定中央値と、全反復の実追加/拒否/原本保持を返します]
#   処理: [1: 八行動の完全バッチ条件を確認し、事前実行と複数サンプルを測定します]
#   引数: [payload: iterations/samples/warmupの専用条件。各反復区分は八の倍数にしてください（Dictionary）]
#   戻り値: [result: 性能/実確認数/最後の実更新/最終数値と状態/固定原本、または反復条件の拒否（Dictionary）]
# }
func measure(payload: Dictionary) -> Dictionary:
	# 最終八体の完全更新を照合するため、測定と事前実行の反復数を八の倍数に制限します。
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	if iterations % 8 != 0 or warmup % 8 != 0:
		return {"ok": false, "reason": "complete_rounds_required"}
	var before := JSON.stringify([_source, _order])
	for index in warmup:
		_stage()
	# 時間に起動/I/Oを含めず、実行ごとの新規八体構築と更新確認は含めて中央値を取ります。
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_stage()
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "actors": 8, "completed": _completed, "last": _last, "numeric": _session.snapshot(),
		"statuses": _session.statuses(), "original_source": _source.duplicate(true), "original_order": _order.duplicate(true),
		"input_preserved": before == JSON.stringify([_source, _order])}


# {
#   責務: [_stage: 取得済み予約で一体へ実付与し、別対象への同予約再判定拒否と数値/他個体不変を確認します]
#   処理: [
#     1: 八行動ごとにSessionと初回順序を新規構築します
#     2: 現在票を取得し、敵対象への出血実追加・再判定拒否・読取・完了を確認します
#   ]
#   引数: []
#   戻り値: [result: なし（void）。全条件が一致した反復だけをcompletedへ加算します]
# }
func _stage() -> void:
	# 付与済みの高速重複だけで反復せず、八体の新規保持コストを八行動ごとに含めます。
	if _position == 8:
		_session = Session.new()
		assert(_session.start_with_statuses(_source["snapshots"]["allies"], _source["snapshots"]["enemies"], _source["statuses"])["ok"])
		assert(_session.begin_round(_order)["ok"])
		_position = 0
	var offered: Dictionary = _session.next_actor()
	var ticket: Dictionary = offered["pending"]["ticket"]
	assert(_session.claim(ticket)["can_execute"])
	var target := {"side": "enemies" if ticket["actor"]["side"] == "allies" else "allies", "id": ticket["actor"]["id"]}
	# 更新対象一体以外と数値/防御の前後を照合し、付与済み重複の高速経路を成功にしません。
	var numeric: Dictionary = _session.snapshot()
	var guards: Dictionary = _session.effects()
	var statuses: Dictionary = _session.statuses()
	var applied: Dictionary = _session.apply_status_application(ticket, target, _source["request"])
	var repeated: Dictionary = _session.apply_status_application(ticket, ticket["actor"], _source["request"])
	var single: Dictionary = _session.status(target)
	var candidate: Dictionary = _source["request"]["effect"].duplicate(true)
	candidate.erase("chance")
	candidate["removable"] = true
	statuses["teams"][target["side"]][target["id"]].append(candidate)
	var verified: bool = applied.get("ok", false) and applied.get("applied", false) and applied.get("apply_chance") == 0.5 \
		and repeated == {"ok": false, "reason": "status_application_already_applied"} \
		and single == {"ok": true, "snapshot": {"status_effects": statuses["teams"][target["side"]][target["id"]]}} \
		and numeric == _session.snapshot() and guards == _session.effects() and statuses == _session.statuses()
	# 正常な完了まで一致した反復だけを計上し、予約途中の結果を完了済みと扱いません。
	var finished: Dictionary = _session.finish(ticket)
	_last = {"applied": applied, "repeated": repeated, "single": single, "finished": finished}
	if verified and finished["ok"]:
		_completed += 1
	_position += 1
