# {
#   責務: [e2e_driver: Godot版のE2E操作を実行します。project.godotの起動画面を本番と同じ方法で開き、Inputの入力経路へキーと文字を送り、画面の状態を読み取りだけで記録します。ゲーム状態を直接書き換えません]
#   フィールド: [
#     checkpoints: ラベルごとに記録した画面の観測結果（Dictionary）
#     KEYS: シナリオのキー名とGodotの物理キーの対応（Dictionary）
#   ]
# }
extends SceneTree

const KEYS := {
	"ENTER": KEY_ENTER, "ESCAPE": KEY_ESCAPE, "TAB": KEY_TAB, "SPACE": KEY_SPACE, "BACKSPACE": KEY_BACKSPACE,
	"UP": KEY_UP, "DOWN": KEY_DOWN, "LEFT": KEY_LEFT, "RIGHT": KEY_RIGHT, "F5": KEY_F5, "F9": KEY_F9,
}
var checkpoints: Dictionary = {}


# {
#   責務: [_initialize: SceneTreeの初期化後へ、シナリオの実行を予約します]
#   処理: [1: シナリオ本体を遅延実行します]
#   引数: []
#   戻り値: [result: なし]
# }
func _initialize() -> void:
	_run.call_deferred()


# {
#   責務: [_run: シナリオJSONを読み、起動画面を開いて操作を順に実行し、観測結果を出力して終了します]
#   処理: [
#     1: コマンドライン引数のシナリオJSONを読みます
#     2: project.godotのrun/main_sceneを読み込み、本番の起動と同じく現在の画面に設定します
#     3: 各操作を順に実行し、失敗した操作は番号と理由を付けて中断します
#     4: 最後の画面をfinalとして記録し、結果をBase64のJSONで出力します
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _run() -> void:
	var arguments := OS.get_cmdline_user_args()
	var request: Variant = JSON.parse_string(FileAccess.get_file_as_string(arguments[0])) if arguments.size() == 1 else null
	if not request is Dictionary or not request.get("steps") is Array:
		_finish({"ok": false, "error": "シナリオJSONを読めません。"})
		return
	root.size = Vector2i(960, 540)
	# エディターで「実行」した場合と同じ起動画面を使い、検査専用の入口を作りません。
	var main_scene: String = ProjectSettings.get_setting("application/run/main_scene")
	var scene: Node = load(main_scene).instantiate()
	root.add_child(scene)
	current_scene = scene
	await process_frame
	await process_frame
	checkpoints["initial"] = _observe()
	var steps: Array = request["steps"]
	for index in steps.size():
		var step: Variant = steps[index]
		var error: String = await _perform(step) if step is Dictionary else "操作は辞書で指定してください。"
		if not error.is_empty():
			_finish({"ok": false, "error": "操作%d（%s）: %s" % [index, str(step.get("kind", "")) if step is Dictionary else "", error],
				"checkpoints": checkpoints})
			return
	checkpoints["final"] = _observe()
	_finish({"ok": true, "checkpoints": checkpoints})


# {
#   責務: [_perform: シナリオの一操作を、キー入力・文字入力・長押し・待機・画面待ち・観測のいずれかとして実行します]
#   処理: [
#     1: 操作の種類に応じて入力または待機を実行します
#     2: 未知の操作や不正な指定は、成功扱いにせず理由を返します
#   ]
#   引数: [step: kindと操作ごとの値を持つ一操作（Dictionary）]
#   戻り値: [result: 失敗理由。成功した場合は空文字列（String）]
# }
func _perform(step: Dictionary) -> String:
	match step.get("kind"):
		"key":
			if not KEYS.has(step.get("key")):
				return "未対応のキーです: " + str(step.get("key"))
			_send_key(KEYS[step["key"]], true)
			await process_frame
			_send_key(KEYS[step["key"]], false)
			await process_frame
			await process_frame
		"text":
			# IMEを通さない確定文字として、LineEditへ一文字ずつUnicodeのキー入力を送ります。
			for character in str(step.get("value", "")):
				_send_text(character, true)
				_send_text(character, false)
				await process_frame
		"hold":
			if not KEYS.has(step.get("key")) or not step.get("frames") is float or step["frames"] < 1:
				return "長押しにはキーと1以上のframesを指定してください。"
			_send_key(KEYS[step["key"]], true)
			for frame in int(step["frames"]):
				await process_frame
			_send_key(KEYS[step["key"]], false)
			await process_frame
		"frames":
			for frame in int(step.get("count", 1)):
				await process_frame
		"wait_scene":
			# 画面の切替を固定のフレーム数に頼らず待ち、上限を超えたら失敗にします。
			for frame in int(step.get("max_frames", 120)):
				if current_scene != null and current_scene.name == str(step.get("name")):
					await process_frame
					return ""
				await process_frame
			return "画面%sへ切り替わりませんでした。" % str(step.get("name"))
		"snapshot":
			var label := str(step.get("label", ""))
			if label.is_empty() or label in ["initial", "final"] or checkpoints.has(label):
				return "観測のlabelは一意で、initialとfinal以外にしてください。"
			checkpoints[label] = _observe()
		_:
			return "未知の操作です。"
	return ""


