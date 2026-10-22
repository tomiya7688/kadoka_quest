# {
#   責務: [battle_status_state: 参加者別の状態を独立保持し、独立読取と最新一覧からの一件治療/付与を個体所有者へ委譲します]
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
	# 再開始や参加者とのID不一致を検証段階で拒否し、所有者を部分公開しません。
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
	# 全個体の検証後だけ参照を切り替え、不正開始からの正常な再試行を可能にします。
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
	# 所有者自体ではなく独立snapshotを返し、対象検査の拒否理由を保持します。
	var checked := _check_key(key)
	return checked if not checked["ok"] else {"ok": true, "snapshot": _by_id[key["side"]][key["id"]].snapshot()}


# {
#   責務: [cure: 指定参加者の最新所有状態から一件の治療を個体状態所有者へ委譲します]
#   処理: [1: 初期化とside/idを共用検証し、所有者へ明示確率/判定値を渡します]
#   引数: [
#     key: 治療対象のside/idキー（Variant）
#     request: cure_chanceと任意rollだけの治療条件。状態や予測の持ち込みは拒否します（Variant）
#   ]
#   戻り値: [result: 実治療の独立結果、または状態を保持した拒否（Dictionary）]
# }
func cure(key: Variant, request: Variant) -> Dictionary:
	# 対象を決める集合の処理と、最新一覧で治療する個体側の規則を分離します。
	var checked := _check_key(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].cure(request)



# {
#   責務: [prepare_application: 指定参加者の最新一覧に基づく付与準備を個体所有者へ委譲します]
#   処理: [1: 初期化・side/idの形式/存在を共用検査し、指定個体のprepare_applicationへ要求を渡します]
#   引数: [
#     key: 付与対象のallies/enemiesのsideと個体idだけを持つキー（Variant）
#     request: effectと任意resistance_levelだけの準備条件。roll/外部一覧は拒否します（Variant）
#   ]
#   戻り値: [result: 個体所有者の独立した結果、または全参加者の状態を保持した拒否（Dictionary）]
# }
func prepare_application(key: Variant, request: Variant) -> Dictionary:
	# 陣営とIDの両方で対象を確定し、同IDの別陣営や他個体を変更しません。
	var checked := _check_key(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].prepare_application(request)


# {
#   責務: [quote_application: 指定参加者の最新一覧で一件付与を予測し、参加者の状態を変更しません]
#   処理: [1: 初期化・side/idの形式/存在を共用検査し、指定個体のquote_applicationへ要求を渡します]
#   引数: [
#     key: 付与対象のallies/enemiesのsideと個体idだけを持つキー（Variant）
#     request: effectと任意resistance_level/rollだけの付与条件。外部一覧/予測は拒否します（Variant）
#   ]
#   戻り値: [result: 個体所有者の独立した結果、または全参加者の状態を保持した拒否（Dictionary）]
# }
func quote_application(key: Variant, request: Variant) -> Dictionary:
	# 陣営とIDの両方で対象を確定し、同IDの別陣営や他個体を変更しません。
	var checked := _check_key(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].quote_application(request)


# {
#   責務: [apply: 指定参加者への重複しない一件付与を最新一覧の個体所有者へ委譲します]
#   処理: [1: 初期化・side/idの形式/存在を共用検査し、指定個体のapplyへ要求を渡します]
#   引数: [
#     key: 付与対象のallies/enemiesのsideと個体idだけを持つキー（Variant）
#     request: effectと任意resistance_level/rollだけの付与条件。外部一覧/予測は拒否します（Variant）
#   ]
#   戻り値: [result: 個体所有者の独立した結果、または全参加者の状態を保持した拒否（Dictionary）]
# }
func apply(key: Variant, request: Variant) -> Dictionary:
	# 陣営とIDの両方で対象を確定し、同IDの別陣営や他個体を変更しません。
	var checked := _check_key(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].apply(request)


# {
#   責務: [_check_key: 個別読取・治療・付与に共通の初期化・参加者キー・存在条件を確認します]
#   処理: [1: 初期化済みで厳密side/idに一致する所有者がある場合だけ成功を返します]
#   引数: [key: 個体別状態を検索する候補キー（Variant）]
#   戻り値: [result: ok=true、または具体的理由の拒否。所有者は公開しません（Dictionary）]
# }
func _check_key(key: Variant) -> Dictionary:
	# 未開始・形式不正・対象不在を順に判定し、陣営別の索引で存在だけを検査します。
	if not _initialized:
		return {"ok": false, "reason": "not_initialized"}
	if not Order.valid_key(key):
		return {"ok": false, "reason": "invalid_actor_key"}
	if not _by_id[key["side"]].has(key["id"]):
		return {"ok": false, "reason": "actor_missing"}
	return {"ok": true}
