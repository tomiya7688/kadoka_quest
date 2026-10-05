extends RefCounted
## Keyboard adaptation and repeat timing, never gameplay rules.

const REPEAT_SECONDS := 0.14
var held := Vector2i.ZERO
var elapsed := 0.0


func reset() -> void:
	held = Vector2i.ZERO
	elapsed = 0.0


func movement_step(delta: float) -> Vector2i:
	var requested := _pressed_direction()
	if requested != held:
		held = requested
		elapsed = 0.0
		return requested
	if held == Vector2i.ZERO:
		return Vector2i.ZERO
	elapsed += delta
	if elapsed >= REPEAT_SECONDS:
		elapsed = fmod(elapsed, REPEAT_SECONDS)
		return held
	return Vector2i.ZERO


static func _pressed_direction() -> Vector2i:
	if Input.is_physical_key_pressed(KEY_LEFT) or Input.is_physical_key_pressed(KEY_A):
		return Vector2i.LEFT
	if Input.is_physical_key_pressed(KEY_RIGHT) or Input.is_physical_key_pressed(KEY_D):
		return Vector2i.RIGHT
	if Input.is_physical_key_pressed(KEY_UP) or Input.is_physical_key_pressed(KEY_W):
		return Vector2i.UP
	if Input.is_physical_key_pressed(KEY_DOWN) or Input.is_physical_key_pressed(KEY_S):
		return Vector2i.DOWN
	return Vector2i.ZERO
