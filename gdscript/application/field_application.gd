# {
#   責務: [field_application: Composition/coordinator: data -> session -> renderer. Source-only prototype.]
#   フィールド: [
#     repository: データ取得先（RefCounted）
#     session: セッション
#     keyboard: keyboard
#     images: 画像一覧（RefCounted）
#     blocks: ブロック定義（Dictionary）
#     view: 表示（Control）
#     title: title（Label）
#     status: 状態異常（Label）
#     persistence: persistence（RefCounted）
#     profile_name: プロファイル・名前
#     owned_snapshot: owned・独立した状態の写し（Dictionary）
#     roster_view: 所有個体台帳・表示（PanelContainer）
#     party_view: パーティ・表示（PanelContainer）
#     party_editor: パーティ・editor（RefCounted）
#     presets: プリセット一覧（RefCounted）
#     preset_view: プリセット・表示（PanelContainer）
#     password_session: 暗号・セッション
#     password_view: 暗号・表示（PanelContainer）
#     password_outcome: 暗号・結果（Dictionary）
#     ghost_acquisition: おばけ・acquisition（RefCounted）
#     ghost_request: おばけ・要求（Dictionary）
#     acquisition_result: acquisition・処理結果（Dictionary）
#     church_registration: 教会・registration（RefCounted）
#     church_result: 教会・処理結果（Dictionary）
#   ]
# }
extends Control
## Composition/coordinator: data -> session -> renderer. Source-only prototype.

const Repository = preload("res://data/content_repository.gd")
const Session = preload("res://application/field_session.gd")
const Keyboard = preload("res://ui/field_input.gd")
const Images = preload("res://ui/content_images.gd")
const FieldView = preload("res://ui/field_view.gd")
const RosterView = preload("res://ui/roster_view.gd")
const PartyView = preload("res://ui/party_view.gd")
const PartyEditor = preload("res://application/party_editor.gd")
const PresetService = preload("res://application/party_presets.gd")
const PresetView = preload("res://ui/party_preset_view.gd")
const SaveStore = preload("res://data/field_save_store.gd")
const Persistence = preload("res://application/field_persistence.gd")
const PasswordSession = preload("res://engine/password_session.gd")
const PasswordView = preload("res://ui/password_view.gd")
const GhostAcquisition = preload("res://application/ghost_acquisition.gd")
const ChurchRegistration = preload("res://application/church_registration.gd")
const PixelTheme = preload("res://ui/pixel_theme.gd")
const FieldChrome = preload("res://ui/field_chrome.gd")
signal password_finished(result: Dictionary)

var repository: RefCounted
var session = Session.new()
var keyboard = Keyboard.new()
var images: RefCounted
var blocks: Dictionary = {}
var view: Control
var title: Label
var status: Label
var persistence: RefCounted
var profile_name := "default"
var owned_snapshot: Dictionary = {"records": {}, "party": [], "warnings": []}
var roster_view: PanelContainer
var party_view: PanelContainer
var party_editor: RefCounted
var presets: RefCounted
var preset_view: PanelContainer
var password_session = PasswordSession.new()
var password_view: PanelContainer
var password_outcome: Dictionary = {}
var ghost_acquisition: RefCounted
var ghost_request: Dictionary = {}
var acquisition_result: Dictionary = {}
var church_registration: RefCounted
var church_result: Dictionary = {}
var chrome: Control


# {
#   責務: [_ready: 正規コンテンツを読み込み、フィールド画面とプロフィール保存サービスを初期化します。]
#   処理: [1: 正規コンテンツを読み込み、フィールド画面とプロフィール保存サービスを初期化します。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func _ready() -> void:
	var content_root := OS.get_environment("KADOKA_CONTENT_ROOT")
	if content_root.is_empty():
		content_root = ProjectSettings.globalize_path("res://").trim_suffix("/").get_base_dir()
	repository = Repository.new(content_root)
	images = Images.new(content_root)
	_create_ui()
	blocks = repository.load_blocks()
	if blocks.is_empty():
		status.text = repository.last_error
		set_process(false)
		return
	images.species["hero"] = repository.load_species("hero")
	open_map("starting_town")
	_setup_persistence()


