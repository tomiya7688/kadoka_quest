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
#   責務: [_init: 正規の基礎能力値と習得スキルを取得するリポジトリを保持します]
#   処理: [1: 正規の基礎能力値と習得スキルを取得するリポジトリを保持します]
#   引数: [content: 正規種族・装備定義の読込先（RefCounted）]
#   戻り値: [result: なし（void）。正規基礎定義の取得先を設定します]
# }
func _init(content: RefCounted) -> void:
	repository = content


# {
#   責務: [rebuild: 種族別の基礎定義を構築処理内で共用し、指定レベルの能力値と習得IDの計算へ委譲します]
#   処理: [1: 種族別の基礎定義を構築処理内で共用し、指定レベルの能力値と習得IDの計算へ委譲します]
#   引数: [monster: モンスター（Dictionary）]
#   戻り値: [result: レベル別能力値・習得IDの再構築結果、または正規定義の読込・検証失敗（Dictionary）]
# }
func rebuild(monster: Dictionary) -> Dictionary:
	var species_id: String = monster["species_id"]
	if not documents.has(species_id):
		documents[species_id] = repository.load_progression(species_id)
	var bundle: Dictionary = documents[species_id]
	if not bundle["ok"]:
		return bundle.duplicate(true)
	return Progression.rebuild(bundle["stats"], bundle["skills"], monster.get("level", 1))
