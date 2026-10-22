# {
#   責務: [physical_skill_action: 習得済み単体物理を最新予約で検証し、予約取得・MP支払い・HP減少・予約完了を同期実行します]
#   フィールド: [
#     _session: 資源とticketの所有者（RefCounted）
#     _context: 開始時に独立コピーした個体別習得/許可装備とID別スキル定義索引（Dictionary）
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
#   処理: [1: HPMPと予約を所有するSessionの参照だけを設定し、資源をActionへ移しません]
#   引数: [session: 戦闘資源とticketの所有者（RefCounted）]
#   戻り値: [result: なし（void）]
# }
func _init(session: RefCounted) -> void:
	# 資源をActionで所有せず、Sessionから最新値を読む。
	_session = session


# {
#   責務: [start: ラウンド間のSessionと満資源snapshotが一致する開始情報だけを、一度だけ保持します]
#   処理: [
#     1: 未設定/ラウンド間を確認し、共用Contextへ満資源・習得・許可装備の検証を委譲します
#     2: 正規化snapshotとSessionの数値が一致した場合だけ、独立した習得/定義索引を保持します
#   ]
#   引数: [
#     teams: 満資源snapshot・skill_ids・許可装備equipmentを持つallies/enemies（Variant）
#     skills: schema_version=1とskills配列を持つ正規/MODスキル一覧（Variant）
#   ]
#   戻り値: [result: 設定成功scope、またはSession/保持情報を変更しない理由付き拒否（Dictionary）]
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
#   引数: [request: ticket/敵target/skill_id/critical_roll/varianceだけを持つ行動要求（Variant）]
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
#     1: 五キー要求と現在提示中の予約ticketが一致することを確認します
#     2: 開始時の習得・定義・許可装備と、指定した敵参加者の存在を確認します
#     3: 行動可能なら最新HPMP/guardの物理結果を予測し、行動不能なら乱数の妥当性だけを確認します
#   ]
#   引数: [request: ticket/target/skill_id/critical_roll/varianceを要求する通常物理の辞書（Variant）]
#   戻り値: [result: 実行前のnumbers、取消の検証成功、または予約/資源を保持した拒否（Dictionary）]
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
#   責務: [_member: Sessionから取得した最新数値snapshot列から、指定した個体IDの辞書を取り出します]
#   処理: [1: 最大四体のidentity.idを照合し、該当個体または不在の空辞書を返します]
#   引数: [
#     team: Sessionから読み取った指定陣営の最大四体の数値コピー列（Array）
#     id: 最新数値を取得する戦闘個体ID（String）
#   ]
#   戻り値: [result: 指定個体の数値コピー、または不在を示す空辞書（Dictionary）]
# }
func _member(team: Array, id: String) -> Dictionary:
	# 保有全個体でなく、最大4体の戦闘参加チームだけを走査する。
	for member: Dictionary in team:
		if member["identity"]["id"] == id:
			return member
	return {}


# {
#   責務: [_reject: 通常物理の要求検証または内部更新の失敗を、理由付き辞書として返します]
#   処理: [1: ok=falseと具体的なreasonを返し、取得済み予約や適用済み資源は巻き戻しません]
#   引数: [reason: 開始/要求/予測または予約取得後の更新を拒否した理由（String）]
#   戻り値: [result: ok=false/reasonの辞書。予約取得前の拒否は資源を消費しません（Dictionary）]
# }
func _reject(reason: String) -> Dictionary:
	# 不正要求を通常攻撃フォールバックで成功扱いにしない。
	return {"ok": false, "reason": reason}
