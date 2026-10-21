# {
#   責務: [battle_speed_state: 両陣営の参加者ごとに速度所有者を保持し、独立読取と指定個体への速度付与を委譲します]
#   フィールド: [
#     _by_id: 陣営と個体IDで検索する速度所有者。外部へ公開しません（Dictionary）
#     _initialized: 全参加者の速度初期化が成功済みかどうか（bool）
#   ]
# }
extends RefCounted

const Speed = preload("res://engine/combatant_speed_state.gd")
const Order = preload("res://engine/turn_order.gd")
var _by_id: Dictionary = {"allies": {}, "enemies": {}}
var _initialized := false


# {
#   責務: [start: 全参加者の初期倍率を検証し、全員成功した場合だけ速度所有者を一度保持します]
#   処理: [
#     1: 数値参加者と明示倍率の陣営/ID集合を検証します
#     2: 各個体の倍率検証を速度所有者へ委譲し、全成功後に参照を保持します
#   ]
#   引数: [
#     snapshots: allies/enemiesだけを持つ六キー数値参加者列（Variant）
#     initial_multipliers: 全参加者に一致するside/id別倍率。省略/nullは全員1です（Variant）
#   ]
#   戻り値: [result: ok=true、または未開始を保持したreasonと必要なside/id（Dictionary）]
# }
func start(snapshots: Variant, initial_multipliers: Variant = null) -> Dictionary:
	# 不正な末尾個体があっても、先に作った所有者を部分公開せず正常入力で再試行できます。
	if _initialized:
		return {"ok": false, "reason": "already_initialized"}
	if not snapshots is Dictionary or snapshots.size() != 2:
		return {"ok": false, "reason": "invalid_speed_participants"}
	var participants := Order.participants(snapshots.get("allies"), snapshots.get("enemies"))
	if not participants["ok"]:
		return participants
	var matched := _match_ids(snapshots, initial_multipliers)
	if not matched["ok"]:
		return matched
	var owners := {"allies": {}, "enemies": {}}
	for side in Order.SIDES:
		for member: Dictionary in snapshots[side]:
			var id: String = member["identity"]["id"]
			var multiplier: Variant = 1.0 if initial_multipliers == null else initial_multipliers[side][id]
			var owner = Speed.new()
			var started: Dictionary = owner.start(multiplier)
			if not started["ok"]:
				started.merge({"side": side, "id": id})
				return started
			owners[side][id] = owner
	_by_id = owners
	_initialized = true
	return {"ok": true}


# {
#   責務: [_match_ids: 明示初期倍率の陣営と全個体IDが数値参加者に過不足なく一致するか確認します]
#   処理: [1: nullの全員1指定を許可し、明示辞書は両陣営・個体数・各IDを厳密照合します]
#   引数: [
#     snapshots: 数値参加者の検証が成功した辞書（Dictionary）
#     multipliers: 検証するside/id別倍率、または全員1を示すnull（Variant）
#   ]
#   戻り値: [result: ok=true、または辞書形式/ID集合不一致の拒否（Dictionary）]
# }
static func _match_ids(snapshots: Dictionary, multipliers: Variant) -> Dictionary:
	# 一人分でも明示した辞書では欠落を1へ補完せず、設定漏れを開始前に検出します。
	if multipliers == null:
		return {"ok": true}
	if not multipliers is Dictionary or multipliers.size() != 2:
		return {"ok": false, "reason": "invalid_initial_speed_multipliers"}
	for side in Order.SIDES:
		var entries: Variant = multipliers.get(side)
		if not entries is Dictionary:
			return {"ok": false, "reason": "invalid_initial_speed_multipliers", "side": side}
		if entries.size() != snapshots[side].size():
			return {"ok": false, "reason": "speed_context_mismatch", "side": side}
		for member: Dictionary in snapshots[side]:
			var id: String = member["identity"]["id"]
			if not entries.has(id):
				return {"ok": false, "reason": "speed_context_mismatch", "side": side, "id": id}
	return {"ok": true}


