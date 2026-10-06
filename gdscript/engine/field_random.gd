# {
#   責務: [field_random: Runtime random adapter. Tests inject the same rolls/order into Python and Godot.]
#   フィールド: [generator: generator]
# }
extends RefCounted
## Runtime random adapter. Tests inject the same rolls/order into Python and Godot.

var generator := RandomNumberGenerator.new()


# {
#   責務: [_init: フィールド・乱数が利用する初期状態と依存を設定する]
#   処理: [1: フィールド・乱数が利用する初期状態と依存を設定する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init() -> void:
	generator.randomize()


# {
#   責務: [randrange: フィールド・乱数のrandrangeを求める]
#   処理: [1: フィールド・乱数のrandrangeを求める]
#   引数: [limit: limit（int）]
#   戻り値: [result: フィールド・乱数のrandrangeを求めるための結果（int）]
# }
func randrange(limit: int) -> int:
	return generator.randi_range(0, limit - 1)


# {
#   責務: [shuffle: フィールド・乱数の並べ替えを求める]
#   処理: [1: フィールド・乱数の並べ替えを求める]
#   引数: [values: 値一覧（Array）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func shuffle(values: Array) -> void:
	for index in range(values.size() - 1, 0, -1):
		var other := randrange(index + 1)
		var saved: Variant = values[index]
		values[index] = values[other]
		values[other] = saved
