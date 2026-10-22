# {
#   責務: [claimed_status_updates: Sessionが検証した取得済み予約について、対象の最新状態更新と種類別の一回判定を保持します]
#   フィールド: [
#     _resources: Session内部の陣営/個体ID別の資源所有者索引。生存読取だけに使います（Dictionary）
#     _statuses: Sessionが専用開始で保持する状態集合。従来開始ではnullです（RefCounted）
#     _last_tickets: 治療/付与それぞれの直近の正常判定済み予約。外部へ返しません（Dictionary）
#   ]
# }
extends RefCounted

const Order = preload("res://engine/turn_order.gd")
var _resources: Dictionary
var _statuses: RefCounted
var _last_tickets := {"cure": {}, "application": {}}


# {
#   責務: [_init: Session内部の資源索引と状態集合を参照し、予約付き状態更新の所有者を構築します]
#   処理: [1: 生存読取と状態委譲の参照だけを保持し、Sessionへの逆参照や数値のコピーを作りません]
#   引数: [
#     resources: Sessionが保持する資源所有者の内部索引。公開要求ではありません（Dictionary）
#     statuses: 検証済み状態集合、または従来開始のnull（RefCounted）
#   ]
#   戻り値: [result: なし（void）。資源を更新せず、状態更新に必要な内部参照だけを保持します]
# }
func _init(resources: Dictionary, statuses: RefCounted) -> void:
	# Sessionを逆参照しないため、RefCounted同士の循環保持を作りません。
	_resources = resources
	_statuses = statuses


# {
#   責務: [cure: Sessionが照合した取得済み予約で、同陣営の生存対象を一回だけ治療します]
#   処理: [1: 固定の治療区分で共用対象検査と最新一覧の一件治療へ委譲します]
#   引数: [
#     ticket: Sessionが現在の取得済み予約との一致を確認した行動票（Dictionary）
#     target: 同陣営の治療対象を指定するside/id（Variant）
#     request: cure_chanceと任意rollだけの治療要求（Variant）
#     can_act: Sessionが最新の行動者/両陣営の生存から計算した可否（bool）
#   ]
#   戻り値: [result: 独立した一件治療結果、または数値/状態/判定記録を保持した拒否（Dictionary）]
# }
func cure(ticket: Dictionary, target: Variant, request: Variant, can_act: bool) -> Dictionary:
	# 呼出元の要求で治療/付与の区分を切り替えず、入口ごとに固定します。
	return _update("cure", ticket, target, request, can_act)


# {
#   責務: [apply: Sessionが照合した取得済み予約で、生存対象への付与を一回だけ判定します]
#   処理: [1: 固定の付与区分で共用対象検査と最新一覧の一件付与へ委譲します]
#   引数: [
#     ticket: Sessionが現在の取得済み予約との一致を確認した行動票（Dictionary）
#     target: 味方/敵/本人を含む生存対象のside/id。スキルの対象制限は上位行動の責務です（Variant）
#     request: effectと任意resistance_level/rollだけの付与要求（Variant）
#     can_act: Sessionが最新の行動者/両陣営の生存から計算した可否（bool）
#   ]
#   戻り値: [result: 独立した一件付与結果、または数値/状態/判定記録を保持した拒否（Dictionary）]
# }
func apply(ticket: Dictionary, target: Variant, request: Variant, can_act: bool) -> Dictionary:
	# 付与確率・重複・状態形式は状態所有者へ任せ、ここで再実装しません。
	return _update("application", ticket, target, request, can_act)


# {
#   責務: [_update: 対象検査後に最新一覧を更新し、正常な不成立を含む一回判定を種類別に記録します]
#   処理: [
#     1: 状態設定・対象・最新生存・同種類の使用済み予約を確認します
#     2: 状態集合の治療/付与を同期実行し、ok=trueだけを独立票で記録します
#   ]
#   引数: [
#     kind: 内部入口が固定したcureまたはapplicationの更新種類（String）
#     ticket: Sessionが検証済みの取得済み行動票（Dictionary）
#     target: 更新対象のside/id（Variant）
#     request: 対応する状態所有者へそのまま渡す厳密要求（Variant）
#     can_act: 最新の行動者/両陣営生存に基づく可否（bool）
#   ]
#   戻り値: [result: 状態所有者の独立結果、または非破壊的拒否（Dictionary）]
# }
func _update(kind: String, ticket: Dictionary, target: Variant, request: Variant, can_act: bool) -> Dictionary:
	# 不正要求を使用済みにせず、正常な確率不成立/重複/候補なしだけは再抽選を防ぎます。
	var checked := _check_target(kind, ticket["actor"], target, can_act)
	if not checked["ok"]:
		return checked
	if ticket == _last_tickets[kind]:
		return _failure("status_cure_already_applied" if kind == "cure" else "status_application_already_applied")
	var result: Dictionary = _statuses.cure(target, request) if kind == "cure" else _statuses.apply(target, request)
	if result["ok"]:
		_last_tickets[kind] = ticket.duplicate(true)
	return result


# {
#   責務: [_check_target: 状態設定・対象の形式/存在/生存と、治療だけの同陣営条件を確認します]
#   処理: [1: 状態設定と対象を先に確認し、その後でSessionが算出した最新行動可否を確認します]
#   引数: [
#     kind: 治療または付与の内部固定区分（String）
#     actor: 取得済み予約の行動者side/id（Dictionary）
#     target: 状態更新対象の候補キー（Variant）
#     can_act: Sessionが最新生存から求めた行動可否（bool）
#   ]
#   戻り値: [result: ok=true、または状態/資源を保持した具体的理由の拒否（Dictionary）]
# }
func _check_target(kind: String, actor: Dictionary, target: Variant, can_act: bool) -> Dictionary:
	# 従来治療の拒否順を維持し、対象不正を行動不能という別の理由で隠しません。
	if _statuses == null:
		return _failure("status_not_configured")
	if not Order.valid_key(target):
		return _failure("invalid_actor_key")
	if not _resources[target["side"]].has(target["id"]):
		return _failure("actor_missing")
	if kind == "cure" and target["side"] != actor["side"]:
		return _failure("target_not_friend")
	if not _resources[target["side"]][target["id"]].alive():
		return _failure("target_not_alive")
	if not can_act:
		return _failure("actor_cannot_cure" if kind == "cure" else "actor_cannot_apply_status")
	return {"ok": true}


# {
#   責務: [_failure: 状態更新も使用済み記録も変更せず、拒否理由を返します]
#   処理: [1: ok=falseと具体的なreasonだけを返します]
#   引数: [reason: 状態更新を許可しなかった具体的な理由（String）]
#   戻り値: [result: ok=falseとreasonの辞書（Dictionary）]
# }
static func _failure(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
