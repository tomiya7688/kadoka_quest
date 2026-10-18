# {
#   責務: [battle_session_application: 保存個体からの戦闘準備と明示された行動要求を担当モジュールへ委譲し、戦闘Sessionと行動処理の参照を保持します]
#   フィールド: [
#     _preparation: 保存個体の戦闘用再構築と行動順計画を行うturn_preparation.gdの準備処理（RefCounted）
#     _repository: 種族・装備・スキルなどの正規データの取得を委譲するリポジトリ（RefCounted）
#     _session: 戦闘中のHP/MP・行動予約・物理防御と専用開始の状態を所有するbattle_session.gd（RefCounted）
#     _attack: battle_session.gdの戦闘状態へ通常攻撃の結果を反映するnormal_attack_action.gdの行動処理（RefCounted）
#     _defend: battle_session.gdの戦闘状態へ基本ぼうぎょの倍率を反映するbasic_defend_action.gdの行動処理（RefCounted）
#     _physical: battle_session.gdの戦闘状態へMP付き単体物理スキルの結果を反映するphysical_skill_action.gdの行動処理（RefCounted）
#     _magic: 戦闘状態へMP付き単体魔法の結果を反映するmagic_skill_action.gdの行動処理（RefCounted）
#     _self_magic: 敵への魔法効果と術者のHP代償を反映する、自傷専用設定のmagic_skill_action.gd（RefCounted）
#     _drain_magic: 敵HP効果・敵MP喪失・術者MP回復を反映する、吸MP専用設定のmagic_skill_action.gd（RefCounted）
#     _heal: 生存する味方1体のHP回復と術者MP消費を同じSessionへ反映するheal_skill_action.gd（RefCounted）
#     _status_physical: 状態付き開始時だけ設定し、付与付き物理の実行と非消費検査を委譲する行動処理（RefCounted）
#     _cure_heal: 専用開始時だけ構築する、HP回復/MP消費と一件治療の共用行動処理（RefCounted）
#   ]
# }
extends RefCounted
## battle_session_application.gdの呼び出し処理は、戦闘準備と明示行動を担当モジュールへ委譲し、ダメージ計算・AI選択・保存書き込みを行いません。

const Preparation = preload("res://application/turn_preparation.gd")
const Session = preload("res://engine/battle_session.gd")
const Attack = preload("res://engine/normal_attack_action.gd")
const Defend = preload("res://engine/basic_defend_action.gd")
const Physical = preload("res://engine/physical_skill_action.gd")
const Magic = preload("res://engine/magic_skill_action.gd")
const StatusPhysical = preload("res://engine/status_physical_skill_action.gd")
const Heal = preload("res://engine/heal_skill_action.gd")
var _preparation: RefCounted
var _repository: RefCounted
var _session: RefCounted = Session.new()
var _attack: RefCounted
var _defend: RefCounted
var _physical: RefCounted
var _magic: RefCounted
var _self_magic: RefCounted
var _drain_magic: RefCounted
var _heal: RefCounted
var _cure_heal: RefCounted
var _status_physical: RefCounted


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
#     2: 正規スキル定義で通常攻撃・基本ぼうぎょ・MP付き物理・通常/自傷/吸MP魔法・単体HP回復の行動処理を設定します
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
	return _start(allies, enemies, shuffle_order, null, false)


# {
#   責務: [start_with_statuses: 保存個体の再構築と明示初期状態付きSession・治療付き回復/付与付き物理行動の構築を調停します]
#   処理: [1: 全参加者の明示初期状態と保存個体・明示順を共用開始調停へ渡します]
#   引数: [
#     allies: 味方の保存個体レコード列（Variant）
#     enemies: 敵の保存個体レコード列（Variant）
#     shuffle_order: 生存参加者のside/id別明示順（Variant）
#     initial_statuses: 全参加者について空状態も明示するside/id別状態辞書（Variant）
#   ]
#   戻り値: [result: 全成功後の準備/数値Sessionコピー、または未開始を保持した拒否（Dictionary）]
# }
func start_with_statuses(allies: Variant, enemies: Variant, shuffle_order: Variant, initial_statuses: Variant) -> Dictionary:
	return _start(allies, enemies, shuffle_order, initial_statuses, true)


