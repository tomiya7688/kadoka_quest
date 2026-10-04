extends Control
## Draw a supplied snapshot. Does not move actors or invoke repository/services.

const CELL := 64
var model: Dictionary = {}
var images: RefCounted


func show_snapshot(snapshot: Dictionary, image_provider: RefCounted) -> void:
	model = snapshot
	images = image_provider
	queue_redraw()


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color("#091329"))
	if model.is_empty():
		return
	var world: Dictionary = model["map"]
	var player: Dictionary = model["player"]
	var columns := maxi(1, int(size.x / CELL))
	var rows := maxi(1, int(size.y / CELL))
	var camera := Vector2i(
		clampi(int(player["x"]) - (columns >> 1), 0, maxi(0, int(world["width"]) - columns)),
		clampi(int(player["y"]) - (rows >> 1), 0, maxi(0, int(world["height"]) - rows)),
	)
	for sy in mini(rows, int(world["height"])):
		for sx in mini(columns, int(world["width"])):
			var block_id: String = world["tiles"][sy + camera.y][sx + camera.x]
			_draw_tile(Rect2(sx * CELL, sy * CELL, CELL, CELL), model["blocks"].get(block_id, {}))
	for character: Dictionary in model["characters"]:
		_draw_character(character, camera)
	_draw_character(player, camera)


func _draw_tile(rect: Rect2, block: Dictionary) -> void:
	var appearance: Dictionary = block.get("appearance", {})
	var color := Color("#344052")
	if appearance.get("type") == "color":
		color = Color.from_string(str(appearance.get("value", "")), color)
	draw_rect(rect, color)
	var image: Variant = images.block_texture(block)
	if image != null:
		draw_texture_rect(image, rect, false)


func _draw_character(character: Dictionary, camera: Vector2i) -> void:
	var cell := Vector2(float(character.get("display_x", character["x"])),
		float(character.get("display_y", character["y"]))) - Vector2(camera)
	var rect := Rect2(cell.x * CELL, cell.y * CELL, CELL, CELL)
	if not Rect2(Vector2.ZERO, size).intersects(rect):
		return
	var image: Variant = images.character_texture(str(character["species_id"]), str(character.get("direction", "front")))
	if image == null:
		draw_rect(rect.grow(-12), Color("#f4eeee"))
		return
	var image_size: Vector2 = image.get_size()
	var fit := minf(CELL / image_size.x, CELL / image_size.y)
	var target_size := image_size * fit
	draw_texture_rect(image, Rect2(rect.position + (rect.size - target_size) / 2, target_size), false)