# {
#   責務: [_create_ui: 共通テーマと表示専用HUDを組み立て、各画面の操作要求を既存のアプリケーション入口へ接続します。]
#   処理: [
#     1: フィールドとHUDを配置します
#     2: 各モーダルを画面内へ配置し、操作シグナルを接続します。
#   ]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _create_ui() -> void:
	# 表示資源を共用し、画像や文字を整数倍率で描画します。
	theme = PixelTheme.create()
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	view = FieldView.new()
	view.clip_contents = true
	view.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(view)
	view.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	view.offset_top = 48
	view.offset_bottom = -44
	chrome = FieldChrome.new()
	add_child(chrome)
	title = chrome.title
	status = chrome.status
	chrome.roster_requested.connect(open_owned_roster)
	chrome.save_requested.connect(save_current_position)
	chrome.load_requested.connect(load_saved_position)
	# モーダルの保存・選択契約は既存のシグナル接続を維持します。
	roster_view = RosterView.new()
	add_child(roster_view)
	PixelTheme.place_modal(roster_view)
	roster_view.hide()
	roster_view.edit_requested.connect(begin_party_edit)
	roster_view.close_requested.connect(roster_view.hide)
	party_view = PartyView.new()
	add_child(party_view)
	PixelTheme.place_modal(party_view)
	party_view.hide()
	party_view.assigned.connect(assign_party_member)
	party_view.save_requested.connect(save_party_edit)
	party_view.cancel_requested.connect(cancel_party_edit)
	party_view.presets_requested.connect(open_party_presets)
	preset_view = PresetView.new()
	add_child(preset_view)
	PixelTheme.place_modal(preset_view)
	preset_view.hide()
	preset_view.save_requested.connect(save_party_preset)
	preset_view.load_requested.connect(load_party_preset)
	preset_view.refresh_requested.connect(refresh_party_presets)
	preset_view.back_requested.connect(close_party_presets)
	password_view = PasswordView.new()
	add_child(password_view)
	PixelTheme.place_modal(password_view)
	password_view.hide()
	password_view.configure_keys(PasswordSession.KANA_KEYS)
	password_view.character_requested.connect(append_password)
	password_view.backspace_requested.connect(backspace_password)
	password_view.submit_requested.connect(submit_password)
	password_view.cancel_requested.connect(cancel_password)
	for modal in [roster_view, party_view, preset_view, password_view]:
		modal.visibility_changed.connect(_sync_modal_controls)
	chrome.menu.visibility_changed.connect(_sync_modal_controls)
	_sync_modal_controls()


# {
#   責務: [_sync_modal_controls: モーダル中の背面メニュー操作と、モーダル終了時の方向キー持ち越しを防ぎます。]
#   処理: [
#     1: 台帳・編成・プリセット・暗号の表示中は背面メニューボタンを無効にします。
#     2: 全モーダルが閉じたとき、押下中の方向キーを探索へ渡さないよう入力アダプターへ通知します。
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _sync_modal_controls() -> void:
	# ヘッダーが見えていても、モーダルの外へ別の画面を重ねないようにします。
	chrome.menu_button.disabled = roster_view.visible or party_view.visible or preset_view.visible or password_view.visible
	# モーダルを閉じるボタンを方向キーで選んでも、探索位置や向きは変更しません。
	if not chrome.menu_button.disabled and not chrome.menu.visible:
		keyboard.suppress_held_movement()


