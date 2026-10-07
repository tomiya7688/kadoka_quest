# {
#   責務: [battle_session_application: 保存個体からの戦闘準備と明示された行動要求を担当モジュールへ委譲し、戦闘Sessionと行動処理の参照を保持します]
#   フィールド: [
#     _preparation: 保存個体の戦闘用再構築と行動順計画を行うturn_preparation.gdの準備処理（RefCounted）
#     _repository: 種族・装備・スキルなどの正規データの取得を委譲するリポジトリ（RefCounted）
#     _session: 戦闘中のHP・MP・行動予約・基本防御倍率を所有するbattle_session.gdの戦闘状態（RefCounted）
#     _attack: battle_session.gdの戦闘状態へ通常攻撃の結果を反映するnormal_attack_action.gdの行動処理（RefCounted）
#     _defend: battle_session.gdの戦闘状態へ基本ぼうぎょの倍率を反映するbasic_defend_action.gdの行動処理（RefCounted）
#     _physical: battle_session.gdの戦闘状態へMP付き単体物理スキルの結果を反映するphysical_skill_action.gdの行動処理（RefCounted）
#   ]
# }
extends RefCounted
## battle_session_application.gdの呼び出し処理は、戦闘準備と明示行動を担当モジュールへ委譲し、ダメージ計算・AI選択・保存書き込みを行いません。

const Preparation = preload("res://application/turn_preparation.gd")
const Session = preload("res://engine/battle_session.gd")
const Attack = preload("res://engine/normal_attack_action.gd")
const Defend = preload("res://engine/basic_defend_action.gd")
const Physical = preload("res://engine/physical_skill_action.gd")
var _preparation: RefCounted
var _repository: RefCounted
var _session: RefCounted = Session.new()
var _attack: RefCounted
var _defend: RefCounted
var _physical: RefCounted


# {
#   責務: [_init: 戦闘準備とスキル読込に使うデータ取得先を保持し、turn_preparation.gdの準備処理へ同じ取得先を渡します]
#   処理: [1: データ取得先の参照を保存し、保存個体を戦闘用に再構築するturn_preparation.gdの準備処理を生成します]
#   引数: [repository: 正規の種族・装備・スキル定義を取得するリポジトリ（RefCounted）]
#   戻り値: [result: なし（void）。戦闘準備の依存を設定し、戦闘は開始しません]
# }
func _init(repository: RefCounted) -> void:
	# 戦闘呼び出し処理は、戦闘準備とスキル読込で異なるデータ取得先を使わないように、リポジトリの参照を共用します。
	_repository = repository
	_preparation = Preparation.new(repository)


# {
#   責務: [start: 保存個体から独立した戦闘Sessionと行動処理を構築し、最初のラウンドを開始します]
#   処理: [
#     1: turn_preparation.gdの準備処理で参加個体を再構築し、候補のbattle_session.gdの戦闘状態へ戦闘資源を設定します
#     2: 正規スキル定義で通常攻撃・基本ぼうぎょ・MP付き単体物理の行動処理を設定します
#     3: 最初のラウンドの計画が成功した場合だけ、使用するbattle_session.gdの戦闘状態と行動処理の参照を切り替えます
#   ]
#   引数: [
#     allies: 戦闘へ参加させる味方の保存個体レコード列（Variant）
#     enemies: 戦闘へ参加させる敵の個体レコード列（Variant）
#     shuffle_order: 陣営sideと個体idで表す全参加者の並べ替え候補列。敏捷性が同じ参加者の順を決めます（Variant）
#   ]
#   戻り値: [result: 成功時は準備結果preparationと戦闘状態session、失敗時は理由reasonを含む結果（Dictionary）]
# }
func start(allies: Variant, enemies: Variant, shuffle_order: Variant) -> Dictionary:
	# 戦闘呼び出し処理は、既に開始した戦闘を新しい参加者で二重に初期化する要求を拒否します。
	if _session.snapshot()["phase"] != "not_started":
		return {"ok": false, "reason": "already_initialized"}
	var prepared: Dictionary = _preparation.prepare(allies, enemies, shuffle_order)
	if not prepared["ok"]:
		return prepared
	# 戦闘呼び出し処理は、準備失敗時に使用中の戦闘資源を部分更新しないため、候補のbattle_session.gdの戦闘状態を別に構築します。
	var candidate = Session.new()
	var started: Dictionary = candidate.start(_snapshots(prepared["teams"]["allies"]), _snapshots(prepared["teams"]["enemies"]))
	if not started["ok"]:
		return started
	# 戦闘呼び出し処理は、スキル定義の読込をリポジトリへ委譲し、各スキルの対応範囲の検証を行動処理へ任せます。
	var skills: Dictionary = _repository.load_skills()
	if not skills["ok"]:
		return skills
	# 戦闘呼び出し処理は、各行動処理へ候補のbattle_session.gdの戦闘状態を渡し、HP・MPと行動予約識別子ticketの所有者を共通にします。
	var attack = Attack.new(candidate)
	var configured: Dictionary = attack.start(prepared["teams"], skills["value"])
	if not configured["ok"]:
		return configured
	var defend = Defend.new(candidate)
	var guarded: Dictionary = defend.start(skills["value"])
	if not guarded["ok"]:
		return guarded
	var physical = Physical.new(candidate)
	var equipped: Dictionary = physical.start(prepared["teams"], skills["value"])
	if not equipped["ok"]:
		return equipped
	# 戦闘呼び出し処理は、全行動処理の設定と最初のラウンド計画が成功してから、使用する戦闘状態と行動処理を一度に切り替えます。
	var planned: Dictionary = candidate.begin_round(shuffle_order)
	if not planned["ok"]:
		return planned
	_session = candidate
	_attack = attack
	_defend = defend
	_physical = physical
	return {"ok": true, "preparation": prepared, "session": snapshot()}


