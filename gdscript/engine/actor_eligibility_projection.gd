# {
#   責務: [actor_eligibility_projection: 検証済みの最新生存情報から、行動可否と独立した友軍/敵の読取結果を組み立てます]
#   フィールド: []
# }
extends RefCounted


# {
#   責務: [project: 生存敵なしを最優先に、行動者の最新生存と両陣営の生存者から行動可否を返します]
#   処理: [
#     1: 敵なし/行動者の生存という共用の優先規則でreasonを決めます
#     2: 呼出元の検証済みキー/生存者列を複製し、内部参照を返さずに結果を作ります
#   ]
#   引数: [
#     key: 呼出元が形式/存在を確認した行動者のside/id（Dictionary）
#     actor_alive: 最新の資源所有者または検証済みsnapshotの生存値（bool）
#     friends: 呼出元が検証した同陣営の生存snapshot列。入力順を保ちます（Array）
#     foes: 呼出元が検証した敵陣営の生存snapshot列。入力順を保ちます（Array）
#   ]
#   戻り値: [result: ok/can_act/stop/reason/actor/friends/foesの独立読取。予約取得や入力検証の代わりではありません（Dictionary）]
# }
static func project(key: Dictionary, actor_alive: bool, friends: Array, foes: Array) -> Dictionary:
	# 公開の生入力はOrder.check_actor、所有資源はSessionの開始/更新APIで検証します。
	# この投影は形式検査を省略する公開要求モードではなく、検証後の結果組立だけを共用します。
	var reason := "ready"
	if foes.is_empty():
		reason = "no_living_foes"
	elif not actor_alive:
		reason = "actor_not_alive"
	return {"ok": true, "can_act": reason == "ready", "stop": foes.is_empty(), "reason": reason,
		"actor": key.duplicate(true), "friends": friends.duplicate(true), "foes": foes.duplicate(true)}
