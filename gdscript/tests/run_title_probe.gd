# {
#   責務: [run_title_probe: 専用の一時保存先で、タイトル画面のセーブ列挙・配置・フォーカス・セーブ名検査・フィールドへの切替を実Godotで検証します]
#   フィールド: [failures: 失敗した期待動作の説明一覧]
# }
extends SceneTree

const SaveStore = preload("res://data/field_save_store.gd")
const TitleScene = preload("res://scenes/title.tscn")
var failures: PackedStringArray = []


# {
#   責務: [_initialize: タイトル検査をSceneTreeの初期化後へ予約します]
#   処理: [1: 検査本体を遅延実行します]
#   引数: []
#   戻り値: [result: なし]
# }
func _initialize() -> void:
	_run.call_deferred()


# {
#   責務: [_run: コマンドライン引数の検査区分に応じて、タイトル画面からの再開または新規開始までを検証して結果を出力します]
#   処理: [
#     1: 保存先の列挙と、保存先がない場合の空一覧を確認します
#     2: タイトル画面を起動し、配置・フォーカス・Escとセーブ名の拒否を確認します
#     3: 検査区分continueは既存セーブで再開し、newは新しいセーブ名で開始して、フィールドへの切替を確認します
#     4: 失敗一覧をBase64のJSONとして出力して終了します
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _run() -> void:
	root.size = Vector2i(960, 540)
	var arguments := OS.get_cmdline_user_args()
	var mode: String = arguments[0] if arguments.size() == 1 else ""
	var save_root := OS.get_environment("KADOKA_GDSCRIPT_SAVE_ROOT")
	_check_store(save_root)
	var title = TitleScene.instantiate()
	root.add_child(title)
	current_scene = title
	await process_frame
	await process_frame
	var view: Control = title.view
	_check(view != null, "セーブ名の環境変数がない起動ではタイトル画面を表示")
	if view == null:
		_finish()
		return
	_check_layout(view)
	await _check_navigation(view)
	_check_rejections(title)
	# 一回の起動で切り替えられるのは一度だけのため、再開と新規開始は別の起動で確認します。
	var started := false
	var expected_name := ""
	if mode == "continue":
		expected_name = "alpha"
		started = title.continue_game(expected_name)
	elif mode == "new":
		expected_name = "新しい冒険"
		started = title.start_new_game(expected_name)
	else:
		_check(false, "検査区分continueまたはnewを指定")
	_check(started, "タイトル画面から%sでフィールドへ切替" % mode)
	# 同じフレームのEnterとボタン押下の重複を想定し、二回目の切替要求を拒否することを確認します。
	_check(not title.continue_game("alpha") and not title.start_new_game("別の冒険"), "切替後の二回目の要求を拒否")
	await process_frame
	await process_frame
	var field_count := 0
	for child in root.get_children():
		if child.name.begins_with("FieldApplication"):
			field_count += 1
	_check(field_count == 1, "フィールド画面は一つだけ")
	var field: Node = current_scene
	_check(field != null and field.name == "FieldApplication", "現在の画面がフィールド画面")
	_check(field != null and field.get("profile_name") == expected_name, "フィールドへ選んだセーブ名を渡す")
	_check(not is_instance_valid(title), "切替後にタイトル画面を解放")
	_finish()


# {
#   責務: [_check_store: 保存先の列挙が開けるセーブだけを自然順で返し、保存先がない場合は空の成功になることを確認します]
#   処理: [
#     1: 試験用に作られた保存先を列挙し、名前・順序・警告件数を確認します
#     2: 存在しない保存先の列挙が空の成功であることを確認します
#   ]
#   引数: [save_root: Pythonテストが作った専用の一時保存先の絶対パス]
#   戻り値: [result: なし]
# }
func _check_store(save_root: String) -> void:
	var listed: Dictionary = SaveStore.new(save_root).list_profiles()
	_check(listed["ok"], "保存先の列挙が成功")
	# ドットで始まるセーブはLinux/macOSで隠しフォルダになりますが、作成できるため一覧にも含めます。
	_check(listed.get("names", []) == [".adventure", "alpha", "冒険2", "冒険10"], "state.jsonのあるセーブだけを、隠しフォルダも含めて自然順で列挙: %s" % str(listed.get("names")))
	_check(listed.get("warnings", []).size() == 1, "40文字を超えるフォルダ名を警告へ残す")
	var missing: Dictionary = SaveStore.new(save_root.path_join("missing_root")).list_profiles()
	_check(missing["ok"] and missing["names"].is_empty(), "保存先がない初回起動は空の一覧")


