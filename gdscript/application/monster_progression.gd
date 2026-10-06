# {
#   責務: [monster_progression: Join an owned monster to read-only species documents; cache only within one roster scan.]
#   フィールド: [
#     repository: データ取得先（RefCounted）
#     documents: 文書一覧（Dictionary）
#   ]
# }
extends RefCounted
## Join an owned monster to read-only species documents; cache only within one roster scan.

const Progression = preload("res://engine/monster_progression.gd")
var repository: RefCounted
var documents: Dictionary = {}


# {
#   責務: [_init: モンスター・progressionが利用する初期状態と依存を設定する]
#   処理: [1: モンスター・progressionが利用する初期状態と依存を設定する]
#   引数: [content: content（RefCounted）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(content: RefCounted) -> void:
	repository = content


# {
#   責務: [rebuild: モンスター・progressionのrebuildを求める]
#   処理: [1: モンスター・progressionのrebuildを求める]
#   引数: [monster: モンスター（Dictionary）]
#   戻り値: [result: モンスター・progressionのrebuildを求めるための結果（Dictionary）]
# }
func rebuild(monster: Dictionary) -> Dictionary:
	var species_id: String = monster["species_id"]
	if not documents.has(species_id):
		documents[species_id] = repository.load_progression(species_id)
	var bundle: Dictionary = documents[species_id]
	if not bundle["ok"]:
		return bundle.duplicate(true)
	return Progression.rebuild(bundle["stats"], bundle["skills"], monster.get("level", 1))
