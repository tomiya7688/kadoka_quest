# {
#   責務: [status_physical_skill_preflight: 付与付き物理の開始情報を独立保持し、最新予約/資源/状態の非消費検査を行います]
#   フィールド: [
#     _session: 数値資源・状態・行動予約識別子ticketの所有者（RefCounted）
#     _context: 検証済みの習得/許可装備・状態耐性・定義索引の非公開コピー（Dictionary）
#   ]
# }
extends RefCounted
const Context = preload("res://engine/status_physical_skill_context.gd")
const Order = preload("res://engine/turn_order.gd")
const REQUEST_FIELDS := ["ticket", "target", "skill_id"]
const SCOPE := "status_physical_preflight_only"
var _session: RefCounted
var _context: Dictionary = {}


# {
#   責務: [_init: 非消費検査で読み取る戦闘Sessionの参照を保持します]
#   処理: [1: HPMP/状態/予約の正本を複製せず、Sessionの参照を設定します]
#   引数: [session: 最新の数値資源・状態・予約を所有する戦闘Session（RefCounted）]
#   戻り値: [result: なし（void）。戦闘を開始しません]
# }
func _init(session: RefCounted) -> void:
	# 非消費検査は資源/予約を所有せず、注入された同じSessionから最新値を読み取ります。
	_session = session


# {
#   責務: [start: 初回ラウンド前のSessionと資源/初期状態が一致する場合だけ、付与付き物理の開始情報を保持します]
#   処理: [
#     1: 未設定・初回ラウンド前を確認し、純粋な準備契約へ入力検証を委譲します
#     2: 数値/状態の一致後だけ非公開contextを設定し、失敗時は再試行可能にします
#   ]
#   引数: [
#     teams: 再構築済みの満資源・習得/許可装備・状態耐性を持つ両陣営（Variant）
#     skills: schema_version=1とskills配列を持つ正規/MOD一覧（Variant）
#     initial_statuses: 全参加者の空状態も明示するside/id別状態辞書（Variant）
#   ]
#   戻り値: [result: 非消費検査の設定成功、またはSession/開始情報を変更しない拒否（Dictionary）]
# }
func start(teams: Variant, skills: Variant, initial_statuses: Variant) -> Dictionary:
	# 消費済み資源や次ラウンドから、開始時の習得/定義を差し替える要求を拒否します。
	if not _context.is_empty():
		return _reject("already_initialized")
	var numeric: Dictionary = _session.snapshot()
	if numeric["phase"] != "between_rounds" or numeric["round"] != 0:
		return _reject("session_not_fresh")
	var checked := Context.prepare(teams, skills, initial_statuses)
	if not checked["ok"]:
		return checked
	if checked["snapshots"] != numeric["teams"]:
		return _reject("status_physical_context_mismatch")
	var statuses: Dictionary = _session.statuses()
	if statuses.is_empty():
		return _reject("status_not_configured")
	if checked["initial_statuses"] != statuses["teams"]:
		return _reject("status_physical_status_mismatch")
	# Context.prepareの独立コピーだけを保持し、返却値としてcontextを公開しません。
	_context = checked["context"]
	return {"ok": true, "scope": SCOPE}


# {
#   責務: [inspect: 提示中の予約と習得/敵対象/最新MP・状態を検査し、行動を実行せず独立した読取結果を返します]
#   処理: [
#     1: 三キー要求と最新offered予約を確認し、専用の定義選択へ委譲します
#     2: 敵対象の存在/生存と実行可能者のMPを確認します
#     3: 最新の数値/状態・対象耐性/guardと独立定義を、実行許可ではない検査結果として返します
#   ]
#   引数: [request: ticket・敵target・習得済みskill_idだけを持つ要求。乱数や外部状態は拒否します（Variant）]
#   戻り値: [result: scopeで非消費を明示した検査結果、または予約/資源/状態を保持した拒否（Dictionary）]
# }
func inspect(request: Variant) -> Dictionary:
	# 数値/乱数を含む最終行動要求と区別し、外部の状態・耐性・定義の持ち込みを拒否します。
	if _context.is_empty():
		return _reject("not_initialized")
	if not request is Dictionary or request.size() != REQUEST_FIELDS.size():
		return _reject("invalid_status_physical_preflight_request")
	for field in REQUEST_FIELDS:
		if not request.has(field):
			return _reject("invalid_status_physical_preflight_request")
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
	# 行動不能者の検査をMP不足へ置き換えず、取消自体もこの読取入口では行いません。
	if inspected["eligibility"]["can_act"]:
		if not defender["alive"]:
			return _reject("target_not_alive")
		var cost: Dictionary = _session.mp_cost(actor, selected["skill"]["mp_cost"])
		if not cost["ok"]:
			return cost
		if not cost["affordable"]:
			return _reject("insufficient_mp")
	return _read_current(request, selected, inspected["eligibility"], teams, defender)


