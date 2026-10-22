# {
#   責務: [status_physical_failure_session: 付与付き物理の内部拒否を一箇所へ注入し、実更新の順序と二重実行防止を検査します]
#   フィールド: [
#     _failure_operation: 拒否を注入するclaim/pay/damage/status/finishの操作名（String）
#     calls: 更新呼出順を記録する検証専用一覧（Array）
#   ]
# }
extends "res://engine/battle_session.gd"
var _failure_operation: String
var calls: Array = []


# {
#   責務: [_init: 実Sessionを継承する検証専用所有者へ、拒否を注入する操作名を固定します]
#   処理: [1: 正規データを読み書きせず、ケース専用の拒否位置だけを保持します]
#   引数: [failure: claim/pay/damage/status/finishのいずれかの検証操作名（String）]
#   戻り値: [result: なし（void）]
# }
func _init(failure: String) -> void:
	_failure_operation = failure


# {
#   責務: [claim: 予約取得の呼出を記録し、指定ケースだけは実取得前に拒否します]
#   処理: [1: claimを記録し、注入対象でなければ実Sessionの一回取得を実行します]
#   引数: [ticket: 実Sessionへ渡す予約識別子（Variant）]
#   戻り値: [result: 注入拒否、または実Sessionの予約取得結果（Dictionary）]
# }
func claim(ticket: Variant) -> Dictionary:
	calls.append("claim")
	return {"ok": false, "reason": "injected_claim_failure"} if _failure_operation == "claim" else super.claim(ticket)


# {
#   責務: [pay_mp: MP支払いの呼出を記録し、指定ケースだけは消費前に拒否します]
#   処理: [1: payを記録し、注入対象でなければ実SessionのMP支払いを実行します]
#   引数: [
#     key: MPを消費する参加者のside/id（Variant）
#     cost: 行動が計算したMP消費量（Variant）
#   ]
#   戻り値: [result: 注入拒否、または実MP支払い結果（Dictionary）]
# }
func pay_mp(key: Variant, cost: Variant) -> Dictionary:
	calls.append("pay")
	return {"ok": false, "reason": "injected_payment_failure"} if _failure_operation == "pay" else super.pay_mp(key, cost)


# {
#   責務: [take_damage: HP減少の呼出を記録し、指定ケースだけはダメージ適用前に拒否します]
#   処理: [1: damageを記録し、注入対象でなければ実SessionのHP減少を実行します]
#   引数: [
#     key: ダメージ対象のside/id（Variant）
#     amount: 予測済みの物理ダメージ（Variant）
#   ]
#   戻り値: [result: 注入拒否、または実HP適用結果（Dictionary）]
# }
func take_damage(key: Variant, amount: Variant) -> Dictionary:
	calls.append("damage")
	return {"ok": false, "reason": "injected_damage_failure"} if _failure_operation == "damage" else super.take_damage(key, amount)


# {
#   責務: [apply_status_application: 状態付与の呼出を記録し、指定ケースだけは状態更新前に拒否します]
#   処理: [1: statusを記録し、注入対象でなければ実Sessionの予約付き一件付与を実行します]
#   引数: [
#     ticket: 現在取得済みの予約識別子（Variant）
#     target: 状態付与対象のside/id（Variant）
#     request: 定義/耐性/明示判定値の付与条件（Variant）
#   ]
#   戻り値: [result: 注入拒否、または実状態付与結果（Dictionary）]
# }
func apply_status_application(ticket: Variant, target: Variant, request: Variant) -> Dictionary:
	calls.append("status")
	return {"ok": false, "reason": "injected_status_failure"} if _failure_operation == "status" else super.apply_status_application(ticket, target, request)


# {
#   責務: [finish: 予約完了の呼出を記録し、指定ケースだけはカーソル更新前に拒否します]
#   処理: [1: finishを記録し、注入対象でなければ実Sessionの予約完了を実行します]
#   引数: [ticket: 完了する現在取得済み予約（Variant）]
#   戻り値: [result: 注入拒否、または実予約完了結果（Dictionary）]
# }
func finish(ticket: Variant) -> Dictionary:
	calls.append("finish")
	return {"ok": false, "reason": "injected_finish_failure"} if _failure_operation == "finish" else super.finish(ticket)
