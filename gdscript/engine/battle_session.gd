# {
#   責務: [battle_session: 資源・単一カーソルとラウンド限定guardを所有する。攻撃計算や勝敗は扱わない]
#   フィールド: [
#     _teams: 両陣営（Dictionary）
#     _by_id: by・識別子（Dictionary）
#     _phase: 進行段階
#     _round: ラウンド
#     _cursor: カーソル
#     _order: 順序（Array）
#     _pending: 保留中の行動（Dictionary）
#     _guards: side+id別の物理防御倍率。資源snapshotとは別に保持する（Dictionary）
#   ]
# }
extends RefCounted
## Own resources, a single-use cursor and round-local guard; no damage calculation or outcomes.

const State = preload("res://engine/combatant_state.gd")
const Order = preload("res://engine/turn_order.gd")
const StatNumbers = preload("res://engine/stat_numbers.gd")
var _teams: Dictionary = {"allies": [], "enemies": []}
var _by_id: Dictionary = {"allies": {}, "enemies": {}}
var _phase := "not_started"
var _round := 0
var _cursor := 0
var _order: Array = []
var _pending: Dictionary = {}
var _guards: Dictionary = {"allies": {}, "enemies": {}}


# {
#   責務: [start: 戦闘・セッションを開始する]
#   処理: [
#     1: 両陣営のfresh snapshotを検証し未公開のStateを構築する
#     2: 全成功後にStateを所有し各guardを1にする
#   ]
#   引数: [
#     allies: 味方（Variant）
#     enemies: 敵（Variant）
#   ]
#   戻り値: [result: 戦闘・セッションを開始するための結果（Dictionary）]
# }
func start(allies: Variant, enemies: Variant) -> Dictionary:
	if _phase != "not_started":
		return _failure("already_initialized")
	var checked := Order.participants(allies, enemies)
	if not checked["ok"]:
		return checked
	var teams := {"allies": [], "enemies": []}
	var by_id := {"allies": {}, "enemies": {}}
	for side in Order.SIDES:
		var members: Array = allies if side == "allies" else enemies
		for index in members.size():
			var member: Dictionary = members[index]
			if member["hp"] != member["stats"]["hp"] or member["mp"] != member["stats"]["mp"] or member["fled"]:
				return {"ok": false, "reason": "fresh_start_required", "side": side, "index": index}
			var state = State.new()
			var initialized: Dictionary = state.start(member["identity"], member["stats"])
			if not initialized["ok"]:
				return initialized
			teams[side].append(state)
			by_id[side][member["identity"]["id"]] = state
	_teams = teams
	_by_id = by_id
	for side in Order.SIDES:
		for id: String in by_id[side]:
			_guards[side][id] = 1.0
	_phase = "between_rounds"
	return {"ok": true, "session": snapshot()}


# {
#   責務: [snapshot: 戦闘・セッションを状態を複製する]
#   処理: [1: 戦闘・セッションを状態を複製する]
#   引数: []
#   戻り値: [result: 戦闘・セッションを状態を複製するための結果（Dictionary）]
# }
func snapshot() -> Dictionary:
	return {"phase": _phase, "round": _round, "cursor": _cursor, "order": _order.duplicate(true),
		"pending": null if _pending.is_empty() else _pending.duplicate(true),
		"teams": _snapshots(), "scope": "base_battle_cursor"}


# {
#   責務: [begin_round: 資源を保持したまま明示shuffleに基づくラウンドの順序を固定する]
#   処理: [
#     1: 開始可能なphaseと参加者/順序の契約を検証する
#     2: 新しいroundとcursorを設定する。敵なし停止は終端処理へ委譲してguardを解除する
#   ]
#   引数: [shuffle_order: 陣営sideと個体idで表す全参加者の並べ替え候補列。敏捷性が同じ参加者の順を決めます（Variant）]
#   戻り値: [result: plan/session/stopまたは理由付き拒否。勝敗処理ではない]
# }
func begin_round(shuffle_order: Variant) -> Dictionary:
	if _phase == "not_started":
		return _failure("not_initialized")
	if _phase not in ["between_rounds", "round_finished"]:
		return _failure("round_not_available")
	var teams := _snapshots()
	var planned := Order.plan(teams["allies"], teams["enemies"], shuffle_order)
	if not planned["ok"]:
		return planned
	_round += 1
	_order = planned["order"].duplicate(true)
	_cursor = 0
	_phase = "round_active"
	if not _both_sides_alive():
		_end_round("stopped")
	return {"ok": true, "plan": planned, "session": snapshot(), "stop": _phase == "stopped"}


