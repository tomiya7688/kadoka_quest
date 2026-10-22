# {
#   責務: [run_scene_smoke: Headless integration of the production scene, real Input adapter and coordinator.]
#   フィールド: []
# }
extends SceneTree
## Headless integration of the production scene, real Input adapter and coordinator.


# {
#   責務: [_initialize: run・scene・smokeのエントリ処理を実行する]
#   処理: [1: run・scene・smokeのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _initialize() -> void:
	_run.call_deferred()


# {
#   責務: [_run: run・scene・smokeを実行する]
#   処理: [1: run・scene・smokeを実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _run() -> void:
	var scene = load("res://scenes/field.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	scene.set_process(false)  # Advance the real input adapter with explicit deltas.
	var initial: String = scene.session.world.get("id", "")
	var start: Array = [scene.session.x, scene.session.y]
	var key := InputEventKey.new()
	key.physical_keycode = KEY_RIGHT
	key.pressed = true
	Input.parse_input_event(key.duplicate())
	Input.flush_buffered_events()
	scene._process(0.0)
	var moved: Array = [scene.session.x, scene.session.y, scene.session.direction]
	scene.session.x = 34
	scene.session.y = 14
	scene._process(0.15)
	var crossed: String = scene.session.world.get("id", "")
	key.pressed = false
	Input.parse_input_event(key.duplicate())
	Input.flush_buffered_events()
	scene._process(0.0)
	scene.open_map("fresh_forest", {"x": 22, "y": 26})
	scene.session.move_player(0, 1)
	key.physical_keycode = KEY_ENTER
	key.pressed = true
	Input.parse_input_event(key.duplicate())
	Input.flush_buffered_events()
	await process_frame
	var interacted: String = scene.session.world.get("id", "")
	key.pressed = false
	Input.parse_input_event(key.duplicate())
	Input.flush_buffered_events()
	var stable_world: String = scene.session.world.get("id", "")
	var invalid_success: bool = scene.open_map("../../outside")
	print("KADOKA_SCENE_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({
		"initial": initial, "start": start, "moved": moved,
		"crossed": crossed, "interacted": interacted,
		"invalid_success": invalid_success,
		"stable_world": stable_world == scene.session.world.get("id", ""),
		"error_visible": scene.status.text.begins_with("Invalid map id"),
		"image_width": scene.images.character_texture("hero", "front").get_width(),
		"filter": scene.view.texture_filter,
	})))
	quit(0)
