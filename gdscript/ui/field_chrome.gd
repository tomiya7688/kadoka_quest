# {
#   責務: [field_chrome: 探索画面の最小HUD・メニュー・会話表示を組み立て、操作要求をシグナルで返します。]
#   フィールド: [
#     title: 現在の地名を表示するLabel
#     status: 保存結果や操作結果を表示するLabel
#     menu: 探索を一時停止する操作パネル
#     dialogue: 会話本文を独立表示するパネル
#     menu_button: メニューを開閉する操作ボタン
#   ]
# }
extends Control

const Style = preload("res://ui/pixel_theme.gd")
signal roster_requested
signal save_requested
signal load_requested
var title: Label
var status: Label
var menu: PanelContainer
var dialogue: PanelContainer
var menu_button: Button
var dialogue_name: Label
var dialogue_text: Label
var menu_actions: Array[Control] = []

# {
#   責務: [_ready: フィールドに重ねるHUDと閉じた操作パネルを作ります。]
#   処理: [
#     1: Windowの最小寸法を960×540に設定します。
#     2: ヘッダーと結果欄を配置します。
#     3: メニューと会話パネルを生成します。
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _ready() -> void:
	# 整数倍率の基準画面よりウィンドウが小さくならないよう、Window自体へ制約を設定します。
	get_window().min_size = Vector2i(960, 540)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var header := HBoxContainer.new()
	add_child(header)
	header.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	header.offset_left = 20
	header.offset_top = 8
	header.offset_right = -20
	title = Label.new()
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(title)
	menu_button = Style.button("メニュー  [Esc]")
	menu_button.pressed.connect(toggle_menu)
	header.add_child(menu_button)
	# 結果欄は補助色の2行に収め、座標や開発用情報を常時表示しません。
	status = Label.new()
	add_child(status)
	status.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	status.offset_left = 20
	status.offset_right = -20
	status.offset_top = -44
	status.offset_bottom = -4
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.add_theme_color_override("font_color", Style.MUTED)
	status.text = "矢印 / WASD  移動     Enter / E  調べる"
	_build_menu()
	_build_dialogue()

# {
#   責務: [_build_menu: フィールドの操作を選べるメニューと操作説明を作ります。]
#   処理: [
#     1: 操作要求のボタンを接続します
#     2: メニュー内のTab巡回を閉じます。
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _build_menu() -> void:
	menu = PanelContainer.new()
	add_child(menu)
	Style.place_modal(menu)
	var column := Style.modal_column(menu)
	var heading := Label.new()
	heading.text = "KADOKA QUEST  /  メニュー"
	column.add_child(heading)
	_add_menu_action(column, "なかま・パーティ", func(): close_menu(); roster_requested.emit())
	_add_menu_action(column, "冒険を保存する", func(): close_menu(); save_requested.emit())
	_add_menu_action(column, "保存した冒険を読む", func(): close_menu(); load_requested.emit())
	_add_menu_action(column, "探索へ戻る", close_menu)
	var help := Label.new()
	help.text = "フィールドでは矢印 / WASDで移動し、Enter / Space / Eで正面を調べてください。\nメニューではTab / 矢印で選び、Enterで決定、Escで戻ってください。\nショートカット: F5 保存 / F9 読込 / F6 なかま\nGodot版の戦闘画面・個体編集・AI編集はまだ利用できません。"
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	help.add_theme_color_override("font_color", Style.MUTED)
	column.add_child(help)
	Style.cycle_focus(menu_actions)
	menu.hide()

# {
#   責務: [_add_menu_action: 操作メニューへ意味付きコールバックを持つボタンを追加します。]
#   処理: [1: 表示名と押下要求を設定しフォーカス順へ登録します。]
#   引数: [
#     column: ボタンを追加するメニュー列
#     label: 利用者へ表示する操作名
#     action: 押下時に通知する要求
#   ]
#   戻り値: [result: なし]
# }
func _add_menu_action(column: VBoxContainer, label: String, action: Callable) -> void:
	var button := Style.button(label)
	button.pressed.connect(action)
	column.add_child(button)
	menu_actions.append(button)

# {
#   責務: [_build_dialogue: 話者名と長文スクロールを持つ独立した会話パネルを作ります。]
#   処理: [1: 画面下部へ固定高の会話パネルを配置します。]
#   引数: []
#   戻り値: [result: なし]
# }
func _build_dialogue() -> void:
	dialogue = PanelContainer.new()
	add_child(dialogue)
	# 会話中は同じ本文を下の結果欄へ重複表示しません。
	dialogue.visibility_changed.connect(func(): status.visible = not dialogue.visible)
	dialogue.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	dialogue.offset_left = 20
	dialogue.offset_right = -20
	dialogue.offset_top = -232
	dialogue.offset_bottom = -52
	var column := Style.modal_column(dialogue)
	dialogue_name = Label.new()
	column.add_child(dialogue_name)
	dialogue_text = Label.new()
	dialogue_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(dialogue_text)
	var dismiss := Style.button("とじる  [Esc]")
	dismiss.pressed.connect(dialogue.hide)
	column.add_child(dismiss)
	dialogue.hide()

# {
#   責務: [show_dialogue: 会話結果の話者と本文を専用パネルへ表示します。]
#   処理: [1: 与えられた会話文字列を表示し本文スクロールを先頭へ戻します。]
#   引数: [
#     speaker: 会話結果の話者名
#     text: 会話結果の本文
#   ]
#   戻り値: [result: なし]
# }
func show_dialogue(speaker: String, text: String) -> void:
	dialogue_name.text = speaker
	dialogue_text.text = text
	(dialogue.get_child(0) as ScrollContainer).scroll_vertical = 0
	dialogue.show()

# {
#   責務: [toggle_menu: 操作メニューを開閉し、開いた場合は先頭ボタンへフォーカスします。]
#   処理: [
#     1: 会話表示を閉じます
#     2: メニューの表示状態を切り替えます。
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func toggle_menu() -> void:
	dialogue.hide()
	if menu.visible:
		close_menu()
	else:
		menu.show()
		menu_actions[0].grab_focus.call_deferred()

# {
#   責務: [close_menu: 探索を再開できるようメニューと入力フォーカスを閉じます。]
#   処理: [1: 現在のControlフォーカスを解放しメニューを隠します。]
#   引数: []
#   戻り値: [result: なし]
# }
func close_menu() -> void:
	get_viewport().gui_release_focus()
	menu.hide()