# {
#   責務: [next_actor: 死亡/逃走候補を飛ばして未実行のofferedを予約する]
#   処理: [
#     1: pendingがあれば同じコピーを返し新しい行動権を与えない
#     2: 最新生存を確認して候補を予約する。敵なし/末尾なら全guardを解除する
#   ]
#   引数: []
#   戻り値: [result: offered/pending/終端結果。取得だけではcan_execute=false（Dictionary）]
# }
func next_actor() -> Dictionary:
	if _phase == "not_started":
		return _failure("not_initialized")
	if _phase != "round_active":
		return {"ok": true, "status": _phase, "can_execute": false}
	if not _pending.is_empty():
		return {"ok": true, "status": "pending", "pending": _pending.duplicate(true), "can_execute": false}
	var skipped: Array = []
	while _cursor < _order.size():
		var checked := _check(_order[_cursor])
		if checked["stop"]:
			_end_round("stopped")
			return {"ok": true, "status": _phase, "reason": checked["reason"], "skipped": skipped, "can_execute": false}
		if not checked["can_act"]:
			skipped.append(_order[_cursor].duplicate(true))
			_cursor += 1
			continue
		_pending = {"ticket": {"round": _round, "slot": _cursor, "actor": _order[_cursor].duplicate(true)},
			"stage": "offered"}
		return {"ok": true, "status": "offered", "pending": _pending.duplicate(true),
			"eligibility": checked, "skipped": skipped, "can_execute": false}
	_end_round("round_finished" if _both_sides_alive() else "stopped")
	return {"ok": true, "status": _phase, "skipped": skipped, "can_execute": false}


# {
#   責務: [inspect_ticket: 現在のoffered ticketと最新実行可否を読み取り専用で確認する]
#   処理: [
#     1: 現在のround/slot/actorとの一致を検証する
#     2: 既claimedを拒否し、最新の死亡・逃走・敵生存を照合する
#   ]
#   引数: [ticket: 行動権チケット（Variant）]
#   戻り値: [result: eligibilityまたは拒否理由。行動権は取得しない]
# }
func inspect_ticket(ticket: Variant) -> Dictionary:
	# Read-only validation, never a permission to execute or consume the cursor.
	var checked := _check_ticket(ticket)
	if not checked["ok"]:
		return checked
	if _pending["stage"] != "offered":
		return _failure("already_claimed")
	return {"ok": true, "eligibility": _check(ticket["actor"])}


# {
#   責務: [claim: offered行動権を最新状態と照合し一度だけ取得する]
#   処理: [
#     1: inspect_ticketで現在の行動候補を確認する
#     2: 実行不能なら候補を取消しcursorを進める
#     3: 実行可能ならclaimedへ変更する。HP/MPや攻撃計算は変更しない
#   ]
#   引数: [ticket: 行動権チケット（Variant）]
#   戻り値: [result: can_execute/ticketまたは拒否理由]
# }
func claim(ticket: Variant) -> Dictionary:
	var checked := inspect_ticket(ticket)
	if not checked["ok"]:
		return checked
	var eligibility: Dictionary = checked["eligibility"]
	if not eligibility["can_act"]:
		_pending.clear()
		_cursor += 1
		_update_phase()
		return {"ok": true, "can_execute": false, "reason": eligibility["reason"], "session": snapshot()}
	_pending["stage"] = "claimed"
	return {"ok": true, "can_execute": true, "ticket": ticket.duplicate(true), "eligibility": eligibility}


