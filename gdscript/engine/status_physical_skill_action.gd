# {
#   責務: [status_physical_skill_action: 最新予約・資源・状態を検証し、MP消費・物理ダメージ・生存対象への一件付与を同期実行します]
#   フィールド: [
#     _session: HPMP・状態・行動予約識別子ticketの所有者（RefCounted）
#     _preflight: 開始情報を独立保持し、非消費で最新値を検査する専用処理（RefCounted）
#   ]
# }
extends RefCounted
const Preflight = preload("res://engine/status_physical_skill_preflight.gd")
const Quote = preload("res://engine/status_physical_skill_contract.gd")
const Stats = preload("res://engine/status_stat_contract.gd")
const Effects = preload("res://engine/status_effect_contract.gd")
const REQUEST_FIELDS := ["ticket", "target", "skill_id", "critical_roll", "variance"]
const SCOPE := "explicit_status_physical_skill_only"
var _session: RefCounted
var _preflight: RefCounted


# {
#   責務: [_init: 実更新先のSessionと、その同じSessionを読む非消費検査を構築します]
#   処理: [1: 資源や状態を複製せず、所有者参照と専用検査だけを保持します]
#   引数: [session: 戦闘資源・状態・予約を所有するbattle_session.gd（RefCounted）]
#   戻り値: [result: なし（void）。開始情報はstartで設定します]
# }
func _init(session: RefCounted) -> void:
	_session = session
	_preflight = Preflight.new(session)


# {
#   責務: [start: 初回ラウンド前の数値/初期状態と一致する開始情報を、専用検査へ一度だけ設定します]
#   処理: [1: 非消費検査の検証/独立保持へ委譲し、成功時は専用行動の設定完了を返します]
#   引数: [
#     teams: 満資源snapshotと習得/許可装備・状態耐性を持つ両陣営（Variant）
#     skills: schema_version=1とskills配列を持つ正規/MOD一覧（Variant）
#     initial_statuses: 全参加者の空状態も明示したside/id別初期状態（Variant）
#   ]
#   戻り値: [result: 行動設定の成功scope、またはSession/設定を保持した拒否（Dictionary）]
# }
func start(teams: Variant, skills: Variant, initial_statuses: Variant) -> Dictionary:
	# 同じ定義索引を検査と実行で共用し、別Sessionや別開始情報を混在させません。
	var configured: Dictionary = _preflight.start(teams, skills, initial_statuses)
	return {"ok": true, "scope": SCOPE} if configured["ok"] else configured


# {
#   責務: [inspect: 付与付き物理の三キー要求を、資源/予約を消費しない専用検査へ渡します]
#   処理: [1: 開始時の索引と最新Sessionを読む検査へ委譲します]
#   引数: [request: ticket/敵target/skill_idだけを持つ非消費検査要求（Variant）]
#   戻り値: [result: 独立した非消費検査結果、または拒否（Dictionary）]
# }
func inspect(request: Variant) -> Dictionary:
	return _preflight.inspect(request)


# {
#   責務: [resolve: 検証済みの付与付き物理を、一回の予約取得からMP消費・HP減少・任意付与・完了まで実行します]
#   処理: [
#     1: 非消費で最新条件と明示乱数を検証し、行動不能ならSessionへ取消を委譲します
#     2: 予約を一回取得し、予測済みMP支払いと物理ダメージを資源所有者へ渡します
#     3: 正の実ダメージ後も生存する対象だけへ状態一件を適用し、予約完了後の独立結果を返します
#   ]
#   引数: [request: ticket/敵target/skill_id/critical_roll/varianceと任意status_rollだけを持つ行動要求（Variant）]
#   戻り値: [result: 実消費・実ダメージ・付与結果・Session/状態コピー、行動取消、または理由付き拒否（Dictionary）]
# }
func resolve(request: Variant) -> Dictionary:
	# 不正/不足はclaim前に返し、提示中の予約を使った修正や別行動を可能にします。
	var checked := _validate(request)
	if not checked["ok"]:
		return checked
	# 予測からfinishまでawaitやcallbackを挟まず、所有状態を外部に更新させません。
	var claimed: Dictionary = _session.claim(request["ticket"])
	if not claimed["ok"]:
		return claimed
	if not claimed["can_execute"]:
		return {"ok": true, "executed": false, "reason": claimed["reason"], "session": claimed["session"]}
	var numbers: Dictionary = checked["numbers"]
	var physical: Dictionary = numbers["physical"]
	var paid: Dictionary = _session.pay_mp(request["ticket"]["actor"], physical["mp_cost"])
	if not paid["ok"]:
		return _failed_update("action_payment_failed")
	var damaged: Dictionary = _session.take_damage(request["target"], physical["damage"])
	if not damaged["ok"]:
		return _failed_update("action_application_failed")
	var applied: Dictionary = {}
	if numbers["status_eligible"]:
		# 外部の予測一覧は上書きせず、Sessionが保持する最新一覧に付与を委譲します。
		applied = _session.apply_status_application(request["ticket"], request["target"], {
			"effect": checked["effect"], "resistance_level": checked["resistance"], "roll": request.get("status_roll")})
		if not applied["ok"]:
			return _failed_update("action_status_failed")
	var finished: Dictionary = _session.finish(request["ticket"])
	if not finished["ok"]:
		return _failed_update("action_finish_failed")
	return {"ok": true, "executed": true, "scope": SCOPE,
		"ticket": request["ticket"].duplicate(true), "target": request["target"].duplicate(true),
		"numbers": numbers, "spent_mp": paid["spent"], "dealt": damaged["dealt"], "applied_status": applied,
		"session": finished["session"], "statuses": _session.statuses()}


