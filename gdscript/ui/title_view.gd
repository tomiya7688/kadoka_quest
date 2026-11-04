# {
#   責務: [title_view: タイトル画面の「つづきから・はじめから・おわる」とセーブ選択・セーブ名入力を白黒の枠で表示し、利用者の選択をシグナルで返します。保存やセーブ名の検査は行いません]
#   フィールド: [
#     logo: ゲーム名を48pxで表示するLabel
#     home: つづきから・はじめから・おわるを並べる最初の操作枠
#     profiles: 保存済みセーブの一覧と決定ボタンを持つ操作枠
#     new_game: 新しいセーブ名を入力する操作枠
#     message: 選択結果や拒否理由を補助色で表示するLabel
#     continue_button: セーブ一覧を開くボタン。セーブがない場合は無効です
#     new_button: セーブ名入力を開くボタン
#     quit_button: ゲームの終了を要求するボタン
#     profile_list: 保存済みセーブ名を選ぶItemList
#     name_input: 新しいセーブ名を入力するLineEdit
#     start_button: 一覧で選んだセーブで冒険を再開するボタン
#     create_button: 入力したセーブ名で新しい冒険を始めるボタン
#     page: 表示中の操作枠の名前。home・profiles・newのいずれかです
#   ]
# }
extends Control

const Style = preload("res://ui/pixel_theme.gd")
signal continue_requested(name: String)
signal new_requested(name: String)
signal quit_requested
var logo: Label
var home: PanelContainer
var profiles: PanelContainer
var new_game: PanelContainer
var message: Label
var continue_button: Button
var new_button: Button
var quit_button: Button
var profile_list: ItemList
var name_input: LineEdit
var start_button: Button
var create_button: Button
var page := "home"


# {
#   責務: [_ready: ゲーム名・三つの操作枠・結果欄を960×540の基準画面へ配置し、最初の操作枠を表示します]
#   処理: [
#     1: 画面全体へ広げ、ゲーム名と補助の見出しを上部中央へ置きます
#     2: 最初の操作枠・セーブ一覧・セーブ名入力の三枠を同じ位置へ作ります
#     3: 結果欄を下部へ置き、最初の操作枠を表示します
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	# ゲーム名は16pxの字形の3倍で描き、ドット絵と同じ格子に揃えます。
	logo = Label.new()
	logo.text = "KADOKA QUEST"
	logo.add_theme_font_size_override("font_size", 48)
	logo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(logo)
	logo.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	logo.offset_left = -300
	logo.offset_right = 300
	logo.offset_top = 64
	logo.offset_bottom = 128
	var subtitle := Label.new()
	subtitle.text = "かどかクエスト"
	subtitle.add_theme_color_override("font_color", Style.MUTED)
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(subtitle)
	subtitle.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	subtitle.offset_left = -300
	subtitle.offset_right = 300
	subtitle.offset_top = 132
	subtitle.offset_bottom = 156
	_build_home()
	_build_profiles()
	_build_new_game()
	# 結果欄は操作説明と拒否理由だけを表示し、保存先のパスなど開発用情報は出しません。
	message = Label.new()
	message.add_theme_color_override("font_color", Style.MUTED)
	message.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	message.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(message)
	message.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	message.offset_left = 40
	message.offset_right = -40
	message.offset_top = -64
	message.offset_bottom = -16
	open_page("home")


# {
#   責務: [_build_home: つづきから・はじめから・おわるの三つのボタンを持つ最初の操作枠を作ります]
#   処理: [1: 中央の枠へ三つのボタンを縦に並べ、押下時の画面切替と終了要求を接続します]
#   引数: []
#   戻り値: [result: なし]
# }
func _build_home() -> void:
	home = _centered_panel(360, 0)
	var column := VBoxContainer.new()
	home.add_child(column)
	continue_button = Style.button("つづきから")
	continue_button.pressed.connect(func(): open_page("profiles"))
	new_button = Style.button("はじめから")
	new_button.pressed.connect(func(): open_page("new"))
	quit_button = Style.button("おわる")
	quit_button.pressed.connect(func(): quit_requested.emit())
	for button in [continue_button, new_button, quit_button]:
		column.add_child(button)
	Style.cycle_focus([continue_button, new_button, quit_button])


