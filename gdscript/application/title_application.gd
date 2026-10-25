# {
#   責務: [title_application: タイトル画面の選択を受け、セーブ名を保存先で検査してから、そのセーブ名のフィールド画面へ切り替えます]
#   フィールド: [
#     store: セーブ名の検査と保存済みセーブの列挙に使う保存先（RefCounted）
#     view: タイトル画面の表示部品（Control）
#     profile_names: 最後に列挙した保存済みセーブ名の一覧（Array）
#     field: 切替後のフィールド画面。切替前はnullです（Control）
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
#     2: 共通テーマのタイトル画面を作り、操作要求を接続します
#     3: 保存先からセーブ一覧を読み、画面へ反映します
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
	var save_root := OS.get_environment("KADOKA_GDSCRIPT_SAVE_ROOT")
	store = SaveStore.new("user://savedata" if save_root.is_empty() else save_root)
	refresh_profiles()


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
#   処理: [1: 一覧に存在しリンク検査を通るセーブ名だけを受け付け、拒否時は理由を表示します]
#   引数: [name: タイトル画面で選ばれたセーブ名]
#   戻り値: [result: フィールドへ切り替えた場合はtrue]
# }
func continue_game(name: String) -> bool:
	# 一覧表示後にフォルダが消えたりリンクへ置き換わったりした場合も、開く直前に確認します。
	var profile: Dictionary = store.resolve_profile(name)
	if name not in profile_names or not profile["ok"] or not FileAccess.file_exists(profile["path"].path_join("state.json")):
		view.show_message("この冒険は開けません: " + str(profile.get("message", "セーブが見つかりません。")))
		refresh_profiles()
		return false
	start_field(profile["name"])
	return true


# {
#   責務: [start_new_game: 入力されたセーブ名を検査し、既存のセーブと重ならない場合だけ新しい冒険としてフィールドへ切り替えます]
#   処理: [
#     1: 保存先と同じ規則でセーブ名を検査します
#     2: 保存済みの名前と同じ場合は、上書きを防ぐため拒否します
#     3: 新しいセーブ名でフィールドへ切り替えます。セーブフォルダは最初の保存時に作られます
#   ]
#   引数: [name: タイトル画面で入力されたセーブ名]
#   戻り値: [result: フィールドへ切り替えた場合はtrue]
# }
func start_new_game(name: String) -> bool:
	var profile: Dictionary = store.resolve_profile(name)
	if not profile["ok"]:
		view.show_message(str(profile["message"]))
		return false
	# 40文字を超える名前は保存先が切り詰めるため、切り詰め後の名前で重複を確認します。
	if profile["name"] != name:
		view.show_message("セーブ名は40文字以内にしてください。")
		return false
	if FileAccess.file_exists(profile["path"].path_join("state.json")):
		view.show_message("同じ名前のセーブがあります。「つづきから」で選ぶか、別の名前を入力してください。")
		return false
	start_field(profile["name"])
	return true


# {
#   責務: [start_field: 指定したセーブ名のフィールド画面を作って現在の画面に設定し、タイトル画面を破棄します]
#   処理: [
#     1: フィールド画面を生成し、画面の準備前にセーブ名を渡します
#     2: SceneTreeの現在の画面をフィールドへ切り替え、タイトル画面を解放します
#   ]
#   引数: [name: フィールド画面が読み書きするセーブ名]
#   戻り値: [result: なし]
# }
func start_field(name: String) -> void:
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
