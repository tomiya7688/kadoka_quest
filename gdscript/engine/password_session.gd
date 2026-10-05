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


func _init(value: String = PASSWORD, keys: String = KANA_KEYS) -> void:
	secret = value
	maximum_length = secret.length()
	for index in keys.length():
		allowed_characters[keys[index]] = true


func open() -> void:
	input_text = ""
	message = prompt
	active = true


func append(character: String) -> bool:
	if not active or not allowed_characters.has(character) or input_text.length() >= maximum_length:
		return false
	input_text += character
	message = ""
	return true


func backspace() -> bool:
	if not active:
		return false
	var changed := not input_text.is_empty()
	input_text = input_text.left(maxi(0, input_text.length() - 1))
	message = ""
	return changed


func submit() -> bool:
	if not active or input_text != secret:
		message = failure_message
		return false
	active = false
	message = ""
	return true


func cancel() -> void:
	input_text = ""
	message = ""
	active = false


func snapshot() -> Dictionary:
	return {"input_text": input_text, "message": message, "active": active, "maximum_length": maximum_length}
