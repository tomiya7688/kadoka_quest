# {
#   責務: [title_application: タイトル画面の選択を受け、セーブ名を保存先で検査してから、そのセーブ名のフィールド画面へ一度だけ切り替えます]
#   フィールド: [
#     store: セーブ名の検査と保存済みセーブの列挙に使う保存先（RefCounted）
#     view: タイトル画面の表示部品（Control）
#     profile_names: 最後に列挙した保存済みセーブ名の一覧（Array）
#     field: 切替後のフィールド画面。切替前はnullで、二回目の切替要求を拒否する目印にもなります（Control）
#   ]
# }
extends Control

const SaveStore = preload("res://data/field_save_store.gd")
const PixelTheme = preload("res://ui/pixel_theme.gd")
const TitleView = preload("res://ui/title_view.gd")
const FieldScene = preload("res://scenes/field.tscn")
var store: RefCounted
var view: Control
var profile_names: Array = []
var field: Control


# {
#   責務: [_ready: 自動実行用のセーブ名指定がある場合はフィールドへ直行し、ない場合はタイトル画面と保存済みセーブ一覧を表示します]
#   処理: [
#     1: KADOKA_GDSCRIPT_SAVE_NAMEが設定されていれば、タイトルを表示せずにフィールドへ切り替えます
#     2: タイトル画面の作成と操作要求の接続を_build_viewへ委譲します
#     3: 環境変数が指す保存先からセーブ一覧を読み、画面へ反映します
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _ready() -> void:
	# 既存の検査と自動実行は環境変数でセーブ名を固定するため、従来どおりフィールドから始めます。
	var configured_name := OS.get_environment("KADOKA_GDSCRIPT_SAVE_NAME")
	if not configured_name.is_empty():
		start_field.call_deferred(configured_name)
		return
	_build_view()
	store = SaveStore.new(SaveStore.configured_root())
	refresh_profiles()


# {
#   責務: [_build_view: 共通の白黒テーマでタイトル画面を作り、再開・新規開始・終了の要求をこのアプリケーションへ接続します]
#   処理: [
#     1: ウィンドウの最小寸法と、ピクセルフォント・最近傍補間のテーマを設定します
#     2: タイトル画面を追加し、三つの要求シグナルを接続します
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _build_view() -> void:
	# 起動直後の画面でも、整数倍率の基準画面よりウィンドウが小さくならないようにします。
	get_window().min_size = Vector2i(960, 540)
	theme = PixelTheme.create()
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	view = TitleView.new()
	add_child(view)
	view.continue_requested.connect(continue_game)
	view.new_requested.connect(start_new_game)
	view.quit_requested.connect(func(): get_tree().quit())


# {
#   責務: [refresh_profiles: 保存先から保存済みセーブ名を読み直し、タイトル画面の一覧と案内へ反映します]
#   処理: [
#     1: 保存先へセーブの列挙を要求します
#     2: 成功時は一覧を表示し、除外したフォルダがあれば件数を案内します。失敗時は空の一覧と理由を表示します
#   ]
#   引数: []
#   戻り値: [result: 列挙に成功した場合はtrue]
# }
func refresh_profiles() -> bool:
	var result: Dictionary = store.list_profiles()
	profile_names = result.get("names", []).duplicate() if result["ok"] else []
	view.show_profiles(profile_names)
	if not result["ok"]:
		view.show_message("セーブ一覧を読めません: " + str(result["message"]))
	elif not result["warnings"].is_empty():
		view.show_message("開けないセーブフォルダが%d件あります。一覧には表示しません。" % result["warnings"].size())
	return result["ok"]


# {
#   責務: [continue_game: 一覧で選ばれたセーブ名を保存先で再検査し、開ける場合だけフィールドへ切り替えます]
#   処理: [
#     1: 一覧に存在しリンク検査を通り、state.jsonが残っているセーブ名だけを受け付けます
#     2: 拒否時は一覧を読み直してから理由を表示し、受付時はフィールドへ切り替えます
#   ]
#   引数: [name: タイトル画面で選ばれたセーブ名]
#   戻り値: [result: フィールドへ切り替えた場合はtrue]
# }
func continue_game(name: String) -> bool:
	if field != null:
		return false
	# 一覧表示後にフォルダが消えたりリンクへ置き換わったりした場合も、開く直前に確認します。
	var profile: Dictionary = store.resolve_profile(name)
	if name not in profile_names or not profile["ok"] or not FileAccess.file_exists(profile["path"].path_join("state.json")):
		# 一覧の読み直しは操作説明を表示し直すため、拒否理由はその後に表示します。
		refresh_profiles()
		view.show_message("この冒険は開けません: " + str(profile.get("message", "セーブが見つかりません。")))
		return false
	start_field(profile["name"])
	return true


# {
#   責務: [start_new_game: 入力されたセーブ名を検査し、既存のセーブフォルダと重ならない場合だけ新しい冒険としてフィールドへ切り替えます]
#   処理: [
#     1: 保存先と同じ規則でセーブ名を検査し、40文字を超える名前を拒否します
#     2: 同じ名前のフォルダがある場合は、既存の個体や所持品を新しい冒険へ混ぜないよう拒否します
#     3: 新しいセーブ名でフィールドへ切り替えます。セーブフォルダは最初の保存時に作られます
#   ]
#   引数: [name: タイトル画面で入力されたセーブ名]
#   戻り値: [result: フィールドへ切り替えた場合はtrue]
# }
func start_new_game(name: String) -> bool:
	if field != null:
		return false
	var profile: Dictionary = store.resolve_profile(name)
	if not profile["ok"]:
		view.show_message(str(profile["message"]))
		return false
	# 保存先は40文字を超える名前を切り詰めるため、入力と異なる名前で始めないよう拒否します。
	if profile["name"] != name:
		view.show_message("セーブ名は40文字以内にしてください。")
		return false
	# state.jsonがないフォルダにも個体や所持品が残っている場合があり、Windowsでは大文字小文字違いも同じフォルダです。
	if DirAccess.dir_exists_absolute(profile["path"]):
		view.show_message("同じ名前のセーブフォルダがあります。「つづきから」で選ぶか、別の名前を入力してください。")
		return false
	start_field(profile["name"])
	return true


# {
#   責務: [start_field: 指定したセーブ名のフィールド画面を一度だけ作って現在の画面に設定し、タイトル画面を破棄します]
#   処理: [
#     1: すでに切り替えている場合は何もしません
#     2: フィールド画面を生成し、画面の準備前にセーブ名を渡します
#     3: SceneTreeの現在の画面をフィールドへ切り替え、タイトル画面を解放します
#   ]
#   引数: [name: フィールド画面が読み書きするセーブ名]
#   戻り値: [result: なし]
# }
func start_field(name: String) -> void:
	# 同じフレームにEnterとボタン押下が重なっても、フィールドを二つ作りません。
	if field != null:
		return
	# フィールドの_readyがセーブ名を使うため、ツリーへ追加する前に設定します。
	field = FieldScene.instantiate()
	field.profile_name = name
	get_tree().root.add_child(field)
	get_tree().current_scene = field
	queue_free()


# {
#   責務: [_input: タイトル画面のEscを表示部品へ渡し、セーブ一覧やセーブ名入力から最初の操作枠へ戻します]
#   処理: [1: 表示部品が処理したキーだけを消費済みにします]
#   引数: [event: 画面へ届いた入力]
#   戻り値: [result: なし]
# }
func _input(event: InputEvent) -> void:
	if view != null and event is InputEventKey and view.handle_key(event):
		get_viewport().set_input_as_handled()