# {
#   責務: [finish: 現在claimedの行動を一度だけ完了し必要時にguardを解除する]
#   処理: [
#     1: 同じticketがclaimedであることを確認する
#     2: pendingを消費しcursorを進め終端判定へ委譲する
#   ]
#   引数: [ticket: 行動権チケット（Variant）]
#   戻り値: [result: 更新後sessionまたは非破壊的拒否。戦闘の勝敗確定ではない（Dictionary）]
# }
func finish(ticket: Variant) -> Dictionary:
	var checked := _check_ticket(ticket)
	if not checked["ok"]:
		return checked
	if _pending["stage"] != "claimed":
		return _failure("pending_not_claimed")
	_pending.clear()
	_cursor += 1
	_update_phase()
	return {"ok": true, "session": snapshot()}


# {
#   責務: [take_damage: ダメージを反映する]
#   処理: [1: ダメージを反映する]
#   引数: [
#     key: キー（Variant）
#     amount: 量（Variant）
#   ]
#   戻り値: [result: ダメージを反映するための結果（Dictionary）]
# }
func take_damage(key: Variant, amount: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].take_damage(amount)


# {
#   責務: [effects: 資源の6キー契約を変更せずguardの独立plainコピーを返す]
#   処理: [1: 両陣営のside+id倍率を複製する]
#   引数: []
#   戻り値: [result: teamsとbasic_guard_only scope（Dictionary）]
# }
func effects() -> Dictionary:
	return {"teams": _guards.duplicate(true), "scope": "basic_guard_only"}