# {
#   責務: [begin_round: 戦闘資源を保持した次のラウンドの開始をbattle_session.gdの戦闘状態へ委譲します]
#   処理: [1: battle_session.gdの戦闘状態へ参加者の並べ替え候補列を渡し、行動順計画または拒否結果を返します]
#   引数: [shuffle_order: 陣営sideと個体idで表す全参加者の並べ替え候補列。敏捷性が同じ参加者の順を決めます（Variant）]
#   戻り値: [result: battle_session.gdの戦闘状態が返す計画・状態・停止判定、または開始を拒否した理由を含む結果（Dictionary）]
# }
func begin_round(shuffle_order: Variant) -> Dictionary:
	return _session.begin_round(shuffle_order)


# {
#   責務: [next_actor: 次の生存行動者の予約をbattle_session.gdの戦闘状態へ依頼します。予約の取得だけでは行動を実行しません]
#   処理: [1: battle_session.gdの戦闘状態へ行動者の取得を委譲し、予約済みの行動またはラウンド終端を返します]
#   引数: []
#   戻り値: [result: 行動者の予約pendingと状態status、または未初期化の拒否。取得だけではcan_executeはfalseです（Dictionary）]
# }
func next_actor() -> Dictionary:
	return _session.next_actor()


# {
#   責務: [resolve_normal_attack: 明示された通常攻撃要求の検証とHPへの反映をnormal_attack_action.gdの行動処理へ委譲します]
#   処理: [1: 初期化済みのnormal_attack_action.gdの行動処理へ要求を渡し、未初期化なら理由not_initializedを返します]
#   引数: [request: 通常攻撃の行動予約識別子ticket・対象・スキルID・会心判定値・威力の乱数を含む要求（Variant）]
#   戻り値: [result: normal_attack_action.gdの行動処理の実行結果または未初期化の拒否結果（Dictionary）]
# }
func resolve_normal_attack(request: Variant) -> Dictionary:
	return {"ok": false, "reason": "not_initialized"} if _attack == null else _attack.resolve(request)


# {
#   責務: [resolve_basic_defend: 明示された基本ぼうぎょ要求の検証と防御倍率の設定をbasic_defend_action.gdの行動処理へ委譲します]
#   処理: [1: 初期化済みのbasic_defend_action.gdの行動処理へ要求を渡し、未初期化なら理由not_initializedを返します]
#   引数: [request: 行動予約識別子ticketとスキルID skill_id=defendを含む基本ぼうぎょ要求（Variant）]
#   戻り値: [result: basic_defend_action.gdの行動処理の実行結果または未初期化の拒否結果（Dictionary）]
# }
func resolve_basic_defend(request: Variant) -> Dictionary:
	return {"ok": false, "reason": "not_initialized"} if _defend == null else _defend.resolve(request)


# {
#   責務: [effects: battle_session.gdの戦闘状態が保持する基本ぼうぎょの物理防御倍率を、戦闘資源とは別の辞書として取得します]
#   処理: [1: battle_session.gdの戦闘状態へ両陣営の個体別防御倍率のコピー取得を委譲します]
#   引数: []
#   戻り値: [result: 個体別倍率のコピーteamsと、基本防御限定を示すscope=basic_guard_onlyを含む辞書（Dictionary）]
# }
func effects() -> Dictionary:
	return _session.effects()


# {
#   責務: [resolve_physical_skill: 明示されたMP付き単体物理スキル要求の検証・MP消費・HPへの反映をphysical_skill_action.gdの行動処理へ委譲します]
#   処理: [1: 初期化済みのphysical_skill_action.gdの行動処理へ要求を渡し、未初期化なら理由not_initializedを返します]
#   引数: [request: 行動予約識別子ticket・対象target・スキルID skill_id・会心判定値critical_roll・威力の乱数varianceを含む要求（Variant）]
#   戻り値: [result: physical_skill_action.gdの行動処理の実行結果または未初期化の拒否結果（Dictionary）]
# }
func resolve_physical_skill(request: Variant) -> Dictionary:
	# battle_session_application.gdの呼び出し処理ではダメージ計算や行動権判定を重複実装せず、physical_skill_action.gdの行動処理へ委譲します。
	return {"ok": false, "reason": "not_initialized"} if _physical == null else _physical.resolve(request)


# {
#   責務: [snapshot: battle_session.gdの戦闘状態が保持する戦闘状態を、内部状態と独立した辞書として取得します]
#   処理: [1: battle_session.gdの戦闘状態へラウンド・行動順・行動予約・両陣営の戦闘資源のコピー取得を委譲します]
#   引数: []
#   戻り値: [result: 戦闘段階phase・ラウンドround・行動順order・予約pending・参加者teamsなどを含む状態辞書（Dictionary）]
# }
func snapshot() -> Dictionary:
	return _session.snapshot()


# {
#   責務: [_snapshots: 準備済みの参加個体から、battle_session.gdの戦闘状態の初期化に渡す戦闘資源辞書だけを順に取り出します]
#   処理: [1: 各参加個体のsnapshotを列へ追加し、装備や習得スキルの情報を戦闘資源の列へ混在させません]
#   引数: [members: snapshot・装備・習得スキルなどを持つ準備済み参加個体の列（Array）]
#   戻り値: [result: 入力の個体順を保った戦闘資源snapshotの参照列。辞書自体はここでは複製しません（Array）]
# }
func _snapshots(members: Array) -> Array:
	# 参加者の資源抽出処理は、戦闘状態へ渡すHP・MPなどの列と、行動処理へ渡す装備・習得スキル情報を区別します。
	var snapshots: Array = []
	for member: Dictionary in members:
		snapshots.append(member["snapshot"])
	return snapshots
