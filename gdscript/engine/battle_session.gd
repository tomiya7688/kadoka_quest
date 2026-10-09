# {
#   責務: [battle_session: 戦闘個体のHP/MP・一回限りの行動予約・ラウンド限定物理防御を所有します。攻撃計算や勝敗判定は行いません]
#   フィールド: [
#     _teams: allies/enemies別に保持する戦闘個体の資源所有者列（Dictionary）
#     _by_id: 陣営sideと個体idから資源所有者を検索する索引（Dictionary）
#     _phase: 戦闘開始前・ラウンド進行中・終端を表す段階（String）
#     _round: 戦闘開始後のラウンド番号（int）
#     _cursor: 確定した行動順内の現在位置（int）
#     _order: 現在ラウンドで固定したside+idの行動順（Array）
#     _pending: 現在提示中または取得済みの行動予約（Dictionary）
#     _guards: side+id別の物理防御倍率。資源snapshotとは別に保持する（Dictionary）
#   ]
# }
extends RefCounted
## 戦闘個体の資源と行動予約を保持し、攻撃計算や勝敗判定は別契約へ分離します。

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
#   責務: [start: 満HP/MP・未逃走の参加者を検証し、資源所有者と初期防御倍率を一度だけ設定します]
#   処理: [
#     1: 参加者と開始資源を検証し、内部へ公開していない資源所有者を構築します
#     2: 全員成功後に資源所有者を保持し、物理防御倍率を1としてラウンド開始待ちへ進みます
#   ]
#   引数: [
#     allies: 味方参加者の六キー数値snapshot列。各個体は満HP/MP・未逃走です（Variant）
#     enemies: 敵参加者の六キー数値snapshot列。各個体は満HP/MP・未逃走です（Variant）
#   ]
#   戻り値: [result: 初期化の成功と独立した状態、またはok=falseと拒否理由（Dictionary）]
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
#   責務: [snapshot: 戦闘段階・ラウンド・行動順・予約・両陣営資源を内部状態と独立した辞書で返します]
#   処理: [1: 戦闘段階・ラウンド・行動順・予約・両陣営資源を内部状態と独立した辞書で返します]
#   引数: []
#   戻り値: [result: 内部状態から独立した戦闘段階・予約・参加者資源の辞書（Dictionary）]
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
#   責務: [take_damage: 指定したside/idの参加個体へダメージ適用を委譲し、実ダメージと現在HPを返します]
#   処理: [1: 指定したside/idの参加個体へダメージ適用を委譲し、実ダメージと現在HPを返します]
#   引数: [
#     key: sideとidで指定する戦闘参加個体（Variant）
#     amount: 非負整数の要求ダメージ量（Variant）
#   ]
#   戻り値: [result: 要求量・実ダメージ・現在HP、または理由付き拒否（Dictionary）]
# }
func take_damage(key: Variant, amount: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].take_damage(amount)


# {
#   責務: [heal: 指定参加個体のHP回復を資源所有者へ委譲します]
#   処理: [1: 初期化とside/idを検証し、combatant_state.gdへ最大HPで止まる回復を依頼します]
#   引数: [
#     key: 回復対象を指定するsideとid（Variant）
#     amount: 非負整数の回復要求量（Variant）
#   ]
#   戻り値: [result: 個体の実回復量と現在HP、または理由付き拒否（Dictionary）]
# }
func heal(key: Variant, amount: Variant) -> Dictionary:
	# 予約・逃走・勝敗を変更せず、HPの数値更新だけを担当個体へ委譲する。
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].heal(amount)


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
#   責務: [pay_mp: 指定したside/idの参加個体へMP支払いを委譲し、不正や不足時は資源を保持します]
#   処理: [1: 指定したside/idの参加個体へMP支払いを委譲し、不正や不足時は資源を保持します]
#   引数: [
#     key: sideとidで指定する戦闘参加個体（Variant）
#     cost: 指定個体が支払う非負整数のMP量（Variant）
#   ]
#   戻り値: [result: 実消費量spent・現在mp、または資源を保持した不足や不正入力の拒否（Dictionary）]
# }
func pay_mp(key: Variant, cost: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].pay_mp(cost)


# {
#   責務: [restore_mp: 指定個体の最大MPまでの数値回復を資源所有者へ委譲し、予約やHPを変更しません]
#   処理: [1: 陣営と個体IDを検証し、combatant_state.gdへMP回復を委譲します]
#   引数: [
#     key: MPを回復する戦闘参加個体のsideとid（Variant）
#     amount: 精度上限以内の非負整数として検証するMP回復要求量（Variant）
#   ]
#   戻り値: [result: 実回復量restored・現在mp、または資源を保持した拒否（Dictionary）]
# }
func restore_mp(key: Variant, amount: Variant) -> Dictionary:
	# 数値回復は行動権を与えず、ラウンドや逃走・勝敗判定を変更しません。
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].restore_mp(amount)


