# {
#   責務: [content_images: External PNG adaptation/cache; no game outcomes or species repository access.]
#   フィールド: [
#     asset_root: asset・基準ディレクトリ（String）
#     species: 種族（Dictionary）
#     cache: cache（Dictionary）
#   ]
# }
extends RefCounted
## External PNG adaptation/cache; no game outcomes or species repository access.

var asset_root: String
var species: Dictionary = {}
var cache: Dictionary = {}


# {
#   責務: [_init: content・画像一覧が利用する初期状態と依存を設定する]
#   処理: [1: content・画像一覧が利用する初期状態と依存を設定する]
#   引数: [content_root: content・基準ディレクトリ（String）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(content_root: String) -> void:
	asset_root = content_root.path_join("assets").simplify_path()


# {
#   責務: [texture: content・画像一覧のtextureを求める]
#   処理: [1: content・画像一覧のtextureを求める]
#   引数: [relative: relative（String）]
#   戻り値: [result: content・画像一覧のtextureを求めるための結果（Variant）]
# }
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


# {
#   責務: [character_texture: content・画像一覧のキャラクター・textureを求める]
#   処理: [1: content・画像一覧のキャラクター・textureを求める]
#   引数: [
#     species_id: 種族・識別子（String）
#     direction: direction（String）
#   ]
#   戻り値: [result: content・画像一覧のキャラクター・textureを求めるための結果（Variant）]
# }
func character_texture(species_id: String, direction: String) -> Variant:
	var definition: Dictionary = species.get(species_id, {})
	var sprites: Dictionary = definition.get("field_sprites", {})
	return texture(str(sprites.get(direction, definition.get("field_sprite_path", ""))))


# {
#   責務: [block_texture: content・画像一覧のブロック・textureを求める]
#   処理: [1: content・画像一覧のブロック・textureを求める]
#   引数: [block: ブロック（Dictionary）]
#   戻り値: [result: content・画像一覧のブロック・textureを求めるための結果（Variant）]
# }
func block_texture(block: Dictionary) -> Variant:
	var appearance: Dictionary = block.get("appearance", {})
	if appearance.get("type") == "path":
		return texture(str(appearance.get("value", "")))
	return null
