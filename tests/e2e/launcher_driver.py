"""Exercise the real Player launcher with SDL events and a captured handoff."""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
import shutil
from unittest.mock import patch

import pygame

from kadoka_quest.apps import launcher
from kadoka_quest.paths import PROJECT_ROOT, SAVEDATA_ROOT


def post_input(value: dict) -> None:
    kind = value["kind"]
    if kind == "click":
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=tuple(value["pos"])))
    elif kind == "key":
        pygame.event.post(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.key.key_code(value["key"]), unicode=str(value.get("unicode", "")),
        ))
    elif kind == "text":
        for character in value["text"]:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=character))
    else:
        raise ValueError(f"Unsupported launcher input: {kind}")


class LauncherFrames:
    """Queue the next input batch at tick(), without sleeping or fake callbacks."""

    def __init__(self, batches: list[list[dict]], clock) -> None:
        self.batches = iter(batches)
        self.clock = clock
        self.count = 0

    def tick(self, _fps: int) -> int:
        self.count += 1
        if self.count > 100:
            raise ValueError("Launcher frame budget exceeded")
        self.clock.advance(16)
        batch = next(self.batches, None)
        if batch is None:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        else:
            for value in batch:
                post_input(value)
        return 16


def drive_launcher(batches: list[list[dict]], clock, sandbox: Path) -> dict:
    # Stage the actual source wrapper, so optional legacy-save lookup stays
    # inside a private project instead of reading the user's old saves/.
    project = sandbox / "launcher-project"
    project.mkdir(exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "game.py", project / "game.py")
    frames = LauncherFrames(batches, clock)
    controls, launches = [], []
    real_button = launcher.Button

    def observe_button(rect, label, action, **kwargs):
        controls.append(str(label))
        return real_button(rect, label, action, **kwargs)

    def capture_launch(command, *, cwd, env):
        profile = Path(env["KADOKA_SAVE_DIR"]).resolve()
        if not profile.is_relative_to(SAVEDATA_ROOT.resolve()):
            raise ValueError("Launcher handoff escaped the isolated savedata root")
        if command != [launcher.sys.executable, str(project / "game.py")]:
            raise ValueError(f"Unexpected Player launch target: {command}")
        if Path(cwd) != project:
            raise ValueError("Unexpected Player launch directory")
        # Observe an OS handoff, not a fake successful game process. The caller
        # creates production stores/runtime with exactly this selected root.
        launches.append(profile)

    pygame.event.clear()
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(launcher, "PROJECT_ROOT", project))
            stack.enter_context(patch.object(launcher, "Button", observe_button))
            stack.enter_context(patch.object(pygame.time, "Clock", lambda: frames))
            stack.enter_context(patch.object(launcher.subprocess, "Popen", capture_launch))
            launcher.main()
    finally:
        pygame.init()
        pygame.display.set_mode((1, 1))
    if len(launches) > 1:
        raise ValueError("Use one Player launch per launcher step")
    return {
        "controls": controls, "frames": frames.count,
        "save_root": str(launches[0]) if launches else None,
        "launched_name": launches[0].name if launches else None,
        "entrypoint": "kadoka_quest.apps.launcher.main",
    }