# {
#   責務: [flee: 指定した参加個体をHPとMPを保持した逃走状態へ変更します]
#   処理: [1: 指定した参加個体をHPとMPを保持した逃走状態へ変更します]
#   引数: [key: sideとidで指定する戦闘参加個体（Variant）]
#   戻り値: [result: 逃走更新の結果・現在HP/MP・生存判定、または未初期化の拒否（Dictionary）]
# }
func flee(key: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].flee()


# {
#   責務: [_resolve: Sessionの初期化とside/idの形式・存在を確認し、指定個体への資源操作を許可または拒否します]
#   処理: [1: Sessionの初期化とside/idの形式・存在を確認し、指定個体への資源操作を許可または拒否します]
#   引数: [key: sideとidで指定する戦闘参加個体（Variant）]
#   戻り値: [result: 指定個体の検証成功ok、または未初期化・不正キー・欠落個体のreason（Dictionary）]
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
#   責務: [_check_ticket: 現在の予約と指定ticketのラウンド・位置・行動者が厳密に一致するか検証します]
#   処理: [1: 現在の予約と指定ticketのラウンド・位置・行動者が厳密に一致するか検証します]
#   引数: [ticket: 行動権チケット（Variant）]
#   戻り値: [result: 予約一致の成功ok、または欠落・不正・不一致を示すreason（Dictionary）]
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
#   責務: [_check: 最新資源を順序契約へ渡し、指定行動者の生存・逃走・敵の有無を確認します]
#   処理: [1: 最新資源を順序契約へ渡し、指定行動者の生存・逃走・敵の有無を確認します]
#   引数: [key: 実行可否を調べる行動者の陣営sideと個体id（Dictionary）]
#   戻り値: [result: 行動者の実行可否can_act・友軍friends・敵foes・停止判定stop（Dictionary）]
# }
func _check(key: Dictionary) -> Dictionary:
	var teams := _snapshots()
	return Order.check_actor(key, teams["allies"], teams["enemies"])


# {
#   責務: [_snapshots: 各資源所有者から最新コピーを取得し、両陣営の参加者列を持つ辞書を返します]
#   処理: [1: 初期参加順を保って最新資源をalliesとenemiesの列へ追加します]
#   引数: []
#   戻り値: [result: alliesとenemiesをキーとする最新資源コピー列の辞書（Dictionary）]
# }
func _snapshots() -> Dictionary:
	var teams := {"allies": [], "enemies": []}
	for side in Order.SIDES:
		for state: RefCounted in _teams[side]:
			teams[side].append(state.snapshot())
	return teams


# {
#   責務: [_both_sides_alive: 両陣営それぞれにHPが正で未逃走の参加個体がいるか確認します]
#   処理: [1: 両陣営それぞれにHPが正で未逃走の参加個体がいるか確認します]
#   引数: []
#   戻り値: [result: 両陣営に生存・未逃走の参加個体がいる場合true、それ以外false（bool）]
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
#   責務: [_update_phase: 最新生存とカーソルを確認し、戦闘停止またはラウンド終端へ段階を更新します]
#   処理: [1: 最新生存とカーソルを確認し、戦闘停止またはラウンド終端へ段階を更新します]
#   引数: []
#   戻り値: [result: なし（void）。最新生存とカーソルに応じて戦闘段階を更新します]
# }
func _update_phase() -> void:
	if not _both_sides_alive():
		_end_round("stopped")
	elif _cursor == _order.size():
		_end_round("round_finished")


# {
#   責務: [_end_round: HPとMPを保持し、全個体のラウンド限定防御倍率を1へ戻します]
#   処理: [1: HPとMPを保持し、全個体のラウンド限定防御倍率を1へ戻します]
#   引数: [phase: round_finishedまたはstopped（String）]
#   戻り値: [result: なし（void）。指定段階を設定し、全個体のラウンド限定防御倍率を1へ戻します]
# }
func _end_round(phase: String) -> void:
	_phase = phase
	for side in Order.SIDES:
		for id: String in _guards[side]:
			_guards[side][id] = 1.0


# {
#   責務: [_failure: Sessionを変更せず、ok=falseと指定した拒否理由を返します]
#   処理: [1: Sessionを変更せず、ok=falseと指定した拒否理由を返します]
#   引数: [reason: 理由（String）]
#   戻り値: [result: ok=falseと指定した拒否理由reasonを持つ辞書（Dictionary）]
# }
func _failure(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
