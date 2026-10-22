# {
#   責務: [run_save_probe: Real production-scene save/load probe. All paths are private fixtures from tests.]
#   フィールド: []
# }
extends SceneTree
## Real production-scene save/load probe. All paths are private fixtures from tests.

const SaveStore = preload("res://data/field_save_store.gd")


# {
#   責務: [_initialize: run・保存・probeのエントリ処理を実行する]
#   処理: [1: run・保存・probeのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _initialize() -> void:
	_run.call_deferred()


# {
#   責務: [_run: run・保存・probeを実行する]
#   処理: [1: run・保存・probeを実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _run() -> void:
	var arguments := OS.get_cmdline_user_args()
	var request: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	var scene = load("res://scenes/field.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	scene.set_process(false)
	var observations: Array = [_snapshot(scene)]
	for action: Dictionary in request.get("actions", []):
		var outcome: Variant = null
		match action["kind"]:
			"open":
				outcome = scene.open_map(action["map_id"], action.get("entry", {}))
			"key":
				var key := InputEventKey.new()
				key.physical_keycode = KEY_F5 if action["key"] == "F5" else KEY_F9
				key.pressed = true
				Input.parse_input_event(key.duplicate())
				Input.flush_buffered_events()
				await process_frame
				key.pressed = false
				Input.parse_input_event(key.duplicate())
				Input.flush_buffered_events()
			"save":
				outcome = scene.save_current_position()
			"load":
				outcome = scene.load_saved_position()
			"stale_write":
				outcome = scene.persistence.store.save_profile(scene.profile_name, {}, "wrong-digest", {})
		var observation := _snapshot(scene)
		observation["outcome"] = outcome
		observations.append(observation)
	var names: Array = []
	for name: String in request.get("names", []):
		names.append(SaveStore.validate_name(name))
	print("KADOKA_SAVE_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({
		"observations": observations, "names": names,
	})))
	quit(0)


# {
#   責務: [_snapshot: run・保存・probeを状態を複製する]
#   処理: [1: run・保存・probeを状態を複製する]
#   引数: [scene: scene（Control）]
#   戻り値: [result: run・保存・probeを状態を複製するための結果（Dictionary）]
# }
func _snapshot(scene: Control) -> Dictionary:
	return {
		"map_id": scene.session.world.get("id", ""), "x": scene.session.x, "y": scene.session.y,
		"direction": scene.session.direction, "status": scene.status.text,
	}