# {
#   責務: [guard: 指定個体の現在の信頼済み物理防御倍率を読み取る]
#   処理: [1: side+idを検証し所有倍率を返す]
#   引数: [key: 対象のside+id（Variant）]
#   戻り値: [result: ok/guardまたはreason付き失敗（Dictionary）]
# }
func guard(key: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else {"ok": true, "guard": _guards[key["side"]][key["id"]]}


# {
#   責務: [apply_defend: 現在claimedの生存行動者だけのguardを更新する]
#   処理: [
#     1: ticketの一致とclaimedおよび有限倍率を検証する
#     2: 最新行動可否を確認し本人の倍率だけを変更する
#   ]
#   引数: [
#     ticket: 単一行動権のticket（Variant）
#     multiplier: 正規defend定義から検証済みの倍率（Variant）
#   ]
#   戻り値: [result: ok/guardまたは非破壊的な失敗（Dictionary）]
# }
func apply_defend(ticket: Variant, multiplier: Variant) -> Dictionary:
	var checked := _check_ticket(ticket)
	if not checked["ok"]:
		return checked
	if _pending["stage"] != "claimed":
		return _failure("pending_not_claimed")
	var value := StatNumbers.float_value(multiplier)
	if not value["ok"]:
		return _failure("invalid_guard")
	if not _check(ticket["actor"])["can_act"]:
		return _failure("actor_cannot_defend")
	var actor: Dictionary = ticket["actor"]
	_guards[actor["side"]][actor["id"]] = value["value"]
	return {"ok": true, "guard": value["value"]}


# {
#   責務: [mp_cost: 指定した戦闘個体が現在のMPで指定消費量を払えるか確認し、MP自体は変更しません]
#   処理: [1: 陣営と個体IDから戦闘個体を特定し、消費MPの妥当性と支払い可否の確認をcombatant_state.gdの戦闘個体へ委譲します]
#   引数: [
#     key: MPの支払い可否を調べる個体の陣営sideと個体idを含む辞書（Variant）
#     cost: 支払えるか確認する消費MP。combatant_state.gdの戦闘個体が非負整数として検証します（Variant）
#   ]
#   戻り値: [result: 妥当な入力なら消費量cost・支払い可否affordable・現在mp、不正なら拒否理由reasonを含む結果（Dictionary）]
# }
func mp_cost(key: Variant, cost: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].mp_cost(cost)


# {
#   責務: [pay_mp: MPを支払う]
#   処理: [1: MPを支払う]
#   引数: [
#     key: キー（Variant）
#     cost: 消費量（Variant）
#   ]
#   戻り値: [result: MPを支払うための結果（Dictionary）]
# }
func pay_mp(key: Variant, cost: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].pay_mp(cost)


# {
#   責務: [flee: 戦闘・セッションを逃走状態を設定する]
#   処理: [1: 戦闘・セッションを逃走状態を設定する]
#   引数: [key: キー（Variant）]
#   戻り値: [result: 戦闘・セッションを逃走状態を設定するための結果（Dictionary）]
# }
func flee(key: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].flee()


# {
#   責務: [_resolve: 戦闘・セッションを解決する]
#   処理: [1: 戦闘・セッションを解決する]
#   引数: [key: キー（Variant）]
#   戻り値: [result: 戦闘・セッションを解決するための結果（Dictionary）]
# }
func _resolve(key: Variant) -> Dictionary:
	if _phase == "not_started":
		return _failure("not_initialized")
	if not Order.valid_key(key):
		return _failure("invalid_actor_key")
	if not _by_id[key["side"]].has(key["id"]):
		return _failure("actor_missing")
	return {"ok": true}


# {
#   責務: [_check_ticket: 行動権チケットを検査する]
#   処理: [1: 行動権チケットを検査する]
#   引数: [ticket: 行動権チケット（Variant）]
#   戻り値: [result: 行動権チケットを検査するための結果（Dictionary）]
# }
func _check_ticket(ticket: Variant) -> Dictionary:
	if _phase == "not_started":
		return _failure("not_initialized")
	if not ticket is Dictionary or ticket.size() != 3 or not Order.valid_key(ticket.get("actor")):
		return _failure("invalid_ticket")
	for key in ["round", "slot"]:
		var value: Variant = ticket.get(key)
		if not (value is int or value is float) or not is_finite(float(value)) \
			or value < 0 or value > State.MAX_EXACT_INTEGER or float(value) != floorf(float(value)):
			return _failure("invalid_ticket")
	if _pending.is_empty() or ticket != _pending["ticket"]:
		return _failure("ticket_not_pending")
	return {"ok": true}


# {
#   責務: [_check: 戦闘・セッションを検査する]
#   処理: [1: 戦闘・セッションを検査する]
#   引数: [key: キー（Dictionary）]
#   戻り値: [result: 戦闘・セッションを検査するための結果（Dictionary）]
# }
func _check(key: Dictionary) -> Dictionary:
	var teams := _snapshots()
	return Order.check_actor(key, teams["allies"], teams["enemies"])


# {
#   責務: [_snapshots: 戦闘・セッションのsnapshotsを求める]
#   処理: [1: 戦闘・セッションのsnapshotsを求める]
#   引数: []
#   戻り値: [result: 戦闘・セッションのsnapshotsを求めるための結果（Dictionary）]
# }
func _snapshots() -> Dictionary:
	var teams := {"allies": [], "enemies": []}
	for side in Order.SIDES:
		for state: RefCounted in _teams[side]:
			teams[side].append(state.snapshot())
	return teams


# {
#   責務: [_both_sides_alive: 戦闘・セッションのboth・sides・aliveを求める]
#   処理: [1: 戦闘・セッションのboth・sides・aliveを求める]
#   引数: []
#   戻り値: [result: 戦闘・セッションのboth・sides・aliveを求めるための結果（bool）]
# }
func _both_sides_alive() -> bool:
	for side in Order.SIDES:
		var living := false
		for state: RefCounted in _teams[side]:
			living = living or state.alive()
		if not living:
			return false
	return true


# {
#   責務: [_update_phase: 進行段階を更新する]
#   処理: [1: 敵なしまたはカーソル末尾ならguard解除を伴う終端処理へ委譲する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _update_phase() -> void:
	if not _both_sides_alive():
		_end_round("stopped")
	elif _cursor == _order.size():
		_end_round("round_finished")


# {
#   責務: [_end_round: 正常末尾と敵なし停止で全guardだけを解除する]
#   処理: [1: 終端phaseを設定し死亡・逃走を含む全参加者の倍率を1へ戻す]
#   引数: [phase: round_finishedまたはstopped（String）]
#   戻り値: [result: なし（void）。HP/MP/fledは保持する]
# }
func _end_round(phase: String) -> void:
	_phase = phase
	for side in Order.SIDES:
		for id: String in _guards[side]:
			_guards[side][id] = 1.0


# {
#   責務: [_failure: 戦闘・セッションのfailureを求める]
#   処理: [1: 戦闘・セッションのfailureを求める]
#   引数: [reason: 理由（String）]
#   戻り値: [result: 戦闘・セッションのfailureを求めるための結果（Dictionary）]
# }
func _failure(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