# {
#   責務: [open_map: 指定IDのマップを読込先へ要求し、取得に成功した場合だけ探索セッションを切り替えます。]
#   処理: [1: 指定IDのマップを読込先へ要求し、取得に成功した場合だけ探索セッションを切り替えます。]
#   引数: [
#     map_id: 読込を要求する正規マップID
#     entry: マップ内の開始位置と向き
#   ]
#   戻り値: [result: マップの読込と切替に成功した場合はtrue]
# }
func open_map(map_id: String, entry: Dictionary = {}) -> bool:
	var world: Dictionary = repository.load_map(map_id)
	if world.is_empty():
		status.text = repository.last_error
		return false
	_enter_world(world, entry)
	return true


# {
#   責務: [_enter_world: 読込済みのマップと入口をセッションへ渡し、表示する種族画像を準備します。]
#   処理: [1: 読込済みのマップと入口をセッションへ渡し、表示する種族画像を準備します。]
#   引数: [
#     world: 読込済みのマップ定義
#     entry: 開始位置と向き
#   ]
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func _enter_world(world: Dictionary, entry: Dictionary) -> void:
	# 前のマップの会話を移動先へ残さず、データ側の開始位置だけを採用します。
	chrome.dialogue.hide()
	session.enter_map(world, blocks, entry)
	session.direction = str(entry.get("direction", session.direction))
	for mob: Dictionary in session.visible_characters:
		var species_id := str(mob["species_id"])
		images.species[species_id] = repository.load_species(species_id)
	_refresh_view()


# {
#   責務: [_setup_persistence: 設定された保存先のサービスを接続し、既存プロフィールの現在地を読み込みます。]
#   処理: [1: 設定された保存先のサービスを接続し、既存プロフィールの現在地を読み込みます。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func _setup_persistence() -> void:
	# タイトル画面のセーブ一覧と同じ保存先を使います。
	var save_root := SaveStore.configured_root()
	var configured_name := OS.get_environment("KADOKA_GDSCRIPT_SAVE_NAME")
	if not configured_name.is_empty():
		profile_name = configured_name
	persistence = Persistence.new(repository, SaveStore.new(save_root), blocks, profile_name)
	ghost_acquisition = GhostAcquisition.new(persistence)
	church_registration = ChurchRegistration.new(persistence)
	password_finished.connect(_on_password_finished)
	presets = PresetService.new(persistence)
	load_saved_position(true)
	_refresh_view()


# {
#   責務: [save_current_position: 探索位置の保存を永続化サービスへ委譲し、保存結果と所有個体一覧を表示へ反映します。]
#   処理: [1: 探索位置の保存を永続化サービスへ委譲し、保存結果と所有個体一覧を表示へ反映します。]
#   引数: []
#   戻り値: [result: 位置保存が成功した場合はtrue]
# }
func save_current_position() -> bool:
	if password_session.active or persistence == null or session.world.is_empty():
		return false
	var result: Dictionary = persistence.save_position(session)
	status.text = "保存しました: " + profile_name if result["ok"] else "保存失敗: " + str(result["message"])
	if result["ok"]:
		_refresh_owned_snapshot()
	return result["ok"]


# {
#   責務: [load_saved_position: 保存サービスが検証した位置・消滅済み固定モブを復元し、所有個体一覧を読み直します。]
#   処理: [1: 保存サービスが検証した位置・消滅済み固定モブを復元し、所有個体一覧を読み直します。]
#   引数: [
#     silent_missing: 初回起動時の保存未作成だけを画面へ通知しない指定
#   ]
#   戻り値: [result: 保存位置の復元が成功した場合はtrue]
# }
func load_saved_position(silent_missing: bool = false) -> bool:
	if password_session.active:
		return false
	var result: Dictionary = persistence.load_position()
	if not result["ok"]:
		if not silent_missing or result["error"] != "not_found":
			status.text = "読込失敗: " + str(result["message"])
		return false
	var entry: Dictionary = result["value"]["player"].duplicate()
	entry["direction"] = entry.get("direction", "front")
	var despawned: Variant = result["value"].get("despawned_fixed_mobs", [])
	session.despawned_fixed_mobs = despawned.duplicate() if despawned is Array else []
	_enter_world(result["world"], entry)
	status.text = "読み込みました: " + profile_name
	_refresh_owned_snapshot()
	return true


