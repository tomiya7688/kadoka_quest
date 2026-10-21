# {
#   責務: [claimed_speed_benchmark: 八行動ごとの新規Sessionで、速度実付与・再送拒否・終端復元を測定します]
#   フィールド: [
#     _source: 固定八体の数値/状態/初期倍率と期間付き付与要求（Dictionary）
#     _order: 同速度八体の明示順（Array）
#     _session: 現在バッチの実Session（RefCounted）
#     _position: 現在の八行動バッチで完了した件数（int）
#     _completed: 実付与と全状態保持を確認した累積件数（int）
#     _last: 最後の実付与/再送拒否/読取/完了の独立結果（Dictionary）
#     _expected: 固定入力だけから構築する現在バッチの期待速度。製品状態から逆算しません（Dictionary）
#   ]
# }
extends RefCounted
const Session = preload("res://engine/battle_session.gd")
var _source := {"snapshots": {"allies": [], "enemies": []}, "statuses": {"allies": {}, "enemies": {}},
	"multipliers": {"allies": {}, "enemies": {}}, "request": {"multiplier": 1.5, "duration": 1}}
var _order: Array = []
var _session: RefCounted
var _position := 8
var _completed := 0
var _last: Dictionary = {}
var _expected: Dictionary = {}


# {
#   責務: [_init: 同IDの両陣営各四体と初期倍率1.2を固定原本として用意します]
#   処理: [1: 満資源・空状態・倍率1.2・同速の明示順を新規データとして構築します]
#   引数: []
#   戻り値: [result: なし（void）。正規データと保存先を読み書きしません]
# }
func _init() -> void:
	# 付与前の固定原本を再利用し、更新済み倍率へのno-opだけの反復を防ぎます。
	for side in ["allies", "enemies"]:
		for index in 4:
			var id := "member_" + str(index)
			_source["snapshots"][side].append({"identity": {"id": id, "species_id": "slime", "name": id},
				"stats": {"hp": 100, "mp": 100, "attack": 10, "defense": 10, "magic": 10, "speed": 10},
				"hp": 100, "mp": 100, "alive": true, "fled": false})
			_source["statuses"][side][id] = []
			_source["multipliers"][side][id] = 1.2
			_order.append({"side": side, "id": id})


# {
#   責務: [measure: 初期構築込みの一速度付与段階を反復し、全正常更新数と中央値を返します]
#   処理: [1: 完全八行動条件を確認し、事前実行と複数サンプルで実付与を測定します]
#   引数: [payload: iterations/samples/warmup。反復数と事前実行数は八の倍数です（Dictionary）]
#   戻り値: [result: 時間/全実更新数/最終状態/固定原本、または反復条件の拒否（Dictionary）]
# }
func measure(payload: Dictionary) -> Dictionary:
	# 最後の八体全員の実更新を独立照合できるよう、端数バッチは測定前に拒否します。
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	if iterations % 8 != 0 or warmup % 8 != 0:
		return {"ok": false, "reason": "complete_rounds_required"}
	var before := JSON.stringify([_source, _order])
	for index in warmup:
		_stage()
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_stage()
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "actors": 8, "completed": _completed, "last": _last,
		"numeric": _session.snapshot(), "statuses": _session.statuses(), "speeds": _session.speeds(),
		"guards": _session.effects(), "original_source": _source.duplicate(true), "original_order": _order.duplicate(true),
		"input_preserved": before == JSON.stringify([_source, _order])}


# {
#   責務: [_stage: 一体の速度を1.5へ実更新し、再送拒否・終端前保持・八体の期限復元を確認します]
#   処理: [
#     1: 八行動ごとに新規Sessionと初回順序を構築します
#     2: 取得済み票で反対陣営の同IDへ実付与し、別対象への再送拒否と独立読取を照合します
#     3: 末尾のfinishでは八体の倍率1.2への復元を照合し、正常完了した実更新だけを累積します
#   ]
#   引数: []
#   戻り値: [result: なし（void）。確認できた段階だけをcompletedに数えます]
# }
func _stage() -> void:
	# 毎回の対象に未更新の所有者を用意し、拒否や弱い倍率だけの高速経路で通しません。
	if _position == 8:
		_session = Session.new()
		assert(_session.start_with_statuses(_source["snapshots"]["allies"], _source["snapshots"]["enemies"],
			_source["statuses"], _source["multipliers"])["ok"])
		assert(_session.begin_round(_order)["ok"])
		_expected = _baseline_speeds()
		_position = 0
	var offered: Dictionary = _session.next_actor()
	var ticket: Dictionary = offered["pending"]["ticket"]
	assert(_session.claim(ticket)["can_execute"])
	var target := {"side": "enemies" if ticket["actor"]["side"] == "allies" else "allies", "id": ticket["actor"]["id"]}
	var numeric: Dictionary = _session.snapshot()
	var guards: Dictionary = _session.effects()
	var statuses: Dictionary = _session.statuses()
	# 先行段階で誤って期間が減っていても期待値へ取り込まず、固定原本からの追跡値と照合します。
	_expected["teams"][target["side"]][target["id"]] = {"speed_multiplier": 1.5, "remaining_turns": 1, "baseline_multiplier": 1.2}
	var expected: Dictionary = _expected
	var applied: Dictionary = _session.apply_speed_multiplier(ticket, target, _source["request"])
	var repeated: Dictionary = _session.apply_speed_multiplier(ticket, ticket["actor"], _source["request"])
	var single: Dictionary = _session.speed(target)
	var verified: bool = applied == {"ok": true, "scope": "combatant_speed_apply", "snapshot": expected["teams"][target["side"]][target["id"]]} \
		and repeated == {"ok": false, "reason": "speed_multiplier_already_applied"} \
		and single == {"ok": true, "snapshot": expected["teams"][target["side"]][target["id"]]} \
		and expected == _session.speeds() and numeric == _session.snapshot() \
		and guards == _session.effects() and statuses == _session.statuses()
	# 最後のfinishだけが全員を期限切れにし、途中のfinishは期間を進めません。
	var finished: Dictionary = _session.finish(ticket)
	if _position == 7:
		verified = verified and _session.speeds() == _baseline_speeds()
	_last = {"applied": applied, "repeated": repeated, "single": single, "finished": finished}
	if verified and finished["ok"]:
		_completed += 1
	_position += 1


# {
#   責務: [_baseline_speeds: 固定八体の初期倍率1.2・残り0・復元先1.2を独立した期待値にします]
#   処理: [1: 固定入力の陣営/IDだけを使い、開始時と期限切れ時に一致すべき速度辞書を構築します]
#   引数: []
#   戻り値: [result: 製品の読取結果から独立したbattle_speed_onlyの期待辞書（Dictionary）]
# }
func _baseline_speeds() -> Dictionary:
	# 製品snapshotとの自己一致で早期失効や復元漏れを見逃さないため、値は固定仕様から作ります。
	var teams := {"allies": {}, "enemies": {}}
	for side in ["allies", "enemies"]:
		for index in 4:
			teams[side]["member_" + str(index)] = {"speed_multiplier": 1.2, "remaining_turns": 0, "baseline_multiplier": 1.2}
	return {"teams": teams, "scope": "battle_speed_only"}
