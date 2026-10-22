# {
#   責務: [password_session: Bounded transient password state. No UI, clock, files or acquisition effects.]
#   フィールド: [
#     secret: secret（String）
#     allowed_characters: allowed・characters（Dictionary）
#     maximum_length: maximum・length（int）
#     prompt: prompt
#     failure_message: failure・message
#     input_text: 入力・文字列
#     message: message
#     active: active
#   ]
# }
extends RefCounted
## Bounded transient password state. No UI, clock, files or acquisition effects.

const PASSWORD := "へいわなすみか"
const KANA_KEYS := "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
var secret: String
var allowed_characters: Dictionary = {}
var maximum_length: int
var prompt := "7文字のあいことばを入力してください。"
var failure_message := "あいことばが違います。"
var input_text := ""
var message := ""
var active := false


# {
#   責務: [_init: 暗号・セッションが利用する初期状態と依存を設定する]
#   処理: [1: 暗号・セッションが利用する初期状態と依存を設定する]
#   引数: [
#     value: 値（String）
#     keys: キー一覧（String）
#   ]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(value: String = PASSWORD, keys: String = KANA_KEYS) -> void:
	secret = value
	maximum_length = secret.length()
	for index in keys.length():
		allowed_characters[keys[index]] = true


# {
#   責務: [open: 暗号・セッションを開く]
#   処理: [1: 暗号・セッションを開く]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func open() -> void:
	input_text = ""
	message = prompt
	active = true


# {
#   責務: [append: 暗号・セッションを末尾へ追加する]
#   処理: [1: 暗号・セッションを末尾へ追加する]
#   引数: [character: キャラクター（String）]
#   戻り値: [result: 暗号・セッションを末尾へ追加するための結果（bool）]
# }
func append(character: String) -> bool:
	if not active or not allowed_characters.has(character) or input_text.length() >= maximum_length:
		return false
	input_text += character
	message = ""
	return true


# {
#   責務: [backspace: 暗号・セッションのbackspaceを求める]
#   処理: [1: 暗号・セッションのbackspaceを求める]
#   引数: []
#   戻り値: [result: 暗号・セッションのbackspaceを求めるための結果（bool）]
# }
func backspace() -> bool:
	if not active:
		return false
	var changed := not input_text.is_empty()
	input_text = input_text.left(maxi(0, input_text.length() - 1))
	message = ""
	return changed


# {
#   責務: [submit: 暗号・セッションを確定する]
#   処理: [1: 暗号・セッションを確定する]
#   引数: []
#   戻り値: [result: 暗号・セッションを確定するための結果（bool）]
# }
func submit() -> bool:
	if not active or input_text != secret:
		message = failure_message
		return false
	active = false
	message = ""
	return true


# {
#   責務: [cancel: 暗号・セッションのcancelを求める]
#   処理: [1: 暗号・セッションのcancelを求める]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func cancel() -> void:
	input_text = ""
	message = ""
	active = false


# {
#   責務: [snapshot: 暗号・セッションを状態を複製する]
#   処理: [1: 暗号・セッションを状態を複製する]
#   引数: []
#   戻り値: [result: 暗号・セッションを状態を複製するための結果（Dictionary）]
# }
func snapshot() -> Dictionary:
	return {"input_text": input_text, "message": message, "active": active, "maximum_length": maximum_length}