# {
#   責務: [_check_layout: ゲーム名・操作枠・結果欄が960×540の画面内にあり、共通の白黒テーマを使うことを確認します]
#   処理: [1: 各部品の画面上の矩形と、ゲーム名の文字サイズ・テーマのフォント設定を確認します]
#   引数: [view: タイトル画面の表示部品]
#   戻り値: [result: なし]
# }
func _check_layout(view: Control) -> void:
	var screen := Rect2(Vector2.ZERO, Vector2(960, 540))
	for part: Control in [view.logo, view.home, view.message]:
		_check(screen.encloses(part.get_global_rect()), "%sが960×540の画面内" % part.get_class())
	_check(not view.logo.get_global_rect().intersects(view.home.get_global_rect()), "ゲーム名と操作枠が重ならない")
	_check(view.logo.get_theme_font_size("font_size") == 48, "ゲーム名は16pxの3倍の48px")
	_check(view.get_theme_default_font().antialiasing == TextServer.FONT_ANTIALIASING_NONE, "タイトル画面も平滑化なしのピクセルフォント")
	_check(view.home.visible and not view.profiles.visible and not view.new_game.visible, "起動時は最初の操作枠だけを表示")


# {
#   責務: [_check_navigation: セーブの有無に応じた最初のフォーカス・一覧の内容・Escでの戻りを確認します]
#   処理: [
#     1: セーブがある場合はつづきからへフォーカスし、一覧に列挙順で表示することを確認します
#     2: セーブ一覧でEscを押すと最初の操作枠へ戻ることを確認します
#     3: セーブがない一覧ではつづきからを無効にし、はじめからへフォーカスすることを確認してから元へ戻します
#   ]
#   引数: [view: タイトル画面の表示部品]
#   戻り値: [result: なし]
# }
func _check_navigation(view: Control) -> void:
	await process_frame
	_check(view.continue_button.has_focus(), "セーブがある場合はつづきからを最初に選択")
	_check(view.profile_list.item_count == 4 and view.profile_list.get_item_text(3) == "冒険10", "セーブ一覧を列挙順で表示")
	view.open_page("profiles")
	await process_frame
	_check(view.profiles.visible and view.profile_list.has_focus(), "つづきからでセーブ一覧へフォーカス")
	var escape := InputEventKey.new()
	escape.pressed = true
	escape.physical_keycode = KEY_ESCAPE
	_check(view.handle_key(escape) and view.home.visible, "セーブ一覧のEscで最初の操作枠へ戻る")
	_check(not view.handle_key(escape), "最初の操作枠のEscはタイトル画面で消費しない")
	var names: Array = []
	for index in view.profile_list.item_count:
		names.append(view.profile_list.get_item_text(index))
	view.show_profiles([])
	view.open_page("home")
	await process_frame
	_check(view.continue_button.disabled and view.new_button.has_focus(), "セーブがない場合ははじめからを最初に選択")
	view.show_profiles(names)


# {
#   責務: [_check_rejections: 不正・重複・存在しないセーブ名を、フィールドへ切り替えずに理由付きで拒否することを確認します]
#   処理: [1: 前後の空白・40文字超・既存セーブ名での新規開始と、一覧にないセーブでの再開を要求し、拒否と案内を確認します]
#   引数: [title: タイトル画面のアプリケーション]
#   戻り値: [result: なし]
# }
func _check_rejections(title: Control) -> void:
	for name in [" alpha", "", "a/b", "あ".repeat(41)]:
		_check(not title.start_new_game(name), "不正なセーブ名「%s」を拒否" % name)
	_check(not title.start_new_game("alpha") and title.view.message.text.contains("同じ名前"), "既存セーブ名での新規開始を拒否")
	# state.jsonのないフォルダにも個体などが残る場合があるため、新しい冒険へ取り込まず拒否します。
	_check(not title.start_new_game("フォルダだけ"), "state.jsonのない既存フォルダ名での新規開始を拒否")
	_check(not title.continue_game("missing"), "一覧にないセーブでの再開を拒否")
	_check(title.view.message.text.begins_with("この冒険は開けません"), "再開の拒否理由を一覧の読み直し後も表示")
	_check(title.field == null, "拒否した要求ではフィールドを作らない")


# {
#   責務: [_finish: 失敗一覧を検査結果として出力し、失敗の有無を終了コードへ反映します]
#   処理: [1: 結果をBase64のJSONで出力して終了します]
#   引数: []
#   戻り値: [result: なし]
# }
func _finish() -> void:
	print("KADOKA_CONTRACT_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({"ok": failures.is_empty(), "failures": failures})))
	quit(0 if failures.is_empty() else 1)


# {
#   責務: [_check: 失敗した期待動作だけを検査結果へ記録します]
#   処理: [1: 偽の条件に対応する説明を失敗一覧へ追加します]
#   引数: [
#     condition: 期待動作が成立したか
#     description: 成立すべき操作と表示の説明
#   ]
#   戻り値: [result: なし]
# }
func _check(condition: bool, description: String) -> void:
	if not condition:
		failures.append(description)