# {
#   責務: [_start: 未公開の候補Sessionと全行動処理を構築し、全成功後だけ使用中の参照を切り替えます]
#   処理: [1: 再構築・区分別Session開始・各行動設定・初回ラウンドを担当へ委譲してから公開します]
#   引数: [
#     allies: 味方保存個体レコード列（Variant）
#     enemies: 敵個体レコード列（Variant）
#     shuffle_order: 初回生存者の明示順（Variant）
#     initial_statuses: 専用開始の明示状態、従来入口ではnull（Variant）
#     with_statuses: 専用入口でだけtrueに固定する構築区分（bool）
#   ]
#   戻り値: [result: 準備と数値Session、または使用中の参照を変更しない拒否（Dictionary）]
# }
func _start(allies: Variant, enemies: Variant, shuffle_order: Variant, initial_statuses: Variant, with_statuses: bool) -> Dictionary:
	# 戦闘呼び出し処理は、既に開始した戦闘を新しい参加者で二重に初期化する要求を拒否します。
	if _session.snapshot()["phase"] != "not_started":
		return {"ok": false, "reason": "already_initialized"}
	var prepared: Dictionary = _preparation.prepare(allies, enemies, shuffle_order)
	if not prepared["ok"]:
		return prepared
	# 戦闘呼び出し処理は、準備失敗時に使用中の戦闘資源を部分更新しないため、候補のbattle_session.gdの戦闘状態を別に構築します。
	var candidate = Session.new()
	var started: Dictionary
	if with_statuses:
		started = candidate.start_with_statuses(_snapshots(prepared["teams"]["allies"]), _snapshots(prepared["teams"]["enemies"]), initial_statuses)
	else:
		started = candidate.start(_snapshots(prepared["teams"]["allies"]), _snapshots(prepared["teams"]["enemies"]))
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
	# 魔法用の習得・許可装備・属性耐性も、同じ候補Sessionとの一致を確認する。
	var magic = Magic.new(candidate)
	var magical: Dictionary = magic.start(prepared["teams"], skills["value"])
	if not magical["ok"]:
		return magical
	# 通常魔法と別の入口で自傷効果を扱い、資源更新の順序は共用の行動処理へ任せる。
	var self_magic = Magic.new(candidate, true)
	var self_magical: Dictionary = self_magic.start(prepared["teams"], skills["value"])
	if not self_magical["ok"]:
		return self_magical
	# 吸MP専用区分も同じ候補Sessionへ接続し、MP移転の計算・実更新を呼び出し層へ取り込みません。
	var drain_magic = Magic.new(candidate, false, true)
	var drain_magical: Dictionary = drain_magic.start(prepared["teams"], skills["value"])
	if not drain_magical["ok"]:
		return drain_magical
	# 回復も同じ候補Sessionへ委譲し、呼び出し層でHP/MPを計算・更新しません。
	var heal = Heal.new(candidate)
	var healing: Dictionary = heal.start(prepared["teams"], skills["value"])
	if not healing["ok"]:
		return healing
	var cure_heal: RefCounted
	var status_physical: RefCounted
	if with_statuses:
		# 専用入口だけが治療付き行動を構築します。通常回復の治療拒否は解除しません。
		cure_heal = Heal.new(candidate, true)
		var curing: Dictionary = cure_heal.start_cure_heal(prepared["teams"], skills["value"], initial_statuses)
		if not curing["ok"]:
			return curing
		# 付与付き物理の実行と非消費検査は、同じ候補Sessionと開始情報を使う専用行動へ委譲します。
		status_physical = StatusPhysical.new(candidate)
		var status_checked: Dictionary = status_physical.start(prepared["teams"], skills["value"], initial_statuses)
		if not status_checked["ok"]:
			return status_checked
	# 戦闘呼び出し処理は、全行動処理/検査の設定と初回ラウンドが成功してから、候補の参照を一度に公開します。
	var planned: Dictionary = candidate.begin_round(shuffle_order)
	if not planned["ok"]:
		return planned
	_session = candidate
	_attack = attack
	_defend = defend
	_physical = physical
	_magic = magic
	_self_magic = self_magic
	_drain_magic = drain_magic
	_heal = heal
	_cure_heal = cure_heal
	_status_physical = status_physical
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
#   責務: [resolve_magic_skill: 明示された単体魔法の検証・MP消費・HP変化を魔法行動処理へ委譲します]
#   処理: [1: 初期化済みのmagic_skill_action.gdへ要求を渡し、未初期化なら拒否します]
#   引数: [request: ticket・敵target・skill_id・varianceの4キーを持つ要求（Variant）]
#   戻り値: [result: 魔法行動の適用結果または未初期化の拒否（Dictionary）]
# }
func resolve_magic_skill(request: Variant) -> Dictionary:
	# 呼び出し処理は数値・習得判定を重複実装せず、単体魔法の担当へ委譲する。
	return {"ok": false, "reason": "not_initialized"} if _magic == null else _magic.resolve(request)


# {
#   責務: [resolve_self_damage_magic_skill: 自傷付き単体魔法の検証・MP消費・敵と術者のHP変化を行動処理へ委譲します]
#   処理: [1: 自傷専用設定のmagic_skill_action.gdへ要求を渡し、未初期化なら拒否します]
#   引数: [request: ticket・敵target・skill_id・varianceの4キーを持つ自傷魔法要求（Variant）]
#   戻り値: [result: 自傷魔法の適用結果または理由付き拒否（Dictionary）]
# }
func resolve_self_damage_magic_skill(request: Variant) -> Dictionary:
	# 呼び出し処理はHP代償を計算・更新せず、共用の魔法行動処理へ委譲する。
	return {"ok": false, "reason": "not_initialized"} if _self_magic == null else _self_magic.resolve(request)


