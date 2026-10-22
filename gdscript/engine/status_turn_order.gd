# {
#   責務: [status_turn_order: 最新状態と明示一時倍率で補正した速度を使い、資源を変更せず行動順を計算します]
#   フィールド: []
# }
extends RefCounted

const Order = preload("res://engine/turn_order.gd")
const Stats = preload("res://engine/status_stat_contract.gd")
const REQUEST_KEYS := ["allies", "enemies", "statuses", "speed_multipliers", "shuffle_order"]


# {
#   責務: [plan: 全参加者の最新状態と一時倍率を検証し、補正済み速度順と生存者の初期順を非破壊で返します]
#   処理: [
#     1: 五キー要求・厳密数値参加者・参加者に一致する状態/倍率の辞書を検証します
#     2: 各個体の状態能力値予測へ委譲し、専用コピーの速度だけを補正後整数へ置き換えます
#     3: 生存者の明示順と安定ソートを基礎順序契約へ委譲し、全成功時だけ順序と速度を返します
#   ]
#   引数: [request: allies/enemiesの六キーsnapshot列、全員分のstatuses/speed_multipliersと生存者shuffle_orderだけを持つ要求（Variant）]
#   戻り値: [result: 独立したinitial/order/speedsとscope=status_turn_order、または部分結果のない理由付き拒否（Dictionary）]
# }
static func plan(request: Variant) -> Dictionary:
	# 任意のeffective_speedや状態入りsnapshotを、実装済みの補正として受け入れません。
	if not request is Dictionary:
		return {"ok": false, "reason": "invalid_status_turn_request"}
	if request.size() != REQUEST_KEYS.size():
		return {"ok": false, "reason": "invalid_status_turn_fields"}
	for field in REQUEST_KEYS:
		if not request.has(field):
			return {"ok": false, "reason": "invalid_status_turn_fields"}
	var participants := Order.participants(request["allies"], request["enemies"])
	if not participants["ok"]:
		return participants
	for field in ["statuses", "speed_multipliers"]:
		var matched := _match_map(request, field)
		if not matched["ok"]:
			return matched
	var prepared := _adjusted_teams(request)
	if not prepared["ok"]:
		return prepared
	# 同速判定・死亡/逃走の除外・明示shuffleの厳密検査は既存の順序契約を共用します。
	var ordered := Order.plan(prepared["allies"], prepared["enemies"], request["shuffle_order"])
	if not ordered["ok"]:
		return ordered
	ordered["scope"] = "status_turn_order"
	ordered["speeds"] = prepared["speeds"]
	return ordered


# {
#   責務: [_match_map: 状態または一時倍率の辞書が両陣営の全参加者に一対一で対応するか確認します]
#   処理: [1: allies/enemiesだけの二辞書と各陣営のID集合を照合し、欠落/未知IDを拒否します]
#   引数: [
#     request: 数値参加者を検証済みの内部要求（Dictionary）
#     field: statusesまたはspeed_multipliersの検査対象名（String）
#   ]
#   戻り値: [result: 一致ならok=true、不正ならreason/fieldと必要なside/id（Dictionary）]
# }
static func _match_map(request: Dictionary, field: String) -> Dictionary:
	# ID集合を読む前に辞書と陣営の形を確認し、不正型による実行診断を防ぎます。
	var entries: Variant = request[field]
	if not entries is Dictionary or entries.size() != Order.SIDES.size():
		return {"ok": false, "reason": "invalid_turn_map", "field": field}
	for side in Order.SIDES:
		var team: Variant = entries.get(side)
		if not team is Dictionary:
			return {"ok": false, "reason": "invalid_turn_map", "field": field, "side": side}
		# 死亡/逃走個体も数値参加者であり、状態や倍率の省略を暗黙の初期値へ置き換えません。
		if team.size() != request[side].size():
			return {"ok": false, "reason": "turn_context_mismatch", "field": field, "side": side}
		for member: Dictionary in request[side]:
			var id: String = member["identity"]["id"]
			if not team.has(id):
				return {"ok": false, "reason": "turn_context_mismatch", "field": field, "side": side, "id": id}
	return {"ok": true}


# {
#   責務: [_adjusted_teams: 全参加者の状態補正を予測し、補正済み速度だけを持つ独立数値snapshotを作ります]
#   処理: [1: 味方/敵の枠順で全員の状態と倍率を共用検証し、全成功時だけ両陣営コピーと速度辞書を返します]
#   引数: [request: 数値参加者と状態/倍率のID集合を検証済みの内部要求（Dictionary）]
#   戻り値: [result: 両陣営の独立snapshotとspeeds、またはreasonと拒否対象side/idだけの失敗（Dictionary）]
# }
static func _adjusted_teams(request: Dictionary) -> Dictionary:
	# 途中まで成功した補正値は外へ公開せず、全参加者の検証が終わるまで専用結果へ蓄積します。
	var result := {"ok": true, "allies": [], "enemies": [], "speeds": {"allies": {}, "enemies": {}}}
	for side in Order.SIDES:
		for member: Dictionary in request[side]:
			var id: String = member["identity"]["id"]
			var quote := Stats.quote_stats({"defense": member["stats"]["defense"], "speed": member["stats"]["speed"],
				"status_effects": request["statuses"][side][id], "speed_multiplier": request["speed_multipliers"][side][id]})
			if not quote["ok"]:
				return {"ok": false, "reason": quote["reason"], "side": side, "id": id}
			# 元の能力値を再入力できるよう、外部snapshotの速度・HPMP・生存フラグを変更しません。
			var adjusted := member.duplicate(true)
			adjusted["stats"]["speed"] = quote["speed"]
			result[side].append(adjusted)
			result["speeds"][side][id] = quote["speed"]
	return result
