# {
#   責務: [password_session: 暗号・セッションの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Iterable


# {
#   責務: [PasswordSession: Owns one bounded virtual-keyboard password-entry session.]
#   フィールド: [
#     secret: secret
#     allowed_characters: allowed・characters
#     maximum_length: maximum・length
#     prompt: prompt
#     failure_message: failure・message
#     input_text: 入力・文字列
#     message: message
#     active: active
#   ]
# }
class PasswordSession:
    """Owns one bounded virtual-keyboard password-entry session."""

    # {
    #   責務: [__init__: 暗号・セッションが利用する初期状態と依存を設定する]
    #   処理: [1: 暗号・セッションが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     secret: secret（str）
    #     allowed_characters: allowed・characters（Iterable[str]）
    #     prompt: prompt（str）
    #     failure_message: failure・message（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(
        self,
        secret: str,
        allowed_characters: Iterable[str],
        *,
        prompt: str = "7文字のあいことばを入力してください。",
        failure_message: str = "あいことばが違います。",
    ) -> None:
        self.secret = str(secret)
        self.allowed_characters = frozenset(str(value) for value in allowed_characters)
        self.maximum_length = len(self.secret)
        self.prompt = str(prompt)
        self.failure_message = str(failure_message)
        self.input_text = ""
        self.message = ""
        self.active = False

    # {
    #   責務: [open: 暗号・セッションを開く]
    #   処理: [1: 暗号・セッションを開く]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def open(self) -> None:
        self.input_text = ""
        self.message = self.prompt
        self.active = True

    # {
    #   責務: [append: 暗号・セッションを末尾へ追加する]
    #   処理: [1: 暗号・セッションを末尾へ追加する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     character: キャラクター（str）
    #   ]
    #   戻り値: [result: 暗号・セッションを末尾へ追加するための結果（bool）]
    # }
    def append(self, character: str) -> bool:
        value = str(character)
        if not self.active or value not in self.allowed_characters or len(self.input_text) >= self.maximum_length:
            return False
        self.input_text += value
        self.message = ""
        return True

    # {
    #   責務: [backspace: 暗号・セッションのbackspaceを求める]
    #   処理: [1: 暗号・セッションのbackspaceを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 暗号・セッションのbackspaceを求めるための結果（bool）]
    # }
    def backspace(self) -> bool:
        if not self.active:
            return False
        changed = bool(self.input_text)
        self.input_text = self.input_text[:-1]
        self.message = ""
        return changed

    # {
    #   責務: [submit: 暗号・セッションを確定する]
    #   処理: [1: 暗号・セッションを確定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 暗号・セッションを確定するための結果（bool）]
    # }
    def submit(self) -> bool:
        if not self.active or self.input_text != self.secret:
            self.message = self.failure_message
            return False
        self.active = False
        self.message = ""
        return True

    # {
    #   責務: [cancel: 暗号・セッションのcancelを求める]
    #   処理: [1: 暗号・セッションのcancelを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def cancel(self) -> None:
        self.input_text = ""
        self.message = ""
        self.active = False