# {
#   責務: [_process: モーダルを開いていない間だけセッションの時刻と移動要求を進め、補間位置を描画へ渡します。]
#   処理: [1: モーダルを開いていない間だけセッションの時刻と移動要求を進め、補間位置を描画へ渡します。]
#   引数: [
#     delta: 前回更新からの経過秒数
#   ]
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func _process(delta: float) -> void:
	if session.world.is_empty() or password_session.active or roster_view.visible or party_view.visible or preset_view.visible or chrome.menu.visible:
		return
	session.advance(delta)
	var step: Vector2i = keyboard.movement_step(delta)
	if step != Vector2i.ZERO:
		chrome.dialogue.hide()
		var result: Dictionary = session.move_player(step.x, step.y)
		if result["kind"] == "moved" and result.get("event") != null:
			_handle_event(result["event"])
		_refresh_view()
	elif not session.visible_characters.is_empty():
		_refresh_view()  # Publish interpolated positions; renderer never advances actors.


# {
#   責務: [_unhandled_key_input: 他の表示部品が受け取らなかった探索操作を保存・読込・正面への調査へ振り分けます。]
#   処理: [1: 他の表示部品が受け取らなかった探索操作を保存・読込・正面への調査へ振り分けます。]
#   引数: [
#     event: 表示部品が消費しなかった入力
#   ]
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func _unhandled_key_input(event: InputEvent) -> void:
	if password_session.active or party_view.visible or roster_view.visible or preset_view.visible or chrome.menu.visible:
		return
	if not event is InputEventKey or not event.pressed or event.echo or session.world.is_empty():
		return
	match event.physical_keycode:
		KEY_F5:
			save_current_position()
		KEY_F9:
			load_saved_position()
		KEY_ENTER, KEY_SPACE, KEY_E:
			_handle_interaction(session.interact())
		_:
			return
	get_viewport().set_input_as_handled()


# {
#   責務: [_input: 表示中のモーダルに応じてキャンセルと選択用キーを振り分け、入力の背面への漏れを防ぎます。]
#   処理: [
#     1: キー解放を入力アダプターへ通知し、方向キーの解除待ちを入力順に更新します。
#     2: 表示中のモーダルに応じてキャンセルと選択用キーを振り分け、入力の背面への漏れを防ぎます。
#   ]
#   引数: [
#     event: 画面へ届いたキーボードまたはその他の入力
#   ]
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func _input(event: InputEvent) -> void:
	# GUIが操作を消費する前に、同一フレームの方向キー解放を探索入力へ記録します。
	if event is InputEventKey and not event.pressed:
		keyboard.observe_key_release(event)
	# メニュー表示中は移動と保存ショートカットが背面へ漏れないようにします。
	if chrome.menu.visible:
		if event is InputEventKey and event.pressed:
			if event.physical_keycode == KEY_ESCAPE and not event.echo:
				chrome.close_menu()
				keyboard.reset()
				get_viewport().set_input_as_handled()
			elif event.physical_keycode in [KEY_F5, KEY_F6, KEY_F9]:
				get_viewport().set_input_as_handled()
		return
	if password_session.active:
		if event is InputEventKey and event.pressed and password_view.handle_key(event):
			get_viewport().set_input_as_handled()
		return
	if not event is InputEventKey or not event.pressed or persistence == null:
		return
	if not roster_view.visible and not party_view.visible and not preset_view.visible and event.physical_keycode == KEY_ESCAPE and not event.echo:
		if chrome.dialogue.visible:
			chrome.dialogue.hide()
		else:
			chrome.toggle_menu()
		keyboard.reset()
		get_viewport().set_input_as_handled()
		return
	if preset_view.visible:
		match event.physical_keycode:
			KEY_ESCAPE, KEY_F6:
				close_party_presets()
			KEY_F5:
				refresh_party_presets()
			KEY_F9:
				pass  # Never field-load while a party draft is open.
			KEY_HOME, KEY_END, KEY_PAGEUP, KEY_PAGEDOWN:
				if not preset_view.handle_navigation(event.physical_keycode):
					return
			_:
				return  # Native list/LineEdit/Button keyboard handling, including text.
		get_viewport().set_input_as_handled()
		return
	if party_view.visible:
		if event.echo:
			return
		match event.physical_keycode:
			KEY_ESCAPE, KEY_F6:
				cancel_party_edit()
			KEY_DELETE:
				party_view.clear_selected()
			KEY_P:
				open_party_presets()
			KEY_S:
				if not event.ctrl_pressed:
					return
				save_party_edit()
			KEY_F5, KEY_F9:
				pass  # A draft can only be saved explicitly through the editor.
			KEY_HOME, KEY_END, KEY_PAGEUP, KEY_PAGEDOWN:
				if not party_view.handle_navigation(event.physical_keycode):
					return
			_:
				return  # Native ItemList/Button/Tab keyboard handling.
		get_viewport().set_input_as_handled()
		return
	if event.physical_keycode == KEY_F6 and not event.echo:
		if roster_view.visible:
			roster_view.hide()
		else:
			open_owned_roster()
	elif roster_view.visible:
		if event.physical_keycode == KEY_ESCAPE:
			roster_view.hide()
		elif event.physical_keycode == KEY_E and not event.echo:
			begin_party_edit()
		else:
			if not roster_view.handle_key(event.physical_keycode):
				return
	else:
		return
	get_viewport().set_input_as_handled()


