# {
#   責務: [magic_skill_action: 最新の行動予約と資源を検証し、単体魔法のMP消費とHP変化を一度だけ適用します]
#   フィールド: [
#     _session: 戦闘資源と行動予約を所有するSession（RefCounted）
#     _context: 開始時の習得・装備・耐性・定義の独立情報（Dictionary）
#   ]
# }
extends RefCounted
const Context = preload("res://engine/magic_skill_context.gd")
const Quote = preload("res://engine/magic_skill_contract.gd")
const Order = preload("res://engine/turn_order.gd")
const Numbers = preload("res://engine/stat_numbers.gd")
const REQUEST_FIELDS := ["ticket", "target", "skill_id", "variance"]
var _session: RefCounted
var _context: Dictionary = {}

# {
#   責務: [_init: HP・MP・行動予約の更新先となるSessionを保持します]
#   処理: [1: 資源を複製せず、更新先の参照を設定します]
#   引数: [session: 戦闘資源と行動予約の所有者（RefCounted）]
#   戻り値: [result: なし（void）]
# }
func _init(session: RefCounted) -> void:
	_session = session

# {
#   責務: [start: 新鮮なSessionと一致する魔法用の開始情報を一度だけ設定します]
#   処理: [1: 初期化時点・開始情報・資源の一致を確認して独立情報を保持します]
#   引数: [
#     teams: 戦闘資源・習得・許可装備・耐性を持つ両陣営（Variant）
#     skills: 正規スキル一覧（Variant）
#   ]
#   戻り値: [result: 設定成功または理由付き拒否（Dictionary）]
# }
func start(teams: Variant, skills: Variant) -> Dictionary:
	# 消費済み資源や開始後の定義差替えは受け付けない。
	if not _context.is_empty():
		return _reject("already_initialized")
	if _session.snapshot()["phase"] != "between_rounds":
		return _reject("session_not_fresh")
	var checked := Context.prepare(teams, skills)
	if not checked["ok"]:
		return checked
	if checked["snapshots"] != _session.snapshot()["teams"]:
		return _reject("magic_context_mismatch")
	_context = checked["context"]
	return {"ok": true, "scope": "explicit_magic_skill_only"}

# {
#   責務: [resolve: 検証済み単体魔法のMP支払い・ダメージまたは吸収回復・予約完了を同期実行します]
#   処理: [
#     1: 最新状態と要求を資源更新なしで検証します
#     2: 予約を一度だけ取得し、行動不可なら資源を消費せず取り消します
#     3: MPとHPを更新して予約を完了します
#   ]
#   引数: [request: ticket・敵target・skill_id・varianceの4キーを持つ要求（Variant）]
#   戻り値: [result: 実行結果とSessionコピー、または理由付き拒否（Dictionary）]
# }
func resolve(request: Variant) -> Dictionary:
	# 不正要求やMP不足は予約取得前に返し、同じ予約で別行動を選択できるようにする。
	var checked := _validate(request)
	if not checked["ok"]:
		return checked
	# 検証からfinishまでawaitやcallbackを挟まず、途中の外部更新を許さない。
	var claimed: Dictionary = _session.claim(request["ticket"])
	if not claimed["ok"]:
		return claimed
	if not claimed["can_execute"]:
		return {"ok": true, "executed": false, "reason": claimed["reason"], "session": claimed["session"]}
	var numbers: Dictionary = checked["numbers"]
	var paid: Dictionary = _session.pay_mp(request["ticket"]["actor"], numbers["mp_cost"])
	if not paid["ok"]:
		return _reject("action_payment_failed")
	var applied: Dictionary
	if numbers["resistance_kind"] == "absorb":
		applied = _session.heal(request["target"], numbers["recovery"])
	else:
		applied = _session.take_damage(request["target"], numbers["damage"])
	if not applied["ok"]:
		return _reject("action_application_failed")
	var finished: Dictionary = _session.finish(request["ticket"])
	if not finished["ok"]:
		return _reject("action_finish_failed")
	return {"ok": true, "executed": true, "scope": "explicit_magic_skill_only",
		"ticket": request["ticket"].duplicate(true), "target": request["target"].duplicate(true),
		"numbers": numbers, "spent_mp": paid["spent"], "session": finished["session"]}

# {
#   責務: [_validate: 最新予約・習得・敵対象・現在MPとHPを確認し、魔法の適用結果を予測します]
#   処理: [
#     1: 厳密な要求と最新offered予約を検証します
#     2: 習得済み定義・敵対象・揺らぎを確認します
#     3: 行動可能な場合だけ最新資源で魔法結果を予測します
#   ]
#   引数: [request: 明示された魔法行動要求（Variant）]
#   戻り値: [result: 予測numbersまたは理由付き拒否（Dictionary）]
# }
func _validate(request: Variant) -> Dictionary:
	# 会心値・威力・MP・耐性・guardの要求側上書きを拒否する。
	if _context.is_empty():
		return _reject("not_initialized")
	if not request is Dictionary or request.size() != REQUEST_FIELDS.size():
		return _reject("invalid_magic_request")
	for field in REQUEST_FIELDS:
		if not request.has(field):
			return _reject("invalid_magic_request")
	if not Order.valid_key(request["target"]):
		return _reject("invalid_target_key")
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
	var variance := Numbers.float_value(request["variance"])
	if not variance["ok"] or variance["value"] < 0.92 or variance["value"] > 1.08:
		return _reject("invalid_variance")
	# 死亡・逃走・敵なしはMP不足に置き換えず、Sessionの予約取消へ渡す。
	if not inspected["eligibility"]["can_act"]:
		return {"ok": true}
	if not defender["alive"]:
		return _reject("target_not_alive")
	var attacker := _member(teams[actor["side"]], actor["id"])
	# guardを渡さないため、基本ぼうぎょは魔法を軽減しない。対象は最新HPで計算する。
	var numbers := Quote.quote_damage(selected["skill"], {"magic": attacker["stats"]["magic"],
		"target_hp": defender["hp"], "target_max_hp": defender["stats"]["hp"], "current_mp": attacker["mp"],
		"target_resistances": _context["members"][target["side"]][target["id"]]["resistances"],
		"variance": request["variance"], "fixed_bonus_damage": selected["fixed_bonus_damage"]})
	return numbers if not numbers["ok"] else {"ok": true, "numbers": numbers}

# {
#   責務: [_member: 最大4体の参加チームから指定IDの最新戦闘資源を取り出します]
#   処理: [1: 参加個体のIDを照合し、一致した資源または空辞書を返します]
#   引数: [
#     team: 最新snapshotの参加チーム（Array）
#     id: 検索する個体ID（String）
#   ]
#   戻り値: [result: 一致した個体の資源または空辞書（Dictionary）]
# }
func _member(team: Array, id: String) -> Dictionary:
	for member: Dictionary in team:
		if member["identity"]["id"] == id:
			return member
	return {}

# {
#   責務: [_reject: 魔法を適用していないことが分かる失敗結果を返します]
#   処理: [1: ok=falseと呼出元が指定した理由を返します]
#   引数: [reason: 要求・開始情報・適用手順の拒否理由（String）]
#   戻り値: [result: 理由付き拒否結果（Dictionary）]
# }
func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