# {
#   責務: [_build_profiles: 保存済みセーブの一覧と「この冒険をはじめる・もどる」を持つ操作枠を作ります]
#   処理: [
#     1: 見出し・セーブ一覧・二つのボタンを縦に並べます
#     2: 一覧のダブルクリックまたはEnterと決定ボタンを、選択中のセーブでの開始要求へ接続します
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _build_profiles() -> void:
	profiles = _centered_panel(520, 260)
	var column := VBoxContainer.new()
	profiles.add_child(column)
	var heading := Label.new()
	heading.text = "つづける冒険を選んでください"
	column.add_child(heading)
	profile_list = ItemList.new()
	profile_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	profile_list.item_activated.connect(func(_index: int): request_continue())
	column.add_child(profile_list)
	var row := HBoxContainer.new()
	column.add_child(row)
	start_button = Style.button("この冒険をはじめる")
	start_button.pressed.connect(request_continue)
	var back := Style.button("もどる  [Esc]")
	back.pressed.connect(func(): open_page("home"))
	for button in [start_button, back]:
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(button)
	Style.cycle_focus([profile_list, start_button, back])


# {
#   責務: [_build_new_game: 新しいセーブ名の入力欄と「はじめる・もどる」を持つ操作枠を作ります]
#   処理: [
#     1: 見出し・名前入力欄・二つのボタンを縦に並べます
#     2: 入力欄のEnterと決定ボタンを、入力したセーブ名での新規開始要求へ接続します
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _build_new_game() -> void:
	new_game = _centered_panel(520, 0)
	var column := VBoxContainer.new()
	new_game.add_child(column)
	var heading := Label.new()
	heading.text = "新しい冒険のセーブ名を入力してください"
	column.add_child(heading)
	name_input = LineEdit.new()
	name_input.placeholder_text = "セーブ名（40文字まで）"
	name_input.max_length = 40
	name_input.text_submitted.connect(func(_text: String): request_new())
	column.add_child(name_input)
	var row := HBoxContainer.new()
	column.add_child(row)
	create_button = Style.button("はじめる")
	create_button.pressed.connect(request_new)
	var back := Style.button("もどる  [Esc]")
	back.pressed.connect(func(): open_page("home"))
	for button in [create_button, back]:
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(button)
	Style.cycle_focus([name_input, create_button, back])


# {
#   責務: [_centered_panel: ゲーム名の下へ、指定した幅の黒地白枠の操作枠を中央揃えで作ります]
#   処理: [1: PanelContainerを中央基準で配置し、高さ0の指定では内容に合わせて下へ伸ばします]
#   引数: [
#     width: 操作枠の幅の画素数
#     height: 操作枠の高さの画素数。0の場合は中身の最小の高さに合わせます
#   ]
#   戻り値: [result: 親へ追加済みで非表示の操作枠（PanelContainer）]
# }
func _centered_panel(width: int, height: int) -> PanelContainer:
	# 枠の上端を見出しの下へ固定し、高さの違う三枠でもゲーム名と重ならないようにします。
	var panel := PanelContainer.new()
	add_child(panel)
	panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	panel.grow_vertical = Control.GROW_DIRECTION_END
	panel.offset_left = -width / 2
	panel.offset_right = width / 2
	panel.offset_top = 188
	panel.offset_bottom = 188 + height
	panel.hide()
	return panel


