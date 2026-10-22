# {
#   責務: [run_password_probe: 専用JSONの操作列で合言葉入力の純粋処理とフィールドSceneを検証するDeveloper専用入口です]
#   フィールド: []
# }
extends SceneTree
## 合言葉入力の状態・画面操作・保存失敗を、呼出側が用意した専用保存先で観測します。
const Password = preload("res://engine/password_session.gd")
const KEYS := {"Enter": KEY_ENTER, "KPEnter": KEY_KP_ENTER, "Escape": KEY_ESCAPE, "Backspace": KEY_BACKSPACE,
	"F5": KEY_F5, "F9": KEY_F9, "F6": KEY_F6, "Tab": KEY_TAB, "Space": KEY_SPACE,
	"Left": KEY_LEFT, "Right": KEY_RIGHT, "E": KEY_E}
const Documents = preload("res://data/json_documents.gd")


# {
#   責務: [FaultStore: 仲間加入の保存失敗と保存後の外部変更を、専用保存先へ注入するテスト用Storeです]
#   フィールド: [
#     mode: 二体目の公開失敗または保存後の外部変更を選ぶ検証区分（String）
#     profile: 外部変更の注入先となる専用プロフィールのパス（String）
#     calls: create_newの呼出回数。二回目の失敗判定に使います（int）
#   ]
# }
class FaultStore extends "res://data/monster_store.gd":
	var mode: String
	var profile: String
	var calls := 0

	# {
	#   責務: [_init: テスト用Storeの親を初期化し、専用保存先と失敗注入区分を保持します]
	#   処理: [
	#     1: 親Storeへ保存先を渡し、失敗注入で使うパスと区分を設定します
	#   ]
	#   引数: [
	#     path: 検証専用プロフィールのパス（String）
	#     fault: fail_secondまたはexternal_stateなどの注入区分（String）
	#   ]
	#   戻り値: [result: なし（void）]
	# }
	func _init(path: String, fault: String) -> void:
		super(path)
		profile = path
		mode = fault

	# {
	#   責務: [create_new: 通常の個体公開へ委譲し、指定された保存失敗または外部変更だけを注入します]
	#   処理: [
	#     1: 二回目の公開を失敗させる区分なら、書込前に失敗を返します
	#     2: 通常公開の初回成功後に外部変更を注入する区分なら、専用stateへ目印を書きます
	#   ]
	#   引数: [
	#     record: 専用保存先へ公開する個体レコード（Dictionary）
	#   ]
	#   戻り値: [result: 通常の公開結果または注入したwrite_failedの辞書（Dictionary）]
	# }
	func create_new(record: Dictionary) -> Dictionary:
		calls += 1
		if mode == "fail_second" and calls == 2:
			return {"ok": false, "error": "write_failed", "message": "test-only second-publication failure"}
		var result: Dictionary = super.create_new(record)
		if result["ok"] and mode == "external_state" and calls == 1:
			var state: Dictionary = Documents.read_object(profile.path_join("state.json"))["value"]
			state["external_update"] = "kept"
			Documents.write_atomic(profile.path_join("state.json"), state)
		return result


# {
#   責務: [FaultService: 仲間加入Serviceへ、失敗注入用Storeを返すテスト用の依存差替えを提供します]
#   フィールド: [
#     mode: 構築するFaultStoreへ渡す失敗注入区分（String）
#   ]
# }
class FaultService extends "res://application/ghost_acquisition.gd":
	var mode: String

	# {
	#   責務: [_init: テスト用仲間加入Serviceの親へFieldを渡し、Storeの失敗注入区分を保持します]
	#   処理: [
	#     1: 親Serviceを初期化し、後から作るFaultStoreの区分を保存します
	#   ]
	#   引数: [
	#     field: 検証用Fieldの参照（RefCounted）
	#     fault: FaultStoreへ渡す失敗注入区分（String）
	#   ]
	#   戻り値: [result: なし（void）]
	# }
	func _init(field: RefCounted, fault: String) -> void:
		super(field)
		mode = fault

	# {
	#   責務: [_monster_store: 仲間加入の通常Storeを、専用保存先と注入区分を持つFaultStoreへ差し替えます]
	#   処理: [
	#     1: 指定された専用保存先と保持する注入区分でFaultStoreを構築します
	#   ]
	#   引数: [
	#     path: 検証用プロフィールのパス（String）
	#   ]
	#   戻り値: [result: 失敗注入に使うStoreの参照（RefCounted）]
	# }
	func _monster_store(path: String) -> RefCounted:
		return FaultStore.new(path, mode)


# {
#   責務: [_initialize: SceneTreeの初期化後に、合言葉検証の_runを遅延実行します]
#   処理: [
#     1: _runを遅延呼出しへ登録し、Scene生成前の初期化を終えます
#   ]
#   引数: []
#   戻り値: [result: なし（void）]
# }
func _initialize() -> void:
	_run.call_deferred()


