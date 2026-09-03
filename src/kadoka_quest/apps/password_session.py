from __future__ import annotations

from collections.abc import Iterable


class PasswordSession:
    """Owns one bounded virtual-keyboard password-entry session."""

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

    def open(self) -> None:
        self.input_text = ""
        self.message = self.prompt
        self.active = True

    def append(self, character: str) -> bool:
        value = str(character)
        if not self.active or value not in self.allowed_characters or len(self.input_text) >= self.maximum_length:
            return False
        self.input_text += value
        self.message = ""
        return True

    def backspace(self) -> bool:
        if not self.active:
            return False
        changed = bool(self.input_text)
        self.input_text = self.input_text[:-1]
        self.message = ""
        return changed

    def submit(self) -> bool:
        if not self.active or self.input_text != self.secret:
            self.message = self.failure_message
            return False
        self.active = False
        self.message = ""
        return True

    def cancel(self) -> None:
        self.input_text = ""
        self.message = ""
        self.active = False