# {
#   責務: [_validate: 厳密な行動要求を最新の専用検査へ渡し、状態補正と統合予測が成功した場合だけ実行準備を返します]
#   処理: [1: 必須/任意キーを検証し、最新予約・習得・資源・状態から純粋予測へ委譲します]
#   引数: [request: 明示乱数を含む付与付き物理の行動要求（Variant）]
#   戻り値: [result: numbers/effect/resistance、行動取消用の成功、または非破壊的拒否（Dictionary）]
# }
func _validate(request: Variant) -> Dictionary:
	# 威力・guard・MP・外部状態・耐性を呼出側から上書きさせません。
	if not request is Dictionary:
		return _reject("invalid_status_physical_request")
	for field in request:
		if field not in REQUEST_FIELDS and field != "status_roll":
			return _reject("invalid_status_physical_request")
	for field in REQUEST_FIELDS:
		if not request.has(field):
			return _reject("invalid_status_physical_request")
	var current := inspect({"ticket": request["ticket"], "target": request["target"], "skill_id": request["skill_id"]})
	if not current["ok"]:
		return current
	var resistance := _resistance(current)
	var predicted := _predict(current, request, resistance)
	if not predicted["ok"]:
		return predicted
	return {"ok": true, "numbers": predicted, "effect": current["skill"]["status_effect"],
		"resistance": resistance}


# {
#   責務: [_predict: 最新の出血補正済み防御力と資源・装備・状態耐性を、共用の物理/付与予測へ渡します]
#   処理: [1: 実行可能時は最新状態を補正し、取消時は資源を使わない入力で明示乱数だけを検証します]
#   引数: [
#     current: 専用非消費検査が成功した独立した最新読取（Dictionary）
#     request: 型とキーを検証した行動要求（Dictionary）
#     resistance: 開始時の状態耐性から新規付与IDに対応して取得した耐性名（String）
#   ]
#   戻り値: [result: 物理/付与の純粋予測、または予約を変更しない拒否（Dictionary）]
# }
func _predict(current: Dictionary, request: Dictionary, resistance: String) -> Dictionary:
	var can_act: bool = current["eligibility"]["can_act"]
	var attacker: Dictionary = current["actor_resources"]
	var defender: Dictionary = current["target_resources"]
	var defense := 0
	if can_act:
		var effective := Stats.quote_stats({"defense": defender["stats"]["defense"], "speed": defender["stats"]["speed"],
			"status_effects": current["target_status"]["status_effects"]})
		if not effective["ok"]:
			return effective
		defense = effective["defense"]
	# 行動不能はMP不足へ置き換えません。HP0の一時予測では付与判定値の省略を許可します。
	var values := {"attack": attacker["stats"]["attack"] if can_act else 1, "defense": defense,
		"target_hp": defender["hp"] if can_act else 0, "current_mp": attacker["mp"] if can_act else current["skill"]["mp_cost"],
		"guard": current["target_guard"], "critical_roll": request["critical_roll"], "variance": request["variance"],
		"power_multiplier": current["equipment"]["power_multiplier"], "fixed_bonus_damage": current["equipment"]["fixed_bonus_damage"],
		"status_effects": current["target_status"]["status_effects"], "status_resistance_level": resistance}
	if request.has("status_roll"):
		values["status_roll"] = request["status_roll"]
	return Quote.quote_damage(current["skill"], values)


# {
#   責務: [_resistance: 新規付与IDに対応する開始時の種族状態耐性を取得します]
#   処理: [1: 新規IDの前後空白を共用規則で除き、未指定の耐性はnormalにします]
#   引数: [current: 正規化前の効果定義と状態耐性辞書を持つ専用検査結果（Dictionary）]
#   戻り値: [result: 状態付与専用の耐性名（String）]
# }
func _resistance(current: Dictionary) -> String:
	var id := Effects.normalized_id(current["skill"]["status_effect"].get("id", ""))
	return current["target_status_resistances"].get(id, "normal")


# {
#   責務: [_failed_update: 予約取得後の内部適用失敗を、再実行できない拒否として明示します]
#   処理: [1: 具体的な失敗理由とaction_consumed=trueを返し、取得済み予約を再提示しません]
#   引数: [reason: MP支払い・HP適用・状態適用・完了の内部拒否理由（String）]
#   戻り値: [result: ok=false/reason/action_consumedの辞書。適用済み資源の巻き戻しは行いません（Dictionary）]
# }
func _failed_update(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason, "action_consumed": true}


# {
#   責務: [_reject: 行動要求の失敗を、資源や予約を消費しない理由付き辞書として返します]
#   処理: [1: ok=falseと具体的なreasonを返します]
#   引数: [reason: 行動要求の形式を拒否した理由（String）]
#   戻り値: [result: ok=false/reasonの辞書（Dictionary）]
# }
func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
