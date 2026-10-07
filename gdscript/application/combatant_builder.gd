# {
#   責務: [combatant_builder: Read-only reconstruction -> plain, full-resource battle snapshot; never a saved record update.]
#   フィールド: [reconstruction: reconstruction（RefCounted）]
# }
extends RefCounted
## Read-only reconstruction -> plain, full-resource battle snapshot; never a saved record update.

const Records = preload("res://engine/monster_record_contract.gd")
const Reconstruction = preload("res://application/monster_reconstruction.gd")
const State = preload("res://engine/combatant_state.gd")
const ACTIVE_TEAM_LIMIT := 4
var reconstruction: RefCounted


# {
#   責務: [_init: 戦闘個体・構築処理が利用する初期状態と依存を設定する]
#   処理: [1: 戦闘個体・構築処理が利用する初期状態と依存を設定する]
#   引数: [repository: データ取得先（RefCounted）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(repository: RefCounted) -> void:
	reconstruction = Reconstruction.new(repository)


# {
#   責務: [build: 戦闘個体・構築処理を構築する]
#   処理: [
#     1: 正規個体を読み取り専用で再構築する
#     2: 新鮮な資源と独立した習得ID・許可装備を返す
#   ]
#   引数: [record: 個体レコード（Variant）]
#   戻り値: [result: 戦闘個体・構築処理を構築するための結果（Dictionary）]
# }
func build(record: Variant) -> Dictionary:
	# 保存個体とAIの形式だけを確認し、不正レコードを補修して戦闘へ持ち込まない。
	if not record is Dictionary or not record.get("monster") is Dictionary or not record.get("ai") is Dictionary:
		return {"ok": false, "reason": "invalid_record"}
	var monster: Dictionary = record["monster"]
	var checked := Records.validate_record(monster, record["ai"], str(monster.get("id", "")))
	if not checked["ok"]:
		return {"ok": false, "reason": "invalid_record", "detail": checked}
	# レベル・＋選択・装備は正規JSONから再構築し、個体やAIへ書き戻さない。
	var rebuilt: Dictionary = reconstruction.rebuild(monster)
	if not rebuilt["ok"]:
		return {"ok": false, "reason": "reconstruction_failed", "detail": rebuilt.duplicate(true)}
	var modified: Dictionary = rebuilt["modifiers"]
	if not modified["ok"]:
		return {"ok": false, "reason": "modifiers_failed", "detail": modified.duplicate(true)}
	# 戦闘用の最大資源を新規Stateへ投影し、保存レコードとは分離する。
	var state = State.new()
	var initialized: Dictionary = state.start(monster, modified["stats"])
	if not initialized["ok"]:
		return initialized
	# 習得IDは資源6キーに混在させず、行動の開始時コピーとして渡す。
	return {"ok": true, "snapshot": state.snapshot(), "skill_ids": modified["skill_ids"].duplicate(true),
		"warnings": modified["warnings"].duplicate(true),
		"equipment": modified["equipment"].duplicate(true), "scope": "combatant_resources_only"}


# {
#   責務: [build_team: チームを構築する]
#   処理: [1: チームを構築する]
#   引数: [records: 個体レコード一覧（Variant）]
#   戻り値: [result: チームを構築するための結果（Dictionary）]
# }
func build_team(records: Variant) -> Dictionary:
	if not records is Array:
		return {"ok": false, "reason": "invalid_team"}
	if records.size() > ACTIVE_TEAM_LIMIT:
		return {"ok": false, "reason": "active_team_limit", "limit": ACTIVE_TEAM_LIMIT}
	var members: Array = []
	var ids: Dictionary = {}
	for index in records.size():
		var built := build(records[index])
		if not built["ok"]:
			built["index"] = index
			return built
		var id: String = built["snapshot"]["identity"]["id"]
		if ids.has(id):
			return {"ok": false, "reason": "duplicate_member", "index": index}
		ids[id] = true
		members.append(built)
	return {"ok": true, "members": members}