# {
#   責務: [open_owned_roster: 所有個体スナップショットを読み直し、台帳画面の編成ボタンへフォーカスを移します。]
#   処理: [1: 所有個体スナップショットを読み直し、台帳画面の編成ボタンへフォーカスを移します。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func open_owned_roster() -> void:
	if password_session.active:
		return
	chrome.close_menu()
	chrome.dialogue.hide()
	_refresh_owned_snapshot()
	roster_view.show_snapshot(owned_snapshot)
	roster_view.show()
	roster_view.edit_button.grab_focus.call_deferred()


# {
#   責務: [begin_party_edit: 編成サービスが下書きを開始できた場合だけ、台帳から編成画面へ切り替えます。]
#   処理: [1: 編成サービスが下書きを開始できた場合だけ、台帳から編成画面へ切り替えます。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func begin_party_edit() -> void:
	if password_session.active:
		return
	var editor = PartyEditor.new(persistence)
	var result: Dictionary = editor.begin()
	if not result["ok"]:
		status.text = "編成を開けません: " + str(result["message"])
		return
	party_editor = editor
	roster_view.hide()
	party_view.show()
	party_view.show_snapshot(party_editor.snapshot(), true)


# {
#   責務: [assign_party_member: 選択枠と個体IDを編成サービスへ渡し、更新された下書きとエラーを再表示します。]
#   処理: [1: 選択枠と個体IDを編成サービスへ渡し、更新された下書きとエラーを再表示します。]
#   引数: [
#     slot: 変更する編成枠のゼロ始まり番号
#     id: 入れる個体ID。nullは枠から外す要求
#   ]
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func assign_party_member(slot: int, id: Variant) -> void:
	var result: Dictionary = party_editor.assign(slot, id)
	party_view.show_snapshot(party_editor.snapshot())
	party_view.message.text = "未保存の編成です。保存またはキャンセルを選んでください。" if result["ok"] else str(result["message"])


