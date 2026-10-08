# {
#   責務: [heal_skill_action: 最新の行動予約・習得・資源を確認し、生存する味方1体のHP回復とMP消費を一度だけ適用します]
#   フィールド: [
#     _session: HP・MPと行動予約の更新を委譲する戦闘資源の所有者（RefCounted）
#     _context: 開始時の習得・許可装備・定義を保持する独立辞書（Dictionary）
#   ]
# }
extends RefCounted
const Context = preload("res://engine/heal_skill_context.gd")
const Quote = preload("res://engine/heal_skill_contract.gd")
const Order = preload("res://engine/turn_order.gd")
const REQUEST_FIELDS := ["ticket", "target", "skill_id"]
var _session: RefCounted
var _context: Dictionary = {}

# {
#   責務: [_init: 回復とMP消費・行動予約の更新先となるSessionの参照を保持します]
#   処理: [1: HP・MPを複製せず、資源所有者の参照だけを設定します]
#   引数: [session: 戦闘資源と行動予約を所有するbattle_session.gd（RefCounted）]
#   戻り値: [result: なし（void）。開始情報はstartで設定します]
# }
func _init(session: RefCounted) -> void:
	_session = session

# {
#   責務: [start: 満HP/MPのSessionと一致する習得・許可装備・回復定義を一度だけ設定します]
#   処理: [
#     1: 開始前の段階と再設定でないことを確認します
#     2: 開始情報を検証し、Session資源と一致する独立情報だけを保持します
#   ]
#   引数: [
#     teams: 満HP/MPのsnapshot・skill_ids・equipmentを持つ両陣営（Variant）
#     skills: 正規スキル一覧または同形式のMOD一覧（Variant）
#   ]
#   戻り値: [result: 設定成功、または資源と既存情報を保持した理由付き拒否（Dictionary）]
# }
func start(teams: Variant, skills: Variant) -> Dictionary:
	# 開始後の習得や定義の差替えを拒否し、行動要求の上書き情報も受け取りません。
	if not _context.is_empty():
		return _reject("already_initialized")
	if _session.snapshot()["phase"] != "between_rounds":
		return _reject("session_not_fresh")
	var checked := Context.prepare(teams, skills)
	if not checked["ok"]:
		return checked
	if checked["snapshots"] != _session.snapshot()["teams"]:
		return _reject("heal_context_mismatch")
	_context = checked["context"]
	return {"ok": true, "scope": "explicit_heal_skill_only"}

# {
#   責務: [resolve: 検証済みの単体HP回復について予約取得・MP消費・HP適用・予約完了を同期実行します]
#   処理: [
#     1: 予約取得前に要求と最新資源を検証し、行動不能ならSessionへ取消を委譲します
#     2: 取得した予約のMPを払い、最大HPで止まる回復をSessionへ委譲します
#     3: 予約を完了し、実回復量と所有資源から独立した結果を返します
#   ]
#   引数: [request: ticket・味方target・skill_idだけを持つ要求。targetは本人でも指定できます（Variant）]
#   戻り値: [result: 実消費MP・実回復HPとSessionコピー、行動取消、または理由付き拒否（Dictionary）]
# }
func resolve(request: Variant) -> Dictionary:
	# MP不足・不正要求では予約を取得せず、同じ予約による別行動を可能にします。
	var checked := _validate(request)
	if not checked["ok"]:
		return checked
	# 検証からfinishまでawait・callbackを挟まず、外部更新による部分適用を許しません。
	var claimed: Dictionary = _session.claim(request["ticket"])
	if not claimed["ok"]:
		return claimed
	if not claimed["can_execute"]:
		return {"ok": true, "executed": false, "reason": claimed["reason"], "session": claimed["session"]}
	var numbers: Dictionary = checked["numbers"]
	# 満HPの味方への回復でも、Python正本と同じくMP支払いを省略しません。
	var paid: Dictionary = _session.pay_mp(request["ticket"]["actor"], numbers["mp_cost"])
	if not paid["ok"]:
		return _reject("action_payment_failed")
	var applied: Dictionary = _session.heal(request["target"], numbers["heal_amount"])
	if not applied["ok"]:
		return _reject("action_application_failed")
	var finished: Dictionary = _session.finish(request["ticket"])
	if not finished["ok"]:
		return _reject("action_finish_failed")
	return {"ok": true, "executed": true, "scope": "explicit_heal_skill_only",
		"ticket": request["ticket"].duplicate(true), "target": request["target"].duplicate(true),
		"numbers": numbers, "spent_mp": paid["spent"], "healed": applied["healed"], "session": finished["session"]}

# {
#   責務: [_validate: 明示した最新予約と回復対象を検証し、現在のHP/MPから回復を予測します]
#   処理: [
#     1: 厳密な3キー要求と最新offered予約・習得済み定義を確認します
#     2: 同陣営の対象と行動者の最新実行可否を確認します
#     3: 行動可能な場合だけ生存対象のHPと行動者MPを回復予測へ渡します
#   ]
#   引数: [request: ticket・target・skill_idを持つ明示回復要求（Variant）]
#   戻り値: [result: 予測numbers、資源を使わない行動取消候補、または理由付き拒否（Dictionary）]
# }
func _validate(request: Variant) -> Dictionary:
	# 回復率・最大HP・現在MP・揺らぎなどを要求側から上書きさせません。
	if _context.is_empty():
		return _reject("not_initialized")
	if not request is Dictionary or request.size() != REQUEST_FIELDS.size():
		return _reject("invalid_heal_request")
	for field in REQUEST_FIELDS:
		if not request.has(field):
			return _reject("invalid_heal_request")
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
	if actor["side"] != target["side"]:
		return _reject("target_not_friend")
	var teams: Dictionary = _session.snapshot()["teams"]
	var recipient := _member(teams[target["side"]], target["id"])
	if recipient.is_empty():
		return _reject("target_missing")
	# 行動者の死亡・逃走・敵なしはMP不足に置き換えず、予約取消の条件として扱います。
	if not inspected["eligibility"]["can_act"]:
		return {"ok": true}
	if not recipient["alive"]:
		return _reject("target_not_alive")
	var caster := _member(teams[actor["side"]], actor["id"])
	# 回復は対象の最大HPだけを使い、術者の魔力・装備攻撃補正・防御倍率・耐性を使いません。
	var numbers := Quote.quote_heal(selected["skill"], {"current_mp": caster["mp"],
		"target_hp": recipient["hp"], "target_max_hp": recipient["stats"]["hp"]})
	return numbers if not numbers["ok"] else {"ok": true, "numbers": numbers}

# {
#   責務: [_member: 最大4体の参加チームから指定IDの最新戦闘資源を取り出します]
#   処理: [1: 各個体のIDを照合し、一致する資源を返します]
#   引数: [
#     team: 最新Sessionコピーの片陣営の参加者列（Array）
#     id: 同じ陣営内で検索する個体ID（String）
#   ]
#   戻り値: [result: 一致する個体資源、または対象がない場合の空辞書（Dictionary）]
# }
func _member(team: Array, id: String) -> Dictionary:
	for member: Dictionary in team:
		if member["identity"]["id"] == id:
			return member
	return {}

# {
#   責務: [_reject: 回復行動の失敗を、成功と区別できる理由付き辞書へ変換します]
#   処理: [1: ok=falseと拒否理由を返します]
#   引数: [reason: 開始情報・要求・内部適用を拒否した具体的理由（String）]
#   戻り値: [result: ok=falseとreasonを持つ辞書（Dictionary）]
# }
func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
