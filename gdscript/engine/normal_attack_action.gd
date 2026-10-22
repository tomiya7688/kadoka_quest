# {
#   責務: [normal_attack_action: Validate -> single claim -> explicit normal-attack HP application -> finish. No RNG/I/O/AI.]
#   フィールド: [
#     _session: セッション（RefCounted）
#     _context: 判断用コンテキスト（Dictionary）
#   ]
# }
extends RefCounted
## Validate -> single claim -> explicit normal-attack HP application -> finish. No RNG/I/O/AI.

const Contract = preload("res://engine/normal_attack_contract.gd")
const Numbers = preload("res://engine/attack_numbers.gd")
const Order = preload("res://engine/turn_order.gd")
const REQUEST_FIELDS := ["ticket", "target", "skill_id", "critical_roll", "variance"]
var _session: RefCounted
var _context: Dictionary = {}


# {
#   責務: [_init: normal・攻撃・actionが利用する初期状態と依存を設定する]
#   処理: [1: normal・攻撃・actionが利用する初期状態と依存を設定する]
#   引数: [session: セッション（RefCounted）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(session: RefCounted) -> void:
	_session = session


# {
#   責務: [start: normal・攻撃・actionを開始する]
#   処理: [1: normal・攻撃・actionを開始する]
#   引数: [
#     teams: 両陣営（Variant）
#     skills: スキル一覧（Variant）
#   ]
#   戻り値: [result: normal・攻撃・actionを開始するための結果（Dictionary）]
# }
func start(teams: Variant, skills: Variant) -> Dictionary:
	if not _context.is_empty():
		return _failure("already_initialized")
	if _session.snapshot()["phase"] != "between_rounds":
		return _failure("session_not_fresh")
	var checked := Contract.prepare(teams, skills)
	if not checked["ok"]:
		return checked
	if checked["snapshots"] != _session.snapshot()["teams"]:
		return _failure("attack_context_mismatch")
	_context = {"skill": checked["skill"].duplicate(true), "equipment": checked["equipment"].duplicate(true)}
	return {"ok": true, "scope": "explicit_normal_attack_only"}


# {
#   責務: [resolve: 最新の対象と数値を検証して単一の通常攻撃をSessionへ適用する]
#   処理: [
#     1: 要求・ticket・最新生存状態・攻撃数値をclaim前に検証する
#     2: 行動権を一度だけ取得し、実行不能なら攻撃せず取消結果を返す
#     3: 対象の実HPを減らしてfinishする。適用失敗時は取得済み行動権を再利用しない
#   ]
#   引数: [request: 要求（Variant）]
#   戻り値: [result: ok/executedと数値・Sessionの写し、またはreason付き拒否結果]
# }
func resolve(request: Variant) -> Dictionary:
	var checked := _validate(request)
	if not checked["ok"]:
		return checked
	# No await/callback between the latest eligibility check, claim, HP update and finish.
	var claimed: Dictionary = _session.claim(request["ticket"])
	if not claimed["ok"]:
		return claimed
	if not claimed["can_execute"]:
		return {"ok": true, "executed": false, "reason": claimed["reason"], "session": claimed["session"]}
	var applied: Dictionary = _session.take_damage(request["target"], checked["numbers"]["damage"])
	if not applied["ok"]:
		return _failure("action_application_failed")  # Claim stays consumed; never retry the attack.
	var finished: Dictionary = _session.finish(request["ticket"])
	if not finished["ok"]:
		return _failure("action_finish_failed")
	return {"ok": true, "executed": true, "scope": "explicit_normal_attack_only",
		"ticket": request["ticket"].duplicate(true), "target": request["target"].duplicate(true),
		"numbers": checked["numbers"], "session": finished["session"]}


# {
#   責務: [_validate: 資源や行動権を変更せず通常攻撃要求の可否と数値を決める]
#   処理: [
#     1: 要求キーとoffered ticketを検証する
#     2: 敵対象の存在と最新生死を確認する
#     3: 信頼済み定義・装備・現在guardと明示乱数から数値を求める。実行不可なら取消用の検証だけ行う
#   ]
#   引数: [request: 要求（Variant）]
#   戻り値: [result: 通常攻撃数値または理由付き拒否。実行許可や資源変更ではない]
# }
func _validate(request: Variant) -> Dictionary:
	if _context.is_empty():
		return _failure("not_initialized")
	if not request is Dictionary or request.size() != REQUEST_FIELDS.size():
		return _failure("invalid_attack_request")
	for field in REQUEST_FIELDS:
		if not request.has(field):
			return _failure("invalid_attack_request")
	if not request["skill_id"] is String or request["skill_id"] != "attack":
		return _failure("unsupported_action")
	if not Order.valid_key(request["target"]):
		return _failure("invalid_target_key")
	var inspected: Dictionary = _session.inspect_ticket(request["ticket"])
	if not inspected["ok"]:
		return inspected
	var actor: Dictionary = request["ticket"]["actor"]
	var target: Dictionary = request["target"]
	if target["side"] == actor["side"]:
		return _failure("target_not_enemy")
	var teams: Dictionary = _session.snapshot()["teams"]
	var defender := _member(teams[target["side"]], target["id"])
	if defender.is_empty():
		return _failure("target_missing")
	var equipment: Dictionary = _context["equipment"][actor["side"]][actor["id"]]
	var skill: Dictionary = _context["skill"]
	if not inspected["eligibility"]["can_act"]:
		var validated := Contract.validate_numbers(skill, equipment, request["critical_roll"], request["variance"])
		if not validated["ok"]:
			return validated
		return {"ok": true}  # Valid request, but claim will skip a dead/fled actor or stop without foes.
	if not defender["alive"]:
		return _failure("target_not_alive")
	var attacker := _member(teams[actor["side"]], actor["id"])
	var guarded: Dictionary = _session.guard(target)
	if not guarded["ok"]:
		return guarded
	var numbers := Numbers.normal_attack({"attack": attacker["stats"]["attack"], "defense": defender["stats"]["defense"],
		"target_hp": defender["hp"], "guard": guarded["guard"], "equipment": equipment, "power": skill["power"],
		"critical_multiplier": skill["critical_multiplier"], "critical_roll": request["critical_roll"], "variance": request["variance"]})
	return numbers if not numbers["ok"] else {"ok": true, "numbers": numbers}


# {
#   責務: [_member: normal・攻撃・actionの個体を求める]
#   処理: [1: normal・攻撃・actionの個体を求める]
#   引数: [
#     team: チーム（Array）
#     id: 識別子（String）
#   ]
#   戻り値: [result: normal・攻撃・actionの個体を求めるための結果（Dictionary）]
# }
func _member(team: Array, id: String) -> Dictionary:
	for member: Dictionary in team:
		if member["identity"]["id"] == id:
			return member
	return {}


# {
#   責務: [_failure: normal・攻撃・actionのfailureを求める]
#   処理: [1: normal・攻撃・actionのfailureを求める]
#   引数: [reason: 理由（String）]
#   戻り値: [result: normal・攻撃・actionのfailureを求めるための結果（Dictionary）]
# }
func _failure(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