# {
#   責務: [_run: run・暗号・probeを実行する]
#   処理: [1: run・暗号・probeを実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _run() -> void:
	var request: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	var result: Variant
	if request.get("scene", false):
		result = await _scene(request)
	else:
		result = _cases(request)
	print("KADOKA_PASSWORD=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit()


# {
#   責務: [_cases: run・暗号・probeのcasesを求める]
#   処理: [1: run・暗号・probeのcasesを求める]
#   引数: [request: 要求（Dictionary）]
#   戻り値: [result: run・暗号・probeのcasesを求めるための結果（Array）]
# }
func _cases(request: Dictionary) -> Array:
	var result: Array = []
	for case: Dictionary in request["cases"]:
		var session = Password.new(case.get("secret", Password.PASSWORD), case.get("keys", Password.KANA_KEYS))
		var observations: Array = [{"state": session.snapshot(), "result": null}]
		for operation: Dictionary in case["operations"]:
			var outcome: Variant = null
			match operation["kind"]:
				"open": session.open()
				"append": outcome = session.append(operation["value"])
				"backspace": outcome = session.backspace()
				"submit": outcome = session.submit()
				"cancel": session.cancel()
			observations.append({"state": session.snapshot(), "result": outcome})
		result.append(observations)
	return result


# {
#   責務: [_scene: run・暗号・probeのsceneを求める]
#   処理: [1: run・暗号・probeのsceneを求める]
#   引数: [request: 要求（Dictionary）]
#   戻り値: [result: run・暗号・probeのsceneを求めるための結果（Array）]
# }
func _scene(request: Dictionary) -> Array:
	root.size = Vector2i(960, 540)  # Headless OS window defaults to 64x64, not the game's viewport.
	var scene = load("res://scenes/field.tscn").instantiate()
	root.add_child(scene)
	scene.set_process(false)
	var signals: Array = []
	scene.password_finished.connect(func(result: Dictionary): signals.append(result))
	await process_frame
	var observations: Array = []
	for action: Dictionary in request["actions"]:
		var outcome: Variant = null
		match action["kind"]:
			"open": scene.open_map("ghost_home", action.get("entry", {"x": 17, "y": 8, "direction": "back"}))
			"key": await _key(action)
			"type":
				for index in str(action["value"]).length():
					await _key({"unicode": str(action["value"]).unicode_at(index)})
			"click": await _click(scene.password_view.buttons[action["target"]])
			"commit_signal":
				# Adapter-level batch signal, not a real OS IME composition.
				scene.password_view.text_input.text = action["value"]
				scene.password_view.text_input.text_changed.emit(action["value"])
			"focus": scene.password_view.buttons[action["target"]].grab_focus()
			"tick": scene._process(float(action["delta"]))
			"save": outcome = scene.save_current_position()
			"load": outcome = scene.load_saved_position()
			"roster": scene.open_owned_roster()
			"party": scene.begin_party_edit()
			"fault": scene.ghost_acquisition = FaultService.new(scene.persistence, action["mode"])
			"change_state":
				var profile: Dictionary = scene.persistence.store.resolve_profile(scene.profile_name)
				var state: Dictionary = scene.persistence.store.load_profile(scene.profile_name)["value"]
				state.merge(action["changes"], true)
				Documents.write_atomic(profile["path"].path_join("state.json"), state)
		await process_frame
		var slot_texts: Array = []
		for slot: Label in scene.password_view.slots:
			slot_texts.append(slot.text)
		var panel: Rect2 = scene.password_view.get_global_rect()
		var bounds_ok := Rect2(Vector2.ZERO, Vector2(root.size)).encloses(panel)
		for button: Button in scene.password_view.buttons.values():
			bounds_ok = bounds_ok and panel.encloses(button.get_global_rect())
		observations.append({"state": scene.password_session.snapshot(), "visible": scene.password_view.visible,
			"slots": slot_texts, "keys": scene.password_view.buttons.keys(), "clock": scene.session.clock_ms,
			"player": [scene.session.x, scene.session.y], "npcs": scene.session.character_snapshot(),
			"keyboard_elapsed": scene.keyboard.elapsed, "roster": scene.roster_view.visible, "party": scene.party_view.visible,
			"outcome": outcome, "signals": signals.duplicate(true), "result": scene.password_outcome.duplicate(),
			"status": scene.status.text, "message": scene.password_view.message.text,
			"native_text": scene.password_view.text_input.text, "bounds_ok": bounds_ok,
			"panel_rect": str(panel), "window_size": str(root.size),
			"acquisition": scene.acquisition_result.duplicate(true), "owned": scene.owned_snapshot.duplicate(true),
			"roster_text": scene.roster_view.body.text})
	return observations


# {
#   責務: [_key: run・暗号・probeのキーを求める]
#   処理: [1: run・暗号・probeのキーを求める]
#   引数: [action: action（Dictionary）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _key(action: Dictionary) -> void:
	var key := InputEventKey.new()
	key.physical_keycode = KEYS.get(action.get("key", ""), 0)
	key.keycode = key.physical_keycode  # Native Tab/Space actions need logical codes too.
	key.unicode = int(action.get("unicode", 0))
	key.echo = action.get("echo", false)
	key.pressed = true
	Input.parse_input_event(key.duplicate())
	Input.flush_buffered_events()
	await process_frame
	key.pressed = false
	key.echo = false
	Input.parse_input_event(key.duplicate())
	Input.flush_buffered_events()
	await process_frame


# {
#   責務: [_click: run・暗号・probeのclickを求める]
#   処理: [1: run・暗号・probeのclickを求める]
#   引数: [control: control（Control）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _click(control: Control) -> void:
	var point := root.get_final_transform() * control.get_global_rect().get_center()
	root.notify_mouse_entered()
	var motion := InputEventMouseMotion.new()
	motion.position = point
	motion.global_position = point
	Input.parse_input_event(motion)
	Input.flush_buffered_events()
	await process_frame
	var button := InputEventMouseButton.new()
	button.position = point
	button.global_position = point
	button.button_index = MOUSE_BUTTON_LEFT
	button.pressed = true
	Input.parse_input_event(button.duplicate())
	Input.flush_buffered_events()
	await process_frame
	button.pressed = false
	Input.parse_input_event(button.duplicate())
	Input.flush_buffered_events()
	await process_frame