# {
#   責務: [_send_key: 物理キーの押下または解放を、OSから届いた入力と同じInputの経路へ送ります]
#   処理: [1: 物理キーとキーコードを設定したイベントをInputへ渡し、すぐに配信します]
#   引数: [
#     keycode: 押下または解放する物理キー（Key）
#     pressed: 押下ならtrue、解放ならfalse（bool）
#   ]
#   戻り値: [result: なし]
# }
func _send_key(keycode: Key, pressed: bool) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = keycode
	event.keycode = keycode
	event.pressed = pressed
	Input.parse_input_event(event)
	Input.flush_buffered_events()


# {
#   責務: [_send_text: 一文字の確定入力を、Unicode付きのキー入力としてInputの経路へ送ります]
#   処理: [1: キーコードなしでUnicodeだけを持つイベントをInputへ渡し、すぐに配信します]
#   引数: [
#     character: 入力する一文字（String）
#     pressed: 押下ならtrue、解放ならfalse（bool）
#   ]
#   戻り値: [result: なし]
# }
func _send_text(character: String, pressed: bool) -> void:
	var event := InputEventKey.new()
	event.unicode = character.unicode_at(0)
	event.pressed = pressed
	Input.parse_input_event(event)
	Input.flush_buffered_events()


# {
#   責務: [_observe: 現在の画面がタイトルかフィールドかを判定し、利用者に見える状態を読み取りだけで記録します]
#   処理: [
#     1: 現在の画面名とキーボードフォーカスの表示を記録します
#     2: タイトルなら表示中の枠・案内・セーブ一覧、フィールドなら地図・位置・向き・案内・メニュー表示を記録します
#   ]
#   引数: []
#   戻り値: [result: 画面の観測結果（Dictionary）]
# }
func _observe() -> Dictionary:
	var scene: Node = current_scene
	var observation := {"scene": scene.name if scene != null else "", "focus": _focus_text()}
	if scene != null and scene.has_method("start_new_game") and scene.get("view") != null:
		var view: Control = scene.view
		var names: Array = []
		for index in view.profile_list.item_count:
			names.append(view.profile_list.get_item_text(index))
		observation["title"] = {"page": view.page, "message": view.message.text,
			"continue_disabled": view.continue_button.disabled, "profiles": names}
	elif scene != null and scene.get("session") != null:
		var session = scene.session
		observation["field"] = {"profile": scene.profile_name, "map_id": session.world.get("id", ""),
			"x": session.x, "y": session.y, "direction": session.direction, "status": scene.status.text,
			"menu_visible": scene.chrome.menu.visible}
	return observation


# {
#   責務: [_focus_text: キーボードフォーカスのある部品を、利用者に見える文字で表します]
#   処理: [1: ボタンは表示文字、一覧は選択中の項目、入力欄は入力中の文字を返します]
#   引数: []
#   戻り値: [result: フォーカスの説明。フォーカスがなければ空文字列（String）]
# }
func _focus_text() -> String:
	var focused := root.gui_get_focus_owner()
	if focused is Button:
		return "Button:" + focused.text
	if focused is ItemList:
		var selected: PackedInt32Array = focused.get_selected_items()
		return "ItemList:" + (focused.get_item_text(selected[0]) if not selected.is_empty() else "")
	if focused is LineEdit:
		return "LineEdit:" + focused.text
	return "" if focused == null else focused.get_class()


# {
#   責務: [_finish: 観測結果を出力し、成功時は0、失敗時は1で終了します]
#   処理: [1: 結果をBase64のJSONで出力して終了します]
#   引数: [result: ok・checkpoints・失敗時のerrorを持つ結果（Dictionary）]
#   戻り値: [result: なし]
# }
func _finish(result: Dictionary) -> void:
	print("KADOKA_E2E_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0 if result.get("ok", false) else 1)