# {
#   責務: [save_party_edit: 編成下書きの保存をサービスへ要求し、成功した場合だけ台帳へ戻ります。]
#   処理: [1: 編成下書きの保存をサービスへ要求し、成功した場合だけ台帳へ戻ります。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func save_party_edit() -> void:
	var result: Dictionary = party_editor.save()
	if not result["ok"]:
		party_view.message.text = "編成保存失敗: " + str(result["message"])
		return
	status.text = result["message"]
	_finish_party_edit()


# {
#   責務: [cancel_party_edit: 編成下書きを保存せずに破棄し、保存済みの台帳へ戻ります。]
#   処理: [1: 編成下書きを保存せずに破棄し、保存済みの台帳へ戻ります。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func cancel_party_edit() -> void:
	status.text = "編成をキャンセルしました。保存データは変更していません。"
	_finish_party_edit()


# {
#   責務: [_finish_party_edit: 編成画面と下書き参照を閉じ、保存済み個体の台帳を再表示します。]
#   処理: [1: 編成画面と下書き参照を閉じ、保存済み個体の台帳を再表示します。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func _finish_party_edit() -> void:
	party_view.hide()
	party_editor = null
	_refresh_owned_snapshot()
	roster_view.show_snapshot(owned_snapshot)
	roster_view.show()


# {
#   責務: [open_party_presets: 編成下書きを保持したままプリセット一覧を開き、保存名入力を空にします。]
#   処理: [1: 編成下書きを保持したままプリセット一覧を開き、保存名入力を空にします。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func open_party_presets() -> void:
	party_view.hide()
	preset_view.show()
	preset_view.name_input.clear()
	preset_view.show_catalog(presets.read_catalog(), true)


# {
#   責務: [refresh_party_presets: プリセットサービスから一覧を再取得して表示を更新します。]
#   処理: [1: プリセットサービスから一覧を再取得して表示を更新します。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func refresh_party_presets() -> void:
	preset_view.show_catalog(presets.read_catalog())


# {
#   責務: [save_party_preset: 現在の編成下書きを別ファイルへ追加保存する要求をサービスへ渡します。]
#   処理: [1: 現在の編成下書きを別ファイルへ追加保存する要求をサービスへ渡します。]
#   引数: [
#     name: 追加保存するプリセットの表示名
#   ]
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func save_party_preset(name: String) -> void:
	var result: Dictionary = presets.save_new(name, party_editor.member_ids())
	if not result["ok"]:
		preset_view.message.text = "追加保存失敗: " + str(result["message"])
		return
	preset_view.show_catalog(presets.read_catalog(), false, result["filename"])
	preset_view.message.text = "追加保存しました: " + result["filename"] + "（現在パーティは未保存）"


# {
#   責務: [load_party_preset: 指定プリセットを編成下書きへ読み込む要求をサービスへ渡し、読込結果を編成画面に表示します。]
#   処理: [1: 指定プリセットを編成下書きへ読み込む要求をサービスへ渡し、読込結果を編成画面に表示します。]
#   引数: [
#     filename: 一覧で選択されたプリセットの保存ファイル名
#   ]
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func load_party_preset(filename: String) -> void:
	var result: Dictionary = presets.load_draft(filename, party_editor)
	if not result["ok"]:
		preset_view.message.text = "読込失敗: " + str(result["message"])
		return
	close_party_presets()
	party_view.show_snapshot(party_editor.snapshot(), true)
	party_view.message.text = "プリセットを下書きへ読み込みました。保存またはキャンセルを選んでください。"
	if not result["warnings"].is_empty():
		party_view.message.text = "注意%d件: %s（下書きのみ変更）" % [result["warnings"].size(), str(result["warnings"][0])]


# {
#   責務: [close_party_presets: プリセット一覧を閉じ、未保存の編成画面の枠選択へ戻します。]
#   処理: [1: プリセット一覧を閉じ、未保存の編成画面の枠選択へ戻します。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func close_party_presets() -> void:
	preset_view.hide()
	party_view.show()
	party_view.slots.grab_focus.call_deferred()


