# {
#   責務: [game_navigation: Player画面の一覧選択とデジタルゲームパッド入力を共通化する]
#   フィールド: []
# }
from __future__ import annotations

import pygame


# {
#   責務: [GamepadDevices: Playerウィンドウが使用するゲームパッドの接続オブジェクトを保持する]
#   フィールド: [devices: 接続中のインスタンス識別子とJoystickオブジェクトの対応]
# }
class GamepadDevices:
    # {
    #   責務: [__init__: ゲームパッドの接続保持領域を用意する]
    #   処理: [1: 接続済みデバイスの空の対応表を作る]
    #   引数: [self: 初期化するGamepadDevices]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self) -> None:
        # Joystickの参照を保持し、初期化直後の破棄による入力停止を防ぐ。
        self.devices: dict[int, object] = {}

    # {
    #   責務: [open: Playerウィンドウの起動時に接続済みゲームパッドを初期化する]
    #   処理: [1: 前のウィンドウの参照を外し、現在の接続デバイスを保持する]
    #   引数: [self: デバイスを保持するGamepadDevices]
    #   戻り値: [result: なし（None）]
    # }
    def open(self) -> None:
        # pygame.quit後に残った前回のJoystickを再利用せず、現在の接続を列挙する。
        self.devices.clear()
        pygame.joystick.init()
        for index in range(pygame.joystick.get_count()):
            self.add(index)

    # {
    #   責務: [add: 新しく接続されたゲームパッドを初期化して保持する]
    #   処理: [1: デバイス番号からJoystickを開き、接続識別子で登録する]
    #   引数: [
    #     self: デバイスを保持するGamepadDevices
    #     index: pygameが列挙した接続デバイス番号
    #   ]
    #   戻り値: [result: 接続を初期化できた場合はTrue]
    # }
    def add(self, index: int) -> bool:
        # 列挙直後に抜かれた機器は登録せず、キーボード操作を継続できるようにする。
        try:
            device = pygame.joystick.Joystick(index)
            device.init()
            self.devices[device.get_instance_id()] = device
        except pygame.error:
            return False
        return True

    # {
    #   責務: [remove: 切断されたゲームパッドだけを保持領域から外す]
    #   処理: [1: 接続識別子に対応するJoystickを解放する]
    #   引数: [
    #     self: デバイスを保持するGamepadDevices
    #     instance_id: 切断イベントに含まれる接続識別子
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def remove(self, instance_id: int) -> None:
        # 重複した切断イベントでも他の機器を解放しない。
        device = self.devices.pop(instance_id, None)
        if device is not None:
            device.quit()


_gamepads = GamepadDevices()


# {
#   責務: [initialize_gamepads: Player入力で利用するゲームパッド接続を起動時に保持する]
#   処理: [1: 共有の接続所有者へデバイス初期化を委譲する]
#   引数: []
#   戻り値: [result: なし（None）]
# }
def initialize_gamepads() -> None:
    # 接続所有者を一か所へ集め、タイトルと牧場で別々の接続表を作らない。
    _gamepads.open()


# {
#   責務: [navigation_event: ゲームパッドの方向・決定・取消を画面共通のキーイベントへ変換する]
#   処理: [1: 対応するデジタル入力だけをキーへ変換し、その他のイベントはそのまま返す]
#   引数: [event: pygameから受け取った入力イベント]
#   戻り値: [result: キーへ変換した新しいイベント、または元のイベント]
# }
def navigation_event(event: pygame.event.Event) -> pygame.event.Event:
    # ウィンドウ起動後の抜き差しも接続所有者へ知らせる。
    if event.type == pygame.JOYDEVICEADDED:
        _gamepads.add(event.device_index)
    elif event.type == pygame.JOYDEVICEREMOVED:
        _gamepads.remove(event.instance_id)
    # ゲームパッドのA相当を決定、B相当を取消、左肩ボタンをフォーカス移動へ割り当てる。
    key = None
    if event.type == pygame.JOYBUTTONDOWN:
        key = {0: pygame.K_RETURN, 1: pygame.K_ESCAPE, 4: pygame.K_TAB}.get(event.button)
    elif event.type == pygame.JOYHATMOTION:
        x, y = event.value
        if y:
            key = pygame.K_UP if y > 0 else pygame.K_DOWN
        elif x:
            key = pygame.K_RIGHT if x > 0 else pygame.K_LEFT
    if key is None:
        return event
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", repeat=False)


# {
#   責務: [move_list_selection: キー入力後の一覧選択と、選択行が見える表示位置を計算する]
#   処理: [
#     1: 空一覧と変更後の件数へ選択位置を合わせる
#     2: 方向・ページ・先頭末尾キーに従って選択を変更する
#     3: 選択行が表示範囲内に入るよう開始位置を調整する
#   ]
#   引数: [
#     selected: 現在選択している項目の添字
#     offset: 現在表示している先頭項目の添字
#     total: 一覧の総項目数
#     page: 画面内へ同時に表示する項目数
#     key: pygameのキー定数
#   ]
#   戻り値: [result: 変更後の選択添字と表示開始位置。空一覧では両方0]
# }
def move_list_selection(selected: int, offset: int, total: int, page: int, key: int) -> tuple[int, int]:
    # 空一覧では負の選択を作らず、スクロール状態も初期位置へ戻す。
    count = max(0, int(total))
    visible = max(1, int(page))
    if not count:
        return 0, 0
    index = max(0, min(count - 1, int(selected)))
    moves = {pygame.K_UP: -1, pygame.K_DOWN: 1, pygame.K_PAGEUP: -visible, pygame.K_PAGEDOWN: visible}
    index += moves.get(key, 0)
    if key == pygame.K_HOME:
        index = 0
    elif key == pygame.K_END:
        index = count - 1
    index = max(0, min(count - 1, index))
    # マウスのスクロール後にも、キーで選んだ行が必ず画面内に現れるようにする。
    start = max(0, min(max(0, count - visible), int(offset)))
    if index < start:
        start = index
    elif index >= start + visible:
        start = index - visible + 1
    return index, start