# {
#   責務: [show_profiles: 呼出元が読んだセーブ名を一覧へ表示し、セーブがない場合は「つづきから」を無効にします]
#   処理: [
#     1: セーブ名を一覧へ入れ直し、先頭を選択します
#     2: セーブの有無で「つづきから」の有効状態を切り替え、表示中の枠のフォーカスを選び直します
#   ]
#   引数: [names: 保存先から読んだセーブ名の一覧（Array）]
#   戻り値: [result: なし]
# }
func show_profiles(names: Array) -> void:
	profile_list.clear()
	for name in names:
		profile_list.add_item(str(name))
	if profile_list.item_count > 0:
		profile_list.select(0)
	# 開けるセーブがないときは、押しても空の一覧になる操作を選ばせません。
	continue_button.disabled = profile_list.item_count == 0
	continue_button.focus_mode = Control.FOCUS_NONE if continue_button.disabled else Control.FOCUS_ALL
	open_page(page)


# {
#   責務: [show_message: 選択結果やセーブ名の拒否理由を結果欄へ表示します]
#   処理: [1: 与えられた説明文を結果欄へ設定します]
#   引数: [text: 利用者へ表示する説明文]
#   戻り値: [result: なし]
# }
func show_message(text: String) -> void:
	message.text = text


# {
#   責務: [open_page: home・profiles・newのうち指定した操作枠だけを表示し、その枠の最初の操作へフォーカスを移します]
#   処理: [
#     1: 指定外の操作枠を隠し、指定した枠を表示します
#     2: 枠ごとの最初の操作へフォーカスし、操作説明を結果欄へ表示します
#   ]
#   引数: [name: 表示する操作枠の名前。home・profiles・newのいずれかです]
#   戻り値: [result: なし]
# }
func open_page(name: String) -> void:
	page = name
	home.visible = name == "home"
	profiles.visible = name == "profiles"
	new_game.visible = name == "new"
	match name:
		"home":
			# セーブがなければ「はじめから」を最初の選択にし、無効なボタンへフォーカスを置きません。
			var first: Button = new_button if continue_button.disabled else continue_button
			first.grab_focus.call_deferred()
			show_message("矢印 / Tab で選び、Enter で決定してください。")
		"profiles":
			profile_list.grab_focus.call_deferred()
			show_message("矢印で冒険を選び、Enter で再開してください。Esc でもどります。")
		"new":
			name_input.clear()
			name_input.grab_focus.call_deferred()
			show_message("セーブ名を入力して Enter を押してください。Esc でもどります。")


# {
#   責務: [request_continue: 一覧で選択中のセーブ名で冒険の再開を要求します]
#   処理: [1: 選択がない場合は理由を表示し、選択がある場合だけセーブ名を通知します]
#   引数: []
#   戻り値: [result: なし]
# }
func request_continue() -> void:
	var selected := profile_list.get_selected_items()
	if selected.is_empty():
		show_message("つづける冒険を選んでください。")
		return
	continue_requested.emit(profile_list.get_item_text(selected[0]))


# {
#   責務: [request_new: 入力欄のセーブ名で新しい冒険の開始を要求します。名前の検査は呼出元が行います]
#   処理: [1: 入力欄の文字列をそのまま通知します]
#   引数: []
#   戻り値: [result: なし]
# }
func request_new() -> void:
	# 前後の空白も含めて通知し、保存先の名前検査で理由付きの拒否を表示させます。
	new_requested.emit(name_input.text)


# {
#   責務: [handle_key: タイトル画面のEscで、セーブ一覧とセーブ名入力から最初の操作枠へ戻ります]
#   処理: [1: 押されたEscだけを処理し、最初の操作枠以外を表示中ならhomeへ切り替えます]
#   引数: [event: タイトル画面へ届いたキー入力（InputEventKey）]
#   戻り値: [result: このキーをタイトル画面で処理した場合はtrue]
# }
func handle_key(event: InputEventKey) -> bool:
	if not event.pressed or event.echo or event.physical_keycode != KEY_ESCAPE or page == "home":
		return false
	open_page("home")
	return true