# {
#   責務: [_refresh_owned_snapshot: 保存サービスから取得できた所有個体一覧、または読込失敗の説明を表示用状態へ保持します。]
#   処理: [1: 保存サービスから取得できた所有個体一覧、または読込失敗の説明を表示用状態へ保持します。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func _refresh_owned_snapshot() -> void:
	var result: Dictionary = persistence.read_owned_roster()
	if result["ok"]:
		owned_snapshot = result
	else:
		owned_snapshot = {"records": {}, "party": [], "warnings": [result["message"]],
			"new_profile": result.get("error") == "not_found"}


# {
#   責務: [_handle_interaction: 正面への調査結果をイベント処理または専用会話パネルへ振り分けます。]
#   処理: [1: 正面への調査結果をイベント処理または専用会話パネルへ振り分けます。]
#   引数: [
#     result: 探索セッションの正面調査結果
#   ]
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func _handle_interaction(result: Dictionary) -> void:
	match result["kind"]:
		"event":
			_handle_event(result["event"])
		"dialogue":
			status.text = "%s『%s』" % [result["name"], result["line"]]
			if result.get("unported_despawn", false):
				status.text += " [未移植: 会話後の消滅]"
			chrome.show_dialogue(str(result["name"]), str(result["line"]))
		"dialogue_error":
			status.text = "%s: %s" % [result["name"], result["message"]]
	_refresh_view()  # Publish the NPC's turned direction, not a renderer-side effect.


# {
#   責務: [_handle_event: マップイベントの種類に応じて既存のマップ移動・台帳・暗号・教会の入口を呼びます。]
#   処理: [1: マップイベントの種類に応じて既存のマップ移動・台帳・暗号・教会の入口を呼びます。]
#   引数: [
#     event: 探索セッションが返したマップイベント
#   ]
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func _handle_event(event: Dictionary) -> void:
	if event.is_empty():
		status.text = "目の前に調べるものはありません。"
		return
	if event.get("type") == "transition":
		var target: Dictionary = event.get("target", {})
		if open_map(str(target.get("map_id", "")), target):
			status.text = str(event.get("text", "マップを移動しました。"))
	elif event.get("type") == "message":
		status.text = str(event.get("text", ""))
	elif event.get("type") == "open_manager":
		open_owned_roster()
		status.text = "牧場台帳を開きました。Eで編成、編成のPでプリセット。個体編集・AI変更は未移植です。"
	elif event.get("type") == "password_spring":
		open_password_input()
	elif event.get("type") == "church":
		register_church(event.get("revive"))
	else:
		status.text = "[未移植: %s] %s" % [event.get("type", "event"), event.get("text", "")]


# {
#   責務: [register_church: 他のモーダルが閉じている場合だけ教会サービスへ復活地点登録を要求し、結果を表示します。]
#   処理: [1: 他のモーダルが閉じている場合だけ教会サービスへ復活地点登録を要求し、結果を表示します。]
#   引数: [
#     revive: マップの教会イベントが指定する復活地点
#   ]
#   戻り値: [result: 登録の成功・失敗と利用者向け説明を持つDictionary]
# }
func register_church(revive: Variant) -> Dictionary:
	if password_session.active or roster_view.visible or party_view.visible or preset_view.visible:
		return {"ok": false, "error": "modal_active", "message": "画面を閉じてから教会を調べてください。"}
	church_result = church_registration.register(revive)
	status.text = church_result["message"]
	return church_result


# {
#   責務: [open_password_input: 取得サービスの開始状態を確保し、探索入力をリセットして暗号入力画面を開きます。]
#   処理: [1: 取得サービスの開始状態を確保し、探索入力をリセットして暗号入力画面を開きます。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func open_password_input() -> void:
	chrome.dialogue.hide()
	ghost_request = ghost_acquisition.begin()
	acquisition_result = {}
	password_session.open()
	password_outcome = {}
	keyboard.reset()
	password_view.show_snapshot(password_session.snapshot(), true)


