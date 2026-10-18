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
	return _result(key, actor_alive, friends.duplicate(true), foes.duplicate(true))


# {
#   責務: [from_resources: Sessionが検証/所有する資源から最新の生存者を一度だけ複製し、行動可否を組み立てます]
#   処理: [1: HP正/未逃走の所有者だけをsnapshotへ変換し、外部入力の検査を省く要求モードは設けません]
#   引数: [
#     key: Sessionの検証済み行動順または予約に由来する行動者のside/id（Dictionary）
#     actor_alive: 指定行動者の資源所有者から読んだ最新の生存判定（bool）
#     friends: Sessionが構築/所有する同陣営のcombatant_state列。JSON入力ではありません（Array）
#     foes: Sessionが構築/所有する敵陣営のcombatant_state列。JSON入力ではありません（Array）
#   ]
#   戻り値: [result: 所有資源を公開しない独立した行動可否/生存者コピー。資源更新や予約取得はしません（Dictionary）]
# }
static func from_resources(key: Dictionary, actor_alive: bool, friends: Array, foes: Array) -> Dictionary:
	# 新規snapshotは呼出元にも所有者にも共有されないため、結果作成時に再複製しません。
	return _result(key, actor_alive, _living_snapshots(friends), _living_snapshots(foes))


# {
#   責務: [_living_snapshots: 検証済み資源所有者の現在のHP/逃走を読み、生存者だけの独立した数値コピーを作ります]
#   処理: [1: 最大四体の所有者を入力順で読み、死亡や逃走をキャッシュせずに生存を判定します]
#   引数: [team: Sessionの開始処理が構築した同陣営のcombatant_state所有者列（Array）]
#   戻り値: [result: HP正/未逃走の参加者だけを含む、新しいsnapshot配列（Array）]
# }
static func _living_snapshots(team: Array) -> Array:
	var living: Array = []
	for state: RefCounted in team:
		if state.alive():
			living.append(state.snapshot())
	return living


# {
#   責務: [_result: 独立コピー済みの生存者列から、敵不在を優先する共用の行動可否結果を作ります]
#   処理: [1: 敵なし/行動者死亡の優先規則を適用し、行動者キーだけを新たに複製します]
#   引数: [
#     key: 入力とは独立に返す行動者の検証済みside/id（Dictionary）
#     actor_alive: 資源所有者または検証済みsnapshotに由来する最新生存（bool）
#     friends: projectまたはfrom_resourcesが新規複製した友軍生存者列（Array）
#     foes: projectまたはfrom_resourcesが新規複製した敵生存者列（Array）
#   ]
#   戻り値: [result: ok/can_act/stop/reason/actor/friends/foesの独立読取（Dictionary）]
# }
static func _result(key: Dictionary, actor_alive: bool, friends: Array, foes: Array) -> Dictionary:
	var reason := "ready"
	if foes.is_empty():
		reason = "no_living_foes"
	elif not actor_alive:
		reason = "actor_not_alive"
	return {"ok": true, "can_act": reason == "ready", "stop": foes.is_empty(), "reason": reason,
		"actor": key.duplicate(true), "friends": friends, "foes": foes}
