# {
#   責務: [physical_skill_action: 習得済み単体物理スキルの単一claim・MP支払い・HP適用・finish]
#   フィールド: [
#     _session: 資源とticketの所有者（RefCounted）
#     _context: 開始時の独立情報（Dictionary）
#   ]
# }
extends RefCounted
const Context = preload("res://engine/physical_skill_context.gd")
const Quote = preload("res://engine/physical_skill_contract.gd")
const Order = preload("res://engine/turn_order.gd")
const REQUEST_FIELDS := ["ticket", "target", "skill_id", "critical_roll", "variance"]
var _session: RefCounted
var _context: Dictionary = {}


# {
#   責務: [_init: 適用先のSessionを保持する]
#   処理: [1: 依存先を設定する]
#   引数: [session: 戦闘資源とticketの所有者（RefCounted）]
#   戻り値: [result: なし（void）]
# }
func _init(session: RefCounted) -> void:
	# 資源をActionで所有せず、Sessionから最新値を読む。
	_session = session


# {
#   責務: [start: 新鮮なSessionと一致する独立情報を一度だけ準備する]
#   処理: [
#     1: 初期化時点と入力を検証する
#     2: Sessionとの一致後だけ情報を保持する
#   ]
#   引数: [
#     teams: 再構築済み両陣営（Variant）
#     skills: 正規スキル一覧（Variant）
#   ]
#   戻り値: [result: 初期化結果（Dictionary）]
# }
func start(teams: Variant, skills: Variant) -> Dictionary:
	# 定義差替えや減った資源の初期化を拒否する。
	if not _context.is_empty():
		return _reject("already_initialized")
	if _session.snapshot()["phase"] != "between_rounds":
		return _reject("session_not_fresh")
	var checked := Context.prepare(teams, skills)
	if not checked["ok"]:
		return checked
	if checked["snapshots"] != _session.snapshot()["teams"]:
		return _reject("physical_context_mismatch")
	_context = checked["context"]
	return {"ok": true, "scope": "explicit_physical_skill_only"}


# {
#   責務: [resolve: 単体物理行動を一度だけSessionへ適用する]
#   処理: [
#     1: 非破壊で要求と最新状態を検証する
#     2: 単一claimを取得し実行不可なら取消する
#     3: MP支払い・HP適用・finishを同期実行する
#   ]
#   引数: [request: ticket・敵対象・スキルID・乱数（Variant）]
#   戻り値: [result: 適用結果とSessionコピーまたは拒否（Dictionary）]
# }
func resolve(request: Variant) -> Dictionary:
	# 不正・MP不足はclaim前に返し、同じofferedで別行動を選べるようにする。
	var checked := _validate(request)
	if not checked["ok"]:
		return checked
	# await・callbackを挟まず、最新検証から適用まで外部変更の入口を作らない。
	var claimed: Dictionary = _session.claim(request["ticket"])
	if not claimed["ok"]:
		return claimed
	if not claimed["can_execute"]:
		return {"ok": true, "executed": false, "reason": claimed["reason"], "session": claimed["session"]}
	var paid: Dictionary = _session.pay_mp(request["ticket"]["actor"], checked["numbers"]["mp_cost"])
	if not paid["ok"]:
		return _reject("action_payment_failed")  # 取得済みticketを再利用しない。
	var applied: Dictionary = _session.take_damage(request["target"], checked["numbers"]["damage"])
	if not applied["ok"]:
		return _reject("action_application_failed")
	var finished: Dictionary = _session.finish(request["ticket"])
	if not finished["ok"]:
		return _reject("action_finish_failed")
	return {"ok": true, "executed": true, "scope": "explicit_physical_skill_only",
		"ticket": request["ticket"].duplicate(true), "target": request["target"].duplicate(true),
		"numbers": checked["numbers"], "spent_mp": paid["spent"], "session": finished["session"]}


