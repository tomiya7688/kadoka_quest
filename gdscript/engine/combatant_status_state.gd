# {
#   責務: [combatant_status_state: 戦闘個体一体の順序付き状態一覧を独立保持し、明示判定による一件治療だけを適用します]
#   フィールド: [
#     _effects: 原本と独立した検証済み状態一覧（Array）
#     _initialized: 状態一覧の初期化が成功済みかどうか（bool）
#   ]
# }
extends RefCounted

const CureContract = preload("res://engine/status_cure_contract.gd")
var _effects: Array = []
var _initialized := false


# {
#   責務: [start: 未開始の状態所有者へ検証済み一覧の独立コピーを一度だけ保持します]
#   処理: [1: 再初期化を拒否し、共用治療契約が検証/コピーした一覧だけを保持します]
#   引数: [effects: 文字列またはJSON互換辞書の順序付き状態一覧。空一覧も有効です（Variant）]
#   戻り値: [result: ok=trueと独立snapshot、または未開始状態を保持した拒否（Dictionary）]
# }
func start(effects: Variant) -> Dictionary:
	# 不正一覧で開始済みにせず、正しい一覧による再試行を可能にします。
	if _initialized:
		return _reject("already_initialized")
	var selected := CureContract.select_candidate(effects)
	if not selected["ok"]:
		return selected
	_effects = selected["effects"]
	_initialized = true
	return {"ok": true, "snapshot": snapshot()}


# {
#   責務: [snapshot: 保持中の状態一覧を編集可能な独立コピーで返し、所有一覧を公開しません]
#   処理: [1: 未開始なら空辞書、開始済みならstatus_effects一キーの独立辞書を返します]
#   引数: []
#   戻り値: [result: 独立したstatus_effects、または未開始の空辞書。数値資源の6キーsnapshotとは別です（Dictionary）]
# }
func snapshot() -> Dictionary:
	if not _initialized:
		return {}
	return {"status_effects": _effects.duplicate(true)}


# {
#   責務: [quote_cure: 保持中の最新状態一覧を使い、明示確率・判定値による一件治療を変更なしで予測します]
#   処理: [1: 初期化と要求キーを確認し、所有一覧・確率・判定値を純粋治療契約へ委譲します]
#   引数: [request: cure_chanceと任意rollだけを持つ要求。状態一覧の外部上書きは禁止します（Variant）]
#   戻り値: [result: status_cure_quote区分の独立予測、または所有状態を保持した拒否（Dictionary）]
# }
func quote_cure(request: Variant) -> Dictionary:
	# 状態・確率・判定の規則を二重実装せず、状態の正本だけをこの所有者から渡します。
	if not _initialized:
		return _reject("not_initialized")
	if not request is Dictionary:
		return _reject("invalid_status_cure_request")
	for field in request:
		if field not in ["cure_chance", "roll"]:
			return _reject("unsupported_status_cure_request")
	return CureContract.quote_cure({"status_effects": _effects,
		"cure_chance": request.get("cure_chance"), "roll": request.get("roll")})


# {
#   責務: [cure: 最新の所有一覧で治療を再判定し、成立した場合だけ候補一件を所有一覧から除きます]
#   処理: [1: quote_cureの検証済み結果に従い一件だけ除き、独立した結果の区分を実状態更新へ変更します]
#   引数: [request: cure_chanceと任意rollだけの要求。予測結果・候補位置・残存一覧を直接渡せません（Variant）]
#   戻り値: [result: combatant_status_cure区分の一件治療結果。不成立/拒否は一覧を保持します（Dictionary）]
# }
func cure(request: Variant) -> Dictionary:
	# 外部の古い予測を信頼せず同期して再判定します。行動予約やMP消費はここでは扱いません。
	var quoted := quote_cure(request)
	if not quoted["ok"]:
		return quoted
	if quoted["cured"]:
		_effects.remove_at(quoted["candidate_index"])
	quoted["scope"] = "combatant_status_cure"
	return quoted


# {
#   責務: [_reject: 所有する状態一覧を変えず、状態操作の拒否理由を返します]
#   処理: [1: ok=falseと具体的な拒否理由を返します]
#   引数: [reason: 初期化または要求形式を拒否した理由（String）]
#   戻り値: [result: ok=falseとreasonの辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
