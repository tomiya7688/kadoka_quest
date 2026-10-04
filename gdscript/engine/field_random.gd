extends RefCounted
## Runtime random adapter. Tests inject the same rolls/order into Python and Godot.

var generator := RandomNumberGenerator.new()


func _init() -> void:
	generator.randomize()


func randrange(limit: int) -> int:
	return generator.randi_range(0, limit - 1)


func shuffle(values: Array) -> void:
	for index in range(values.size() - 1, 0, -1):
		var other := randrange(index + 1)
		var saved: Variant = values[index]
		values[index] = values[other]
		values[other] = saved