# {
#   責務: [_validate: 行動権と資源を消費せず習得・対象・MP・数値を検証する]
#   処理: [
#     1: 厳密要求とofferedを確認する
#     2: 習得・定義・装備と敵対象を確認する
#     3: 最新資源を予測し、取消では乱数妥当性だけを確認する
#   ]
#   引数: [request: plain行動要求（Variant）]
#   戻り値: [result: numbersまたは拒否（Dictionary）]
# }
func _validate(request: Variant) -> Dictionary:
	# 威力・guard・MP・装備・習得の上書きを要求から受け付けない。
	if _context.is_empty():
		return _reject("not_initialized")
	if not request is Dictionary or request.size() != REQUEST_FIELDS.size():
		return _reject("invalid_physical_request")
	for field in REQUEST_FIELDS:
		if not request.has(field):
			return _reject("invalid_physical_request")
	if not Order.valid_key(request["target"]):
		return _reject("invalid_target_key")
	# 最新のofferedを読み、呼出側の過去snapshotを実行許可として使わない。
	var inspected: Dictionary = _session.inspect_ticket(request["ticket"])
	if not inspected["ok"]:
		return inspected
	var actor: Dictionary = request["ticket"]["actor"]
	var target: Dictionary = request["target"]
	var selected := Context.select(_context, actor, request["skill_id"])
	if not selected["ok"]:
		return selected
	if actor["side"] == target["side"]:
		return _reject("target_not_enemy")
	var teams: Dictionary = _session.snapshot()["teams"]
	var defender := _member(teams[target["side"]], target["id"])
	if defender.is_empty():
		return _reject("target_missing")
	# 死亡・逃走・敵なしをMP不足へ置き換えず、Sessionの取消規則へ渡す。
	if not inspected["eligibility"]["can_act"]:
		var valid := Quote.quote_damage(selected["skill"], {"attack": 1, "defense": 0, "target_hp": 1,
			"current_mp": selected["skill"]["mp_cost"], "critical_roll": request["critical_roll"],
			"variance": request["variance"], "power_multiplier": selected["equipment"]["power_multiplier"],
			"fixed_bonus_damage": selected["equipment"]["fixed_bonus_damage"]})
		return valid if not valid["ok"] else {"ok": true}
	if not defender["alive"]:
		return _reject("target_not_alive")
	var attacker := _member(teams[actor["side"]], actor["id"])
	var guarded: Dictionary = _session.guard(target)
	if not guarded["ok"]:
		return guarded
	# 予測が成功した場合だけresolveでclaimする。MP不足はofferedを保持する。
	var numbers := Quote.quote_damage(selected["skill"], {"attack": attacker["stats"]["attack"],
		"defense": defender["stats"]["defense"], "target_hp": defender["hp"], "current_mp": attacker["mp"],
		"guard": guarded["guard"], "critical_roll": request["critical_roll"], "variance": request["variance"],
		"power_multiplier": selected["equipment"]["power_multiplier"],
		"fixed_bonus_damage": selected["equipment"]["fixed_bonus_damage"]})
	return numbers if not numbers["ok"] else {"ok": true, "numbers": numbers}


# {
#   責務: [_member: 最新snapshotから指定IDを取り出す]
#   処理: [1: 参加チームのIDを確認する]
#   引数: [
#     team: 最大4体のチーム（Array）
#     id: 対象ID（String）
#   ]
#   戻り値: [result: 個体または空辞書（Dictionary）]
# }
func _member(team: Array, id: String) -> Dictionary:
	# 保有全個体でなく、最大4体の戦闘参加チームだけを走査する。
	for member: Dictionary in team:
		if member["identity"]["id"] == id:
			return member
	return {}


# {
#   責務: [_reject: 行動未適用を判別可能な理由で返す]
#   処理: [1: plainな失敗結果を作る]
#   引数: [reason: 呼出元が扱う理由（String）]
#   戻り値: [result: ok=falseの辞書（Dictionary）]
# }
func _reject(reason: String) -> Dictionary:
	# 不正要求を通常攻撃フォールバックで成功扱いにしない。
	return {"ok": false, "reason": reason}
