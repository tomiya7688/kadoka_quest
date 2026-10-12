# {
#   責務: [combatant_status_state: 戦闘個体一体の順序付き状態一覧を独立保持し、明示判定による一件治療と重複しない一件付与を適用します]
#   フィールド: [
#     _effects: 原本と独立した検証済み状態一覧（Array）
#     _initialized: 状態一覧の初期化が成功済みかどうか（bool）
#   ]
# }
extends RefCounted

const ApplyContract = preload("res://engine/status_apply_contract.gd")
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
#   責務: [prepare_application: 最新の所有一覧から付与確率と判定値の要否を取得し、状態を変更しません]
#   処理: [1: 外部一覧/予測の上書きを拒否し、所有一覧と効果/耐性を純粋付与準備へ委譲します]
#   引数: [request: effectと任意resistance_levelだけの要求。rollと外部状態一覧は受けません（Variant）]
#   戻り値: [result: 独立候補/一覧・確率・判定要否、または所有状態を保持した拒否（Dictionary）]
# }
func prepare_application(request: Variant) -> Dictionary:
	# 判定値を取得する前に最新一覧を正本として渡し、準備結果で所有一覧を変更しません。
	var checked := _application_request(request, false)
	if not checked["ok"]:
		return checked
	return ApplyContract.prepare_application(checked["request"])


# {
#   責務: [quote_application: 最新の所有一覧で一件付与を予測し、予測による所有状態の変更を行いません]
#   処理: [1: 状態所有者の開始/要求を確認し、所有一覧・効果・耐性・明示rollを純粋付与予測へ委譲します]
#   引数: [request: effectと任意resistance_level/rollだけの要求。予測一覧や付与済み結果は受けません（Variant）]
#   戻り値: [result: status_apply_quote区分の独立予測、または所有状態を保持した拒否（Dictionary）]
# }
func quote_application(request: Variant) -> Dictionary:
	# 外部の一覧上書きを入口で拒否し、確率と重複の規則は純粋契約へ委譲します。
	var checked := _application_request(request, true)
	if not checked["ok"]:
		return checked
	return ApplyContract.quote_application(checked["request"])


# {
#   責務: [apply: 最新の所有一覧で付与を再判定し、成立した候補一件だけを末尾へ独立コピーして追加します]
#   処理: [1: quote_applicationで再検証し、付与成立時だけ新規候補を保持して結果区分を実更新へ変更します]
#   引数: [request: effectと任意resistance_level/rollだけの要求。外部一覧/古い予測を更新命令へ使えません（Variant）]
#   戻り値: [result: combatant_status_apply区分の独立結果。不成立/重複/拒否では所有一覧を保持します（Dictionary）]
# }
func apply(request: Variant) -> Dictionary:
	# 返却一覧全体で所有一覧を置換せず、新規候補だけを別コピーして返却値の編集から守ります。
	var quoted := quote_application(request)
	if not quoted["ok"]:
		return quoted
	if quoted["applied"]:
		_effects.append(quoted["resulting_status_effects"].back().duplicate(true))
	quoted["scope"] = "combatant_status_apply"
	return quoted


# {
#   責務: [_application_request: 状態所有者の開始と付与要求キーを検査し、内部一覧を純粋契約へ渡す専用要求を作ります]
#   処理: [1: 未開始/辞書以外/未知要求を拒否し、外部要求の浅いコピーへ所有一覧を設定します]
#   引数: [
#     request: 効果と任意耐性/判定値の付与要求（Variant）
#     allow_roll: 準備はfalse、予測/実更新はtrueに固定した判定値キーの許可（bool）
#   ]
#   戻り値: [result: 内部委譲専用request、または理由付き拒否。内部要求は公開APIから直接返しません（Dictionary）]
# }
func _application_request(request: Variant, allow_roll: bool) -> Dictionary:
	# 状態一覧・候補・古い結果を要求から持ち込ませず、この個体の最新一覧を正本にします。
	if not _initialized:
		return _reject("not_initialized")
	if not request is Dictionary:
		return _reject("invalid_status_apply_request")
	for field in request:
		if field not in ["effect", "resistance_level"] and not (allow_roll and field is String and field == "roll"):
			return _reject("unsupported_status_apply_request")
	var forwarded: Dictionary = request.duplicate()
	forwarded["status_effects"] = _effects
	return {"ok": true, "request": forwarded}


# {
#   責務: [_reject: 所有する状態一覧を変えず、状態操作の拒否理由を返します]
#   処理: [1: ok=falseと具体的な拒否理由を返します]
#   引数: [reason: 初期化または要求形式を拒否した理由（String）]
#   戻り値: [result: ok=falseとreasonの辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
