# {
#   責務: [field_chrome: 探索画面の最小HUD・メニュー・会話表示を組み立て、操作要求をシグナルで返します。]
#   フィールド: [
#     title: 現在の地名を表示するLabel
#     status: 保存結果や操作結果を表示するLabel
#     menu: 探索を一時停止する操作パネル
#     dialogue: 会話本文を独立表示するパネル
#     dialogue_choices: 会話の選択肢ボタンを縦に並べる列
#     dismiss_button: 選択肢がない会話を閉じるボタン
#     menu_button: メニューを開閉する操作ボタン
#     NOTICE_SECONDS: 結果欄の通知を表示し続ける秒数
#     notice_text: 秒数を数え始めた時点の結果欄の文字列
#     notice_remaining: 結果欄の通知を消すまでの残り秒数
#   ]
# }
extends Control

const Style = preload("res://ui/pixel_theme.gd")
const NOTICE_SECONDS := 6.0
signal roster_requested
signal save_requested
signal load_requested
signal choice_selected(index: int)
var title: Label
var status: Label
var menu: PanelContainer
var dialogue: PanelContainer
var menu_button: Button
var dialogue_name: Label
var dialogue_text: Label
var dialogue_choices: VBoxContainer
var dismiss_button: Button
var menu_actions: Array[Control] = []
var notice_text := ""
var notice_remaining := 0.0

# {
#   責務: [_process: 結果欄の通知を表示してからの経過時間を進めます。]
#   処理: [1: 描画フレームの経過秒数をadvance_noticeへ渡します。]
#   引数: [delta: 前のフレームからの経過秒数]
#   戻り値: [result: なし]
# }
func _process(delta: float) -> void:
	advance_notice(delta)

# {
#   責務: [advance_notice: 結果欄の通知を一時表示にし、決めた秒数を過ぎたら空にして、世界の表示面積を広げます。]
#   処理: [
#     1: 結果欄の文字列が前回と違えば、新しい通知として残り秒数を設定し直します
#     2: 文字列が空でなければ経過秒数を引き、残りがなくなったら文字列を空にします
#   ]
#   引数: [delta: 進める秒数]
#   戻り値: [result: なし]
# }
func advance_notice(delta: float) -> void:
	if status.text != notice_text:
		notice_text = status.text
		notice_remaining = NOTICE_SECONDS
	if notice_text.is_empty():
		return
	notice_remaining -= delta
	if notice_remaining <= 0.0:
		status.text = ""
		notice_text = ""

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
	dialogue_choices = VBoxContainer.new()
	column.add_child(dialogue_choices)
	dismiss_button = Style.button("とじる  [Esc]")
	dismiss_button.pressed.connect(close_dialogue)
	column.add_child(dismiss_button)
	dialogue.hide()

# {
#   責務: [show_dialogue: 会話結果の話者・本文・選択肢を専用パネルへ表示します。]
#   処理: [
#     1: 話者名が空なら話者名の行を隠し、本文を表示して本文スクロールを先頭へ戻します
#     2: 前回の選択肢を取り除き、選択肢があれば順に並べて先頭へフォーカスし、閉じるボタンを隠します
#   ]
#   引数: [
#     speaker: 会話結果の話者名。空の文字列なら話者名を表示しません
#     text: 会話結果の本文
#     choices: 利用者へ表示する選択肢の文字列の並び。省略または空なら閉じるボタンだけを表示します
#   ]
#   戻り値: [result: なし]
# }
func show_dialogue(speaker: String, text: String, choices: Array = []) -> void:
	dialogue_name.text = speaker
	dialogue_name.visible = not speaker.is_empty()
	dialogue_text.text = text
	(dialogue.get_child(0) as ScrollContainer).scroll_vertical = 0
	for old in dialogue_choices.get_children():
		dialogue_choices.remove_child(old)
		old.queue_free()
	var buttons: Array[Control] = []
	for index in choices.size():
		var button := Style.button(str(choices[index]))
		button.pressed.connect(_select_choice.bind(index))
		dialogue_choices.add_child(button)
		buttons.append(button)
	dismiss_button.visible = buttons.is_empty()
	dialogue.show()
	if not buttons.is_empty():
		Style.cycle_focus(buttons)
		buttons[0].grab_focus.call_deferred()

# {
#   責務: [_select_choice: 会話の選択肢が選ばれたことを通知し、会話パネルを閉じます。]
#   処理: [1: 選ばれた順番をchoice_selectedで通知してから、会話パネルを隠します。]
#   引数: [index: 選ばれた選択肢の0始まりの順番]
#   戻り値: [result: なし]
# }
func _select_choice(index: int) -> void:
	choice_selected.emit(index)
	close_dialogue()

# {
#   責務: [close_dialogue: 会話パネルを隠し、会話中に持っていた入力フォーカスを解放します。]
#   処理: [1: 現在のControlフォーカスを解放して会話パネルを隠します。]
#   引数: []
#   戻り値: [result: なし]
# }
func close_dialogue() -> void:
	get_viewport().gui_release_focus()
	dialogue.hide()

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
