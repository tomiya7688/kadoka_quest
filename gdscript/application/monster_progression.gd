extends RefCounted
## Join an owned monster to read-only species documents; cache only within one roster scan.

const Progression = preload("res://engine/monster_progression.gd")
var repository: RefCounted
var documents: Dictionary = {}


func _init(content: RefCounted) -> void:
	repository = content


func rebuild(monster: Dictionary) -> Dictionary:
	var species_id: String = monster["species_id"]
	if not documents.has(species_id):
		documents[species_id] = repository.load_progression(species_id)
	var bundle: Dictionary = documents[species_id]
	if not bundle["ok"]:
		return bundle.duplicate(true)
	return Progression.rebuild(bundle["stats"], bundle["skills"], monster.get("level", 1))