# {
#   責務: [resolve_drain_mp_skill: 吸MP魔法の予約・習得・資源の検証と敵HP/両者MP更新を、専用区分の魔法行動へ委譲します]
#   処理: [1: 吸MP専用のmagic_skill_action.gdへ要求を渡し、未初期化なら資源を変更せず拒否します]
#   引数: [request: ticket・敵target・skill_id・varianceの4キーを持つ吸MP魔法要求（Variant）]
#   戻り値: [result: 実MP消費・敵HP/MP喪失・術者MP回復の結果とSession、または理由付き拒否（Dictionary）]
# }
func resolve_drain_mp_skill(request: Variant) -> Dictionary:
	# 呼び出し層はMP移転や最大MPの制限を重複実装せず、資源を所有する戦闘処理へ委譲します。
	return {"ok": false, "reason": "not_initialized"} if _drain_magic == null else _drain_magic.resolve(request)


# {
#   責務: [resolve_heal_skill: 明示した生存味方1体への回復要求の検証・MP支払い・HP回復を担当行動へ委譲します]
#   処理: [1: 初期化済みのheal_skill_action.gdへ要求を渡し、未初期化なら資源を変更せず拒否します]
#   引数: [request: ticket・同陣営target・skill_idの3キーだけを持つ単体HP回復要求（Variant）]
#   戻り値: [result: 実回復量・実消費MPとSessionコピー、行動取消、または理由付き拒否（Dictionary）]
# }
func resolve_heal_skill(request: Variant) -> Dictionary:
	# 呼び出し層では回復対象を自動選択せず、指定対象の検証と回復量を担当行動へ任せます。
	return {"ok": false, "reason": "not_initialized"} if _heal == null else _heal.resolve(request)


# {
#   責務: [resolve_cure_heal_skill: 明示された同陣営への治療付き回復を、専用区分の共用回復行動へ委譲します]
#   処理: [1: 専用行動がなければ未初期化を返し、構築済みなら検証/実更新を担当へ渡します]
#   引数: [request: 現在ticket・同陣営target・治療付きskill_idと任意rollだけの要求（Variant）]
#   戻り値: [result: 実HP/MP/治療と独立Session/状態コピー、行動取消、または拒否（Dictionary）]
# }
func resolve_cure_heal_skill(request: Variant) -> Dictionary:
	return {"ok": false, "reason": "not_initialized"} if _cure_heal == null else _cure_heal.resolve(request)


# {
#   責務: [inspect_status_physical_skill: 付与付き物理の予約/習得/敵対象/最新資源・状態の非消費検査を担当へ委譲します]
#   処理: [1: 状態付き専用開始で設定した検査へ要求を渡し、未設定ならnot_initializedを返します]
#   引数: [request: 現在ticket・敵target・習得済みskill_idだけを持つ検査要求（Variant）]
#   戻り値: [result: 独立した非消費検査結果または拒否。実行/ダメージ/状態付与は行いません（Dictionary）]
# }
func inspect_status_physical_skill(request: Variant) -> Dictionary:
	# 呼び出し層は検査結果を行動の実行許可として保持せず、数値/状態の計算や更新も行いません。
	return {"ok": false, "reason": "not_initialized"} if _status_physical == null else _status_physical.inspect(request)


# {
#   責務: [resolve_status_physical_skill: 付与付き単体物理の予約検証・状態補正・MP/HP/状態更新を専用行動へ委譲します]
#   処理: [1: 状態付き開始で構築した行動へ要求を渡し、未設定ならnot_initializedを返します]
#   引数: [request: ticket/敵target/skill_id/critical_roll/varianceと任意status_rollを持つ行動要求（Variant）]
#   戻り値: [result: 専用行動の適用結果、行動取消、または拒否（Dictionary）]
# }
func resolve_status_physical_skill(request: Variant) -> Dictionary:
	# 呼出層はダメージや状態を計算せず、同じSessionを持つ専用行動へ渡します。
	return {"ok": false, "reason": "not_initialized"} if _status_physical == null else _status_physical.resolve(request)


# {
#   責務: [statuses: 全参加者の所有状態を数値snapshotとは別の独立コピーで取得します]
#   処理: [1: Sessionの全状態読取へ委譲します]
#   引数: []
#   戻り値: [result: side/id別teamsとbattle_status_only区分、未設定なら空辞書（Dictionary）]
# }
func statuses() -> Dictionary:
	return _session.statuses()


# {
#   責務: [status: 指定参加者の所有状態一覧を独立コピーとしてSessionから取得します]
#   処理: [1: Sessionへside/idキーを渡し、読取または拒否を返します]
#   引数: [key: 読み取る参加者のside/id（Variant）]
#   戻り値: [result: status_effectsのsnapshotまたは未設定/不正参加者の拒否（Dictionary）]
# }
func status(key: Variant) -> Dictionary:
	return _session.status(key)


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
