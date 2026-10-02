extends RefCounted
## External PNG adaptation/cache; no game outcomes or species repository access.

var asset_root: String
var species: Dictionary = {}
var cache: Dictionary = {}


func _init(content_root: String) -> void:
	asset_root = content_root.path_join("assets").simplify_path()


func texture(relative: String) -> Variant:
	if relative.is_empty():
		return null
	var path := asset_root.path_join(relative).simplify_path()
	if relative.is_absolute_path() or not path.begins_with(asset_root + "/"):
		return null
	if not cache.has(path):
		cache[path] = null
		if FileAccess.file_exists(path):
			var image := Image.load_from_file(path)
			if image != null and not image.is_empty():
				cache[path] = ImageTexture.create_from_image(image)
	return cache[path]


func character_texture(species_id: String, direction: String) -> Variant:
	var definition: Dictionary = species.get(species_id, {})
	var sprites: Dictionary = definition.get("field_sprites", {})
	return texture(str(sprites.get(direction, definition.get("field_sprite_path", ""))))


func block_texture(block: Dictionary) -> Variant:
	var appearance: Dictionary = block.get("appearance", {})
	if appearance.get("type") == "path":
		return texture(str(appearance.get("value", "")))
	return null