# {
#   責務: [snapshot: 全員の速度倍率・残り期間・復元先を、数値資源と別の独立辞書で返します]
#   処理: [1: 未開始なら空辞書、開始済みなら各速度所有者の三キーsnapshotを集めます]
#   引数: []
#   戻り値: [result: side/id別teamsとscope=battle_speed_only、または未開始の空辞書（Dictionary）]
# }
func snapshot() -> Dictionary:
	# 死亡/逃走で参加者を削除せず、開始済みの全所有者について独立した速度辞書を返します。
	if not _initialized:
		return {}
	var teams := {"allies": {}, "enemies": {}}
	for side in Order.SIDES:
		for id: String in _by_id[side]:
			teams[side][id] = _by_id[side][id].snapshot()
	return {"teams": teams, "scope": "battle_speed_only"}


# {
#   責務: [multipliers: 行動順契約へ渡す全参加者の最新倍率だけを独立辞書で返します]
#   処理: [1: 未開始なら空辞書、開始済みなら残り期間や所有者を除いて現在倍率だけを投影します]
#   引数: []
#   戻り値: [result: allies/enemies別のidから倍率への辞書、または未開始の空辞書（Dictionary）]
# }
func multipliers() -> Dictionary:
	# 状態読取の全辞書を再構築せず、最大八体の行動順に必要な現在倍率だけを取り出します。
	if not _initialized:
		return {}
	var result := {"allies": {}, "enemies": {}}
	for side in Order.SIDES:
		for id: String in _by_id[side]:
			result[side][id] = _by_id[side][id].snapshot()["speed_multiplier"]
	return result


# {
#   責務: [read: 厳密なside/idで指定した参加者の速度状態を独立コピーで返します]
#   処理: [1: 未開始・不正キー・不在個体を拒否し、指定所有者の三キーsnapshotを返します]
#   引数: [key: allies/enemiesのsideと空でないidだけを持つ参加者キー（Variant）]
#   戻り値: [result: ok=true/snapshot、または状態を保持したreason付き拒否（Dictionary）]
# }
func read(key: Variant) -> Dictionary:
	# 同じIDが両陣営にあっても、陣営索引を先に選び別々の所有者を読み取ります。
	var checked := _check_key(key)
	return checked if not checked["ok"] else {"ok": true, "snapshot": _by_id[key["side"]][key["id"]].snapshot()}


# {
#   責務: [apply_multiplier: 指定参加者の最新倍率・期間・復元先の更新を個体速度所有者へ委譲します]
#   処理: [1: 初期化と厳密side/idを共用検査し、倍率要求を指定個体へそのまま渡します]
#   引数: [
#     key: 更新する参加者のside/idだけを持つキー（Variant）
#     request: multiplierと任意durationだけの正規化/期間選択済み要求（Variant）
#   ]
#   戻り値: [result: 個体速度所有者の独立結果、または全参加者を保持した拒否（Dictionary）]
# }
func apply_multiplier(key: Variant, request: Variant) -> Dictionary:
	# 集合は倍率・期間の最大値規則を再実装せず、他の参加者や数値資源を変更しません。
	var checked := _check_key(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].apply_multiplier(request)


# {
#   責務: [_check_key: 個別速度読取と付与に共通の初期化・参加者キー・存在を確認します]
#   処理: [1: 開始済みか確認してから、厳密side/idと指定所有者の存在を検査します]
#   引数: [key: 速度所有者を検索する候補キー（Variant）]
#   戻り値: [result: ok=true、または未開始/不正/不在を示す拒否（Dictionary）]
# }
func _check_key(key: Variant) -> Dictionary:
	# 陣営別の索引を使い、同IDの別陣営や無関係な参加者を走査しません。
	if not _initialized:
		return {"ok": false, "reason": "not_initialized"}
	if not Order.valid_key(key):
		return {"ok": false, "reason": "invalid_actor_key"}
	if not _by_id[key["side"]].has(key["id"]):
		return {"ok": false, "reason": "actor_missing"}
	return {"ok": true}
