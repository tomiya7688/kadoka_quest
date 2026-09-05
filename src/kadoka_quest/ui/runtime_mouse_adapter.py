from __future__ import annotations

from collections.abc import Iterable, Mapping

import pygame


class RuntimeMouseAdapter:
    """Translates screen-specific left clicks into semantic command requests."""

    def __init__(
        self,
        password_keys: Iterable[tuple[str, pygame.Rect]],
        password_actions: Mapping[str, pygame.Rect],
        battle_buttons: Iterable[tuple[str, pygame.Rect]],
    ) -> None:
        self.password_keys = [(character, rect.copy()) for character, rect in password_keys]
        self.password_actions = {action: rect.copy() for action, rect in password_actions.items()}
        self.battle_buttons = [(command, rect.copy()) for command, rect in battle_buttons]

    def translate(
        self,
        event: pygame.event.Event,
        mode: str,
        *,
        battle_enabled: bool = True,
    ) -> list[dict]:
        if event.type != pygame.MOUSEBUTTONDOWN or getattr(event, "button", None) != 1:
            return []
        position = tuple(event.pos)
        if mode == "password":
            return self._password_click(position)
        if mode == "battle" and battle_enabled:
            return self._battle_click(position)
        return []

    def _password_click(self, position: tuple[int, int]) -> list[dict]:
        for character, rect in self.password_keys:
            if rect.collidepoint(position):
                return [self._command("password", "append", character=character)]
        for action in ("backspace", "submit", "cancel"):
            rect = self.password_actions.get(action)
            if rect is not None and rect.collidepoint(position):
                return [self._command("password", action)]
        return []

    def _battle_click(self, position: tuple[int, int]) -> list[dict]:
        for command, rect in self.battle_buttons:
            if rect.collidepoint(position):
                return [self._command("battle", "execute", command=command)]
        return []

    @staticmethod
    def _command(target: str, action: str, **payload: object) -> dict:
        return {"kind": "command", "target": target, "action": action, "payload": payload}
