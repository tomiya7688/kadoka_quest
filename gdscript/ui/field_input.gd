# {
#   責務: [field_input: 物理方向キーを探索の単発移動と長押し反復へ変換し、モーダル操作中の長押しを探索へ持ち越しません。]
#   フィールド: [
#     held: 探索で直前に受け取った移動方向
#     elapsed: 同じ方向を保持してからの反復待ち時間（秒）
#     awaiting_release: モーダル終了時の方向キーがすべて離されるまで移動を抑止する状態
#   ]
# }
extends RefCounted
## Keyboard adaptation and repeat timing, never gameplay rules.

const REPEAT_SECONDS := 0.14
var held := Vector2i.ZERO
var elapsed := 0.0
var awaiting_release := false


# {
#   責務: [reset: 探索の移動方向と反復待ち時間を消去し、方向キーの解除待ちは保持します。]
#   処理: [1: 次回の新規方向入力を単発移動として扱えるよう反復状態を初期化します。]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func reset() -> void:
	# 画面操作から何度リセットされても、モーダル終了時の解除待ちは破棄しません。
	held = Vector2i.ZERO
	elapsed = 0.0


# {
#   責務: [suppress_held_movement: モーダル終了時に押されている方向キーを、全方向キーの解除まで探索へ渡しません。]
#   処理: [
#     1: 探索の反復状態を消去します。
#     2: 方向キーが押下中の場合だけ解除待ちを開始します。
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func suppress_held_movement() -> void:
	# ボタン移動に使った長押しを、新しい探索移動と誤認しないための境界です。
	reset()
	awaiting_release = _pressed_direction() != Vector2i.ZERO


# {
#   責務: [observe_key_release: 全方向キーを離した入力イベントで解除待ちを終え、同一フレーム内の押し直しを受け付けます。]
#   処理: [1: キー解放時に方向キーが一つも押されていない場合だけ、モーダル終了時の移動抑止を解除します。]
#   引数: [event: Godotが物理キー状態へ反映済みのキーボードイベント]
#   戻り値: [result: なし]
# }
func observe_key_release(event: InputEventKey) -> void:
	# フレーム更新だけの観測では、短時間の解放・再押下を取りこぼすため入力順に記録します。
	if awaiting_release and not event.pressed and _pressed_direction() == Vector2i.ZERO:
		awaiting_release = false


# {
#   責務: [movement_step: 解除待ちでない方向入力を、初回または反復間隔ごとに一歩分の方向へ変換します。]
#   処理: [
#     1: モーダル終了時の長押しが残っている間は移動を返しません。
#     2: 新しい方向は即時に返し、同じ方向は反復間隔に達したときだけ返します。
#   ]
#   引数: [delta: 前回の探索更新からの経過秒数]
#   戻り値: [result: 今回移動する方向。移動しない場合はVector2i.ZERO]
# }
func movement_step(delta: float) -> Vector2i:
	var requested := _pressed_direction()
	# すべての方向キーを離してから、次の押下を探索入力として受け付けます。
	if awaiting_release:
		awaiting_release = requested != Vector2i.ZERO
		return Vector2i.ZERO
	# 押し始めと方向転換は反復待ち時間に依存させません。
	if requested != held:
		held = requested
		elapsed = 0.0
		return requested
	if held == Vector2i.ZERO:
		return Vector2i.ZERO
	# フレーム時間の余りを維持し、長押し時の反復間隔を一定にします。
	elapsed += delta
	if elapsed >= REPEAT_SECONDS:
		elapsed = fmod(elapsed, REPEAT_SECONDS)
		return held
	return Vector2i.ZERO


# {
#   責務: [_pressed_direction: 矢印キーまたはWASDの物理押下から、優先順位が左・右・上・下の一方向を返します。]
#   処理: [1: 複数方向を押している場合も、最初に該当する一方向だけを選びます。]
#   引数: []
#   戻り値: [result: 押下中の方向。方向キーが押されていない場合はVector2i.ZERO]
# }
static func _pressed_direction() -> Vector2i:
	# 斜め移動を生成せず、フィールドの一歩単位の操作へ合わせます。
	if Input.is_physical_key_pressed(KEY_LEFT) or Input.is_physical_key_pressed(KEY_A):
		return Vector2i.LEFT
	if Input.is_physical_key_pressed(KEY_RIGHT) or Input.is_physical_key_pressed(KEY_D):
		return Vector2i.RIGHT
	if Input.is_physical_key_pressed(KEY_UP) or Input.is_physical_key_pressed(KEY_W):
		return Vector2i.UP
	if Input.is_physical_key_pressed(KEY_DOWN) or Input.is_physical_key_pressed(KEY_S):
		return Vector2i.DOWN
	return Vector2i.ZERO
