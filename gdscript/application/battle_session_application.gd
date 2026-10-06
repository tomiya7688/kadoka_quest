# {
#   責務: [battle_session_application: Route read-only battle preparation and explicit actions; no calculations, AI or persistence.]
#   フィールド: [
#     _preparation: preparation（RefCounted）
#     _repository: データ取得先（RefCounted）
#     _session: セッション（RefCounted）
#     _attack: 攻撃（RefCounted）
#     _defend: 基本ぼうぎょの純粋行動解決（RefCounted）
#   ]
# }
extends RefCounted
## Route read-only battle preparation and explicit actions; no calculations, AI or persistence.

const Preparation = preload("res://application/turn_preparation.gd")
const Session = preload("res://engine/battle_session.gd")
const Attack = preload("res://engine/normal_attack_action.gd")
const Defend = preload("res://engine/basic_defend_action.gd")
var _preparation: RefCounted
var _repository: RefCounted
var _session: RefCounted = Session.new()
var _attack: RefCounted
var _defend: RefCounted


# {
#   責務: [_init: 戦闘・セッション・applicationが利用する初期状態と依存を設定する]
#   処理: [1: 戦闘・セッション・applicationが利用する初期状態と依存を設定する]
#   引数: [repository: データ取得先（RefCounted）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(repository: RefCounted) -> void:
	_repository = repository
	_preparation = Preparation.new(repository)


# {
#   責務: [start: 戦闘・セッション・applicationを開始する]
#   処理: [
#     1: read-only準備から新規Sessionを構築する
#     2: 正規skillsで攻撃と基本防御を設定しbegin_roundへ委譲する
#     3: 全成功後だけ内部所有者を切り替える
#   ]
#   引数: [
#     allies: 味方（Variant）
#     enemies: 敵（Variant）
#     shuffle_order: 並べ替え・順序（Variant）
#   ]
#   戻り値: [result: 戦闘・セッション・applicationを開始するための結果（Dictionary）]
# }
func start(allies: Variant, enemies: Variant, shuffle_order: Variant) -> Dictionary:
	if _session.snapshot()["phase"] != "not_started":
		return {"ok": false, "reason": "already_initialized"}
	var prepared: Dictionary = _preparation.prepare(allies, enemies, shuffle_order)
	if not prepared["ok"]:
		return prepared
	var candidate = Session.new()
	var started: Dictionary = candidate.start(_snapshots(prepared["teams"]["allies"]), _snapshots(prepared["teams"]["enemies"]))
	if not started["ok"]:
		return started
	var skills: Dictionary = _repository.load_skills()
	if not skills["ok"]:
		return skills
	var attack = Attack.new(candidate)
	var configured: Dictionary = attack.start(prepared["teams"], skills["value"])
	if not configured["ok"]:
		return configured
	var defend = Defend.new(candidate)
	var guarded: Dictionary = defend.start(skills["value"])
	if not guarded["ok"]:
		return guarded
	var planned: Dictionary = candidate.begin_round(shuffle_order)
	if not planned["ok"]:
		return planned
	_session = candidate
	_attack = attack
	_defend = defend
	return {"ok": true, "preparation": prepared, "session": snapshot()}


# {
#   責務: [begin_round: ラウンドを開始する]
#   処理: [1: ラウンドを開始する]
#   引数: [shuffle_order: 並べ替え・順序（Variant）]
#   戻り値: [result: ラウンドを開始するための結果（Dictionary）]
# }
func begin_round(shuffle_order: Variant) -> Dictionary:
	return _session.begin_round(shuffle_order)


# {
#   責務: [next_actor: 行動個体を次の値を求める]
#   処理: [1: 行動個体を次の値を求める]
#   引数: []
#   戻り値: [result: 行動個体を次の値を求めるための結果（Dictionary）]
# }
func next_actor() -> Dictionary:
	return _session.next_actor()


# {
#   責務: [resolve_normal_attack: normal・攻撃を解決する]
#   処理: [1: normal・攻撃を解決する]
#   引数: [request: 要求（Variant）]
#   戻り値: [result: normal・攻撃を解決するための結果（Dictionary）]
# }
func resolve_normal_attack(request: Variant) -> Dictionary:
	return {"ok": false, "reason": "not_initialized"} if _attack == null else _attack.resolve(request)


# {
#   責務: [resolve_basic_defend: 明示基本ぼうぎょを純粋行動解決へ委譲する]
#   処理: [1: 初期化済みActionへ要求を渡す]
#   引数: [request: ticketとskill_id=defendのplain要求（Variant）]
#   戻り値: [result: Actionの結果または未初期化失敗（Dictionary）]
# }
func resolve_basic_defend(request: Variant) -> Dictionary:
	return {"ok": false, "reason": "not_initialized"} if _defend == null else _defend.resolve(request)


# {
#   責務: [effects: Session所有の倍率を別のplain契約として読む]
#   処理: [1: guardコピー取得をSessionへ委譲する]
#   引数: []
#   戻り値: [result: basic_guard_only効果コピー（Dictionary）]
# }
func effects() -> Dictionary:
	return _session.effects()


# {
#   責務: [snapshot: 戦闘・セッション・applicationを状態を複製する]
#   処理: [1: 戦闘・セッション・applicationを状態を複製する]
#   引数: []
#   戻り値: [result: 戦闘・セッション・applicationを状態を複製するための結果（Dictionary）]
# }
func snapshot() -> Dictionary:
	return _session.snapshot()


# {
#   責務: [_snapshots: 戦闘・セッション・applicationのsnapshotsを求める]
#   処理: [1: 戦闘・セッション・applicationのsnapshotsを求める]
#   引数: [members: 個体一覧（Array）]
#   戻り値: [result: 戦闘・セッション・applicationのsnapshotsを求めるための結果（Array）]
# }
func _snapshots(members: Array) -> Array:
	var snapshots: Array = []
	for member: Dictionary in members:
		snapshots.append(member["snapshot"])
	return snapshots
