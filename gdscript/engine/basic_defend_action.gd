# {
#   責務: [basic_defend_action: 基本ぼうぎょ要求を検証し単一claimから本人guard更新とfinishへ進める]
#   フィールド: [
#     _session: 資源とguardを所有する戦闘Session（RefCounted）
#     _guard: 正規定義からコピーした有限倍率（float）
#     _initialized: 一度だけの設定成功状態（bool）
#   ]
# }
extends RefCounted

const Contract = preload("res://engine/basic_defend_contract.gd")
var _session: RefCounted
var _guard := 1.0
var _initialized := false


# {
#   責務: [_init: 既存Sessionへ依存を注入する]
#   処理: [1: Session参照を保持する]
#   引数: [session: 同期行動処理用の所有Session（RefCounted）]
#   戻り値: [result: なし（void）]
# }
func _init(session: RefCounted) -> void:
	_session = session


# {
#   責務: [start: fresh Sessionに対し正規defendを一度だけ設定する]
#   処理: [
#     1: 再設定と途中Sessionを拒否する
#     2: 定義を検証しコピー済み倍率だけを保持する
#   ]
#   引数: [skills: 正規skills文書（Variant）]
#   戻り値: [result: ok/scopeまたはreason付き失敗（Dictionary）]
# }
func start(skills: Variant) -> Dictionary:
	if _initialized:
		return _failure("already_initialized")
	if _session.snapshot()["phase"] != "between_rounds":
		return _failure("session_not_fresh")
	var checked := Contract.prepare(skills)
	if not checked["ok"]:
		return checked
	_guard = checked["guard"]
	_initialized = true
	return {"ok": true, "scope": "explicit_basic_defend_only"}


# {
#   責務: [resolve: 検証済み要求だけを同期claim・guard更新・finishで一度処理する]
#   処理: [
#     1: 要求を検証する。対象指定や倍率上書きは受け付けない
#     2: 最新生死でclaimし取消時は効果を適用しない
#     3: 本人guardのみ変更してfinishする。終端ならSessionが倍率を解除する
#   ]
#   引数: [request: ticketとskill_id=defendだけの要求（Variant）]
#   戻り値: [result: 実行結果/適用倍率/session/effectsまたは非破壊的拒否（Dictionary）]
#   補足: [boundary: await・外部callbackなし。内部適用失敗のclaimを再利用しない]
# }
func resolve(request: Variant) -> Dictionary:
	var checked := _validate(request)
	if not checked["ok"]:
		return checked
	var claimed: Dictionary = _session.claim(request["ticket"])
	if not claimed["ok"]:
		return claimed
	if not claimed["can_execute"]:
		return {"ok": true, "executed": false, "reason": claimed["reason"],
			"session": claimed["session"], "effects": _session.effects()}
	var applied: Dictionary = _session.apply_defend(request["ticket"], _guard)
	if not applied["ok"]:
		return _failure("action_application_failed")
	var finished: Dictionary = _session.finish(request["ticket"])
	if not finished["ok"]:
		return _failure("action_finish_failed")
	return {"ok": true, "executed": true, "scope": "explicit_basic_defend_only",
		"ticket": request["ticket"].duplicate(true), "applied_guard": applied["guard"],
		"session": finished["session"], "effects": _session.effects()}


# {
#   責務: [_validate: 資源・効果・カーソルを変更せず自己防御要求を検証する]
#   処理: [1: 初期化と厳密な2キー要求を確認してoffered ticketを読み取り検証する]
#   引数: [request: 未信頼の行動要求（Variant）]
#   戻り値: [result: inspect結果または非破壊的失敗（Dictionary）]
# }
func _validate(request: Variant) -> Dictionary:
	if not _initialized:
		return _failure("not_initialized")
	if not request is Dictionary or request.size() != 2 or not request.has("ticket") or not request.has("skill_id"):
		return _failure("invalid_defend_request")
	if not request["skill_id"] is String or request["skill_id"] != "defend":
		return _failure("unsupported_action")
	return _session.inspect_ticket(request["ticket"])


# {
#   責務: [_failure: 行動失敗をplain辞書で返す]
#   処理: [1: 拒否理由を返す]
#   引数: [reason: 拒否理由（String）]
#   戻り値: [result: ok=falseとreason（Dictionary）]
# }
func _failure(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
