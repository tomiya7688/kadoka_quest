# {
#   責務: [battle_status_state: 両陣営の参加者ごとに状態所有者を独立保持し、読取専用のコピーを返します]
#   フィールド: [
#     _by_id: allies/enemiesと個体idをキーとする状態所有者。外部へ返しません（Dictionary）
#     _initialized: 全参加者の状態初期化が成功済みかどうか（bool）
#   ]
# }
extends RefCounted
const Status = preload("res://engine/combatant_status_state.gd")
const InitialMap = preload("res://engine/initial_status_map.gd")
const Order = preload("res://engine/turn_order.gd")
var _by_id: Dictionary = {"allies": {}, "enemies": {}}
var _initialized := false


# {
#   責務: [start: 全参加者に一致する初期状態を検証し、全員成功した場合だけ状態所有者を一度保持します]
#   処理: [
#     1: 数値参加者と初期状態のID集合を共用契約で照合します
#     2: 未公開の個体別状態所有者へ一覧検証を委譲し、全員成功後に保持します
#   ]
#   引数: [
#     snapshots: allies/enemies別の六キー数値参加者列（Variant）
#     initial_statuses: 全参加者の初期状態をside/id別に明示した辞書。空状態も[]と指定します（Variant）
#   ]
#   戻り値: [result: 全員初期化できればok=true、不正なら未開始を保持したreasonと必要なside/id（Dictionary）]
# }
func start(snapshots: Variant, initial_statuses: Variant) -> Dictionary:
	if _initialized:
		return {"ok": false, "reason": "already_initialized"}
	var checked := InitialMap.validate(snapshots, initial_statuses)
	if not checked["ok"]:
		return checked
	# 途中で一体の状態が不正でも、既に検証した他個体を公開しません。
	var owners := {"allies": {}, "enemies": {}}
	for side in Order.SIDES:
		for member: Dictionary in snapshots[side]:
			var id: String = member["identity"]["id"]
			var owner = Status.new()
			var initialized: Dictionary = owner.start(initial_statuses[side][id])
			if not initialized["ok"]:
				initialized["side"] = side
				initialized["id"] = id
				return initialized
			owners[side][id] = owner
	_by_id = owners
	_initialized = true
	return {"ok": true}


# {
#   責務: [snapshot: 保持中の全状態一覧を、数値資源や状態所有者を含まない独立コピーで返します]
#   処理: [1: 未開始は空辞書、開始済みは各状態所有者のコピーをside/id別に集めます]
#   引数: []
#   戻り値: [result: 独立したteamsの状態配列とscope=battle_status_only、または未開始の空辞書（Dictionary）]
# }
func snapshot() -> Dictionary:
	if not _initialized:
		return {}
	var teams := {"allies": {}, "enemies": {}}
	for side in Order.SIDES:
		for id: String in _by_id[side]:
			teams[side][id] = _by_id[side][id].snapshot()["status_effects"]
	return {"teams": teams, "scope": "battle_status_only"}


# {
#   責務: [read: 指定参加者の状態一覧を検証済み陣営/個体IDから取得し、独立コピーで返します]
#   処理: [1: 初期化・side/idの形式と存在を確認し、個体別所有者のsnapshotへ委譲します]
#   引数: [key: allies/enemiesのsideと空でない個体idだけを持つ辞書（Variant）]
#   戻り値: [result: ok=trueとstatus_effects一キーのsnapshot、または理由付き拒否（Dictionary）]
# }
func read(key: Variant) -> Dictionary:
	if not _initialized:
		return {"ok": false, "reason": "not_initialized"}
	if not Order.valid_key(key):
		return {"ok": false, "reason": "invalid_actor_key"}
	if not _by_id[key["side"]].has(key["id"]):
		return {"ok": false, "reason": "actor_missing"}
	# 所有者そのものを返さず、読取結果から状態更新を行えないようにします。
	return {"ok": true, "snapshot": _by_id[key["side"]][key["id"]].snapshot()}
