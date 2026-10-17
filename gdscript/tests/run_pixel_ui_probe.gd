# {
#   責務: [run_pixel_ui_probe: 実セーブを使わずに白黒UIの配置・フォーカス・スクロール・入力要求を実Godotで検証します。]
#   フィールド: [failures: 失敗した期待動作の説明一覧]
# }
extends SceneTree

const Style = preload("res://ui/pixel_theme.gd")
var failures: PackedStringArray = []

# {
#   責務: [_initialize: UI検査をSceneTreeの初期化後へ予約します。]
#   処理: [1: 検査本体を遅延実行します。]
#   引数: []
#   戻り値: [result: なし]
# }
func _initialize() -> void:
	_run.call_deferred()

# {
#   責務: [_run: 最小画面での共通テーマと各モーダルの操作契約を検証します。]
#   処理: [
#     1: 表示だけの試験用ツリーを作ります
#     2: テーマ・配列選択・かな入力を確認します
#     3: 結果を出力して終了します。
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _run() -> void:
	root.size = Vector2i(960, 540)
	var surface := Control.new()
	root.add_child(surface)
	surface.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	surface.theme = Style.create()
	var chrome = load("res://ui/field_chrome.gd").new()
	surface.add_child(chrome)
	await process_frame
	# テーマの値とControlの実際の配置を確認し、画像検査や実GUI成功とは区別します。
	_check(root.min_size == Vector2i(960, 540), "Windowの最小寸法プロパティが960×540")
	var panel: StyleBoxFlat = surface.theme.get_stylebox("panel", "PanelContainer")
	_check(panel.bg_color == Style.INK and panel.border_color == Style.PAPER, "白黒の矩形枠")
	_check(panel.border_width_left == 3 and panel.corner_radius_top_left == 0, "3px枠と角丸なし")
	_check(surface.theme.default_font.antialiasing == TextServer.FONT_ANTIALIASING_NONE, "日本語フォントの平滑化なし")
	chrome.toggle_menu()
	await process_frame
	_check(chrome.menu.visible and chrome.menu_actions[0].has_focus(), "メニューを開くと最初の操作を選択")
	_check(chrome.menu.get_global_rect().end.x <= 960, "メニューの右端が画面内")
	chrome.close_menu()
	_check(not chrome.menu.visible and root.gui_get_focus_owner() == null, "メニューを閉じるとフォーカスを解放")
	chrome.show_dialogue("町のひと", "こんにちは。".repeat(80))
	await process_frame
	var dialogue_scroll := chrome.dialogue.get_child(0) as ScrollContainer
	_check(dialogue_scroll.get_v_scroll_bar().max_value > dialogue_scroll.size.y, "長い会話をスクロール可能")
	chrome.dialogue.hide()
	await _check_roster(surface)
	await _check_party(surface)
	await _check_presets(surface)
	await _check_password(surface)
	print("KADOKA_PIXEL_UI_RESULT=" + JSON.stringify({"ok": failures.is_empty(), "failures": failures}))
	print("KADOKA_CONTRACT_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({"ok": failures.is_empty(), "failures": failures})))
	surface.queue_free()
	await process_frame
	quit(0 if failures.is_empty() else 1)

# {
#   責務: [_check_roster: 空の台帳から編成ボタンへフォーカスでき、Tabを阻害しないことを確認します。]
#   処理: [
#     1: 新規プロフィールの台帳を表示します
#     2: キー処理と画面内配置を確認します。
#   ]
#   引数: [surface: 試験用UIの親Control]
#   戻り値: [result: なし]
# }
func _check_roster(surface: Control) -> void:
	var view = load("res://ui/roster_view.gd").new()
	surface.add_child(view)
	Style.place_modal(view)
	view.show_snapshot({"records": {}, "party": [], "new_profile": true})
	view.edit_button.grab_focus()
	await process_frame
	_check(view.edit_button.has_focus(), "台帳の編成ボタンへキーボードフォーカス")
	_check(not view.handle_key(KEY_TAB) and view.handle_key(KEY_END), "台帳はTabを部品へ渡してEndをスクロールへ使用")
	_check(view.size.x <= 960 and view.size.y <= 540, "台帳モーダルが最小画面内")
	view.queue_free()
	await process_frame

# {
#   責務: [_check_party: 多数の仲間のページ選択と割当要求が既存の識別子を維持することを確認します。]
#   処理: [
#     1: 80体の表示専用レコードを生成します
#     2: Endによる末尾選択とシグナルを確認します。
#   ]
#   引数: [surface: 試験用UIの親Control]
#   戻り値: [result: なし]
# }
func _check_party(surface: Control) -> void:
	var view = load("res://ui/party_view.gd").new()
	surface.add_child(view)
	Style.place_modal(view)
	var records := {}
	for index in 80:
		records["member_%d" % index] = {"monster": {"name": "なかま%d" % index, "level": 1}, "species": {"display_name": "かどか"}}
	var party := []
	for index in 4:
		party.append({"id": null, "record": null})
	view.show_snapshot({"dirty": false, "party": party, "records": records, "warnings": []}, true)
	await process_frame
	view.owned.grab_focus()
	_check(view.handle_navigation(KEY_END), "仲間一覧の末尾選択を処理")
	_check(view.owned.get_selected_items()[0] == 79, "仲間80体目までキーボードで到達")
	var assignment := []
	view.assigned.connect(func(slot: int, id: Variant): assignment.append([slot, id]))
	view.assign_selected()
	_check(assignment == [[0, "member_79"]], "編成枠と仲間IDの割当シグナルを維持")
	_check(view.presets_button.focus_mode == Control.FOCUS_ALL, "プリセットもTab巡回の対象")
	view.queue_free()
	await process_frame

# {
#   責務: [_check_presets: プリセットの末尾選択が名前入力のカーソル操作と混ざらないことを確認します。]
#   処理: [
#     1: 60件の一覧を表示します
#     2: End選択と名前入力中のキー委譲を確認します。
#   ]
#   引数: [surface: 試験用UIの親Control]
#   戻り値: [result: なし]
# }
func _check_presets(surface: Control) -> void:
	var view = load("res://ui/party_preset_view.gd").new()
	surface.add_child(view)
	Style.place_modal(view)
	var entries := []
	for index in 60:
		entries.append({"name": "編成%d" % index, "filename": "preset_%d.json" % index, "members": [null, null, null, null]})
	view.show_catalog({"ok": true, "entries": entries, "warnings": []}, true)
	await process_frame
	view.handle_navigation(KEY_END)
	_check(view.listing.get_selected_items()[0] == 59, "プリセット60件目まで到達")
	view.name_input.grab_focus()
	_check(not view.handle_navigation(KEY_HOME), "名前入力のHomeキーを一覧が横取りしない")
	view.queue_free()
	await process_frame

# {
#   責務: [_check_password: かなボタンのEnterを確定処理が横取りせず、長いキー配列をスクロールできることを確認します。]
#   処理: [
#     1: 正規のかなキー配列を表示します
#     2: フォーカス中のEnter委譲と閉じる操作を確認します。
#   ]
#   引数: [surface: 試験用UIの親Control]
#   戻り値: [result: なし]
# }
func _check_password(surface: Control) -> void:
	var view = load("res://ui/password_view.gd").new()
	surface.add_child(view)
	Style.place_modal(view)
	view.configure_keys(load("res://engine/password_session.gd").KANA_KEYS)
	view.show_snapshot({"input_text": "あいう", "message": "7文字を選んでください。"}, true)
	await process_frame
	var key := InputEventKey.new()
	key.pressed = true
	key.physical_keycode = KEY_ENTER
	view.buttons["あ"].grab_focus()
	_check(not view.handle_key(key), "かなボタンのEnterはボタンへ委譲")
	view.text_input.grab_focus()
	var requests := []
	view.submit_requested.connect(func(): requests.append("submit"))
	_check(view.handle_key(key) and requests == ["submit"], "入力欄のEnterは確定要求を1回通知")
	var scroll := view.get_child(0) as ScrollContainer
	_check(scroll.follow_focus, "かなキーのフォーカスにスクロールが追従")
	_check(view.slots[2].text == "う" and view.slots[3].text == "＿", "7文字枠に入力状態を表示")
	view.queue_free()
	await process_frame

# {
#   責務: [_check: 失敗した期待動作だけを検査結果へ記録します。]
#   処理: [1: 偽の条件に対応する説明を失敗一覧へ追加します。]
#   引数: [
#     condition: 期待動作が成立したか
#     description: 成立すべき操作と表示の説明
#   ]
#   戻り値: [result: なし]
# }
func _check(condition: bool, description: String) -> void:
	if not condition:
		failures.append(description)