# {
#   責務: [append_password: 確定した文字を暗号セッションへ渡し、7文字枠の表示を更新します。]
#   処理: [1: 確定した文字を暗号セッションへ渡し、7文字枠の表示を更新します。]
#   引数: [
#     character: IMEまたは仮想キーで確定した1文字
#   ]
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func append_password(character: String) -> void:
	password_session.append(character)
	password_view.show_snapshot(password_session.snapshot())


# {
#   責務: [backspace_password: 暗号セッションへ末尾文字の削除を要求し、7文字枠の表示を更新します。]
#   処理: [1: 暗号セッションへ末尾文字の削除を要求し、7文字枠の表示を更新します。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func backspace_password() -> void:
	password_session.backspace()
	password_view.show_snapshot(password_session.snapshot())


# {
#   責務: [submit_password: 暗号セッションへ一致判定を要求し、成功した場合だけ暗号完了シグナルを通知します。]
#   処理: [1: 暗号セッションへ一致判定を要求し、成功した場合だけ暗号完了シグナルを通知します。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func submit_password() -> void:
	if not password_session.submit():
		password_view.show_snapshot(password_session.snapshot())
		return
	_finish_password({"kind": "password_matched"}, "あいことばは一致しました。")


# {
#   責務: [cancel_password: 暗号セッションへ取消を要求し、保存を実行せず入力画面を閉じます。]
#   処理: [1: 暗号セッションへ取消を要求し、保存を実行せず入力画面を閉じます。]
#   引数: []
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func cancel_password() -> void:
	password_session.cancel()
	_finish_password({"kind": "password_cancelled"}, "あいことばの入力をやめました。保存データは変更していません。")


# {
#   責務: [_finish_password: 暗号画面を閉じて移動入力をリセットし、独立コピーの完了結果を通知します。]
#   処理: [1: 暗号画面を閉じて移動入力をリセットし、独立コピーの完了結果を通知します。]
#   引数: [
#     result: 暗号一致または取消の結果
#     text: 暗号画面を閉じた後に表示する結果説明
#   ]
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func _finish_password(result: Dictionary, text: String) -> void:
	password_view.hide()
	keyboard.reset()
	password_outcome = result
	status.text = text
	password_finished.emit(result.duplicate())


# {
#   責務: [_on_password_finished: 暗号が一致した場合だけ取得サービスへ仲間の追加を要求し、保存結果と台帳を更新します。]
#   処理: [1: 暗号が一致した場合だけ取得サービスへ仲間の追加を要求し、保存結果と台帳を更新します。]
#   引数: [
#     result: 暗号完了シグナルが通知した独立コピーの結果
#   ]
#   戻り値: [result: なし。画面状態または要求先を更新します。]
# }
func _on_password_finished(result: Dictionary) -> void:
	if result["kind"] != "password_matched":
		return
	acquisition_result = ghost_acquisition.acquire(ghost_request)
	status.text = acquisition_result["message"]
	_refresh_owned_snapshot()  # Publish verified additions, including explicit partial success.


# {
#   責務: [_refresh_view: 地名と描画用の位置スナップショットを表示層へ渡します。]
#   処理: [
#     1: 変更された地名だけを更新します
#     2: 補間済みのキャラクター位置を描画層へ渡します。
#   ]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _refresh_view() -> void:
	# 補間位置は毎フレーム変わるため、地名の再レイアウトだけを抑止します。
	var map_title := str(session.world.get("display_name", ""))
	if title.text != map_title:
		title.text = map_title
	var warning := "" if session.fixed_mobs.warnings.is_empty() else str(session.fixed_mobs.warnings[0])
	if title.tooltip_text != warning:
		title.tooltip_text = warning
	view.show_snapshot({
		"map": session.world, "blocks": blocks, "characters": session.character_snapshot(),
		"player": {"species_id": "hero", "x": session.x, "y": session.y, "direction": session.direction},
	}, images)
