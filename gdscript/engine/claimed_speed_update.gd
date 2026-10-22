# {
#   責務: [claimed_speed_update: Sessionで照合済みの取得予約について、生存対象の速度強化を一回だけ委譲します]
#   フィールド: [
#     _resources: 生存読取だけに使うSession内部の陣営/ID別資源所有者索引（Dictionary）
#     _speeds: Sessionが所有する参加者速度集合。従来開始ではnullです（RefCounted）
#     _last_ticket: 直近の正常な速度付与に使った予約の独立コピー（Dictionary）
#   ]
# }
extends RefCounted
const Order = preload("res://engine/turn_order.gd")
var _resources: Dictionary
var _speeds: RefCounted
var _last_ticket: Dictionary = {}


# {
#   責務: [_init: Session内部の生存読取索引と速度集合を参照し、速度付与の一回記録を所有します]
#   処理: [1: Sessionへの逆参照を作らず、対象検査と速度委譲に必要な内部参照だけを保持します]
#   引数: [
#     resources: Session内部の資源所有者索引。公開要求として受け付けません（Dictionary）
#     speeds: 検証済み参加者速度集合、または従来開始のnull（RefCounted）
#   ]
#   戻り値: [result: なし（void）。数値資源・速度・予約を変更しません]
# }
func _init(resources: Dictionary, speeds: RefCounted) -> void:
	# RefCountedの循環を作らないため、呼出元Session自体は保持しません。
	_resources = resources
	_speeds = speeds


# {
#   責務: [apply: 最新生存を確認し、正常な速度付与だけを一予約一回として記録します]
#   処理: [
#     1: 速度設定・対象・最新生存と使用済み予約を確認します
#     2: 倍率と期間の更新を所有集合へ同期委譲し、成功した予約を独立保持します
#   ]
#   引数: [
#     ticket: Sessionが現在取得済み予約との厳密一致を確認した票（Dictionary）
#     target: 生存する味方/敵/本人のside/id。スキル対象制限は上位行動が確認します（Variant）
#     request: multiplierと任意durationだけの正規化/期間選択済み要求（Variant）
#     can_act: Sessionが最新行動者と両陣営の生存から求めた可否（bool）
#   ]
#   戻り値: [result: 速度所有者の独立結果、または速度/資源/一回記録を保持した拒否（Dictionary）]
# }
func apply(ticket: Dictionary, target: Variant, request: Variant, can_act: bool) -> Dictionary:
	# 弱い倍率による変化なしも正常な付与として数え、不正要求だけは修正後の再試行を許可します。
	var checked := _check_target(target, can_act)
	if not checked["ok"]:
		return checked
	if ticket == _last_ticket:
		return {"ok": false, "reason": "speed_multiplier_already_applied"}
	var result: Dictionary = _speeds.apply_multiplier(target, request)
	if result["ok"]:
		_last_ticket = ticket.duplicate(true)
	return result


# {
#   責務: [_check_target: 速度設定・対象の形式/存在/生存と最新行動可否を確認します]
#   処理: [1: 速度設定と対象を先に検査し、その後に行動者と両陣営の最新生存を要求します]
#   引数: [
#     target: 速度付与対象の候補キー（Variant）
#     can_act: Sessionが算出した最新行動可否（bool）
#   ]
#   戻り値: [result: ok=true、または具体的な理由付き拒否（Dictionary）]
# }
func _check_target(target: Variant, can_act: bool) -> Dictionary:
	# 速度強化は復活や逃走取消を行わず、対象不正を行動不能という別の理由で隠しません。
	if _speeds == null:
		return {"ok": false, "reason": "speed_not_configured"}
	if not Order.valid_key(target):
		return {"ok": false, "reason": "invalid_actor_key"}
	if not _resources[target["side"]].has(target["id"]):
		return {"ok": false, "reason": "actor_missing"}
	if not _resources[target["side"]][target["id"]].alive():
		return {"ok": false, "reason": "target_not_alive"}
	if not can_act:
		return {"ok": false, "reason": "actor_cannot_apply_speed"}
	return {"ok": true}