# {
#   責務: [_read_current: Sessionの最新状態と開始時の対象耐性を、非消費検査用の独立辞書へまとめます]
#   処理: [1: 状態読取/物理guardをSessionへ委譲し、補正前の数値と検査範囲を明示して返します]
#   引数: [
#     request: 形式検証済みのticket/target/skill_id要求（Dictionary）
#     selected: 独立した専用定義と装備威力補正（Dictionary）
#     eligibility: Sessionが返した現在の生存/逃走/敵存在の検査結果（Dictionary）
#     teams: Sessionの最新数値snapshotコピー（Dictionary）
#     defender: teams内の対象数値コピー（Dictionary）
#   ]
#   戻り値: [result: 非消費検査結果。ダメージ/付与確率や行動完了は返しません（Dictionary）]
# }
func _read_current(request: Dictionary, selected: Dictionary, eligibility: Dictionary, teams: Dictionary, defender: Dictionary) -> Dictionary:
	var actor: Dictionary = request["ticket"]["actor"]
	var target: Dictionary = request["target"]
	var actor_status: Dictionary = _session.status(actor)
	if not actor_status["ok"]:
		return actor_status
	var target_status: Dictionary = _session.status(target)
	if not target_status["ok"]:
		return target_status
	var guarded: Dictionary = _session.guard(target)
	if not guarded["ok"]:
		return guarded
	# 生の能力値を実効能力値や最終予測と誤認させず、状態補正/付与判定は実装済みとしません。
	return {"ok": true, "scope": SCOPE, "ticket": request["ticket"].duplicate(true),
		"eligibility": eligibility, "skill": selected["skill"], "equipment": selected["equipment"],
		"actor_resources": _member(teams[actor["side"]], actor["id"]), "target_resources": defender,
		"actor_status": actor_status["snapshot"], "target_status": target_status["snapshot"],
		"target_status_resistances": _context["members"][target["side"]][target["id"]]["status_resistances"].duplicate(),
		"target_guard": guarded["guard"], "stats_scope": "before_status_modifiers"}


# {
#   責務: [_member: 戦闘参加する最大四体だけから、指定IDの最新数値コピーを取り出します]
#   処理: [1: 参加者列のidentity.idを照合し、該当個体または空辞書を返します]
#   引数: [
#     team: Sessionから読み取った最大四体の参加者列（Array）
#     id: 探す個体ID（String）
#   ]
#   戻り値: [result: 参加者コピーまたは不在を示す空辞書（Dictionary）]
# }
func _member(team: Array, id: String) -> Dictionary:
	# 無制限の保有個体ではなく、当該陣営の最大四体だけを検索します。
	for member: Dictionary in team:
		if member["identity"]["id"] == id:
			return member
	return {}


# {
#   責務: [_reject: 付与付き物理の非消費検査を、部分成功なしの理由付き辞書で拒否します]
#   処理: [1: ok=falseと具体的なreasonを返します]
#   引数: [reason: 開始情報/要求/資源の拒否理由（String）]
#   戻り値: [result: 予約・資源・状態を変更しない拒否（Dictionary）]
# }
func _reject(reason: String) -> Dictionary:
	# 検査の拒否を行動実行や予約消費の成功へ置き換えません。
	return {"ok": false, "reason": reason}
