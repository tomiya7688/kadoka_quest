"""Private process entry: validate isolation BEFORE importing game modules."""

from __future__ import annotations

from contextlib import ExitStack
import json
import os
from pathlib import Path
import random
import sys
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from scenario_clock import ScenarioClock


def validate_request(request: dict) -> dict[str, Path]:
    root = Path(request["root"]).resolve()
    paths = {"save": root / "profile", "savedata": root / "savedata", "imports": root / "imports"}
    for name, variable in (("save", "KADOKA_SAVE_DIR"),
                           ("savedata", "KADOKA_SAVEDATA_ROOT"),
                           ("imports", "KADOKA_IMPORT_DIR")):
        expected = paths[name].resolve()
        if not expected.is_relative_to(root) or Path(os.environ[variable]).resolve() != expected:
            raise ValueError(f"Unsafe E2E isolation path: {variable}")
    if isinstance(request["seed"], bool) or not isinstance(request["seed"], int):
        raise ValueError("seed must be an integer")
    if not isinstance(request["steps"], list) or len(request["steps"]) > 1000:
        raise ValueError("steps must be a list of at most 1000 actions")
    return paths


def run(request: dict) -> dict:
    paths = validate_request(request)
    clock = ScenarioClock(request["start_ms"])
    # All path constants now resolve to the sandbox, even if the parent pytest
    # process has already imported production modules with different paths.
    import pygame
    from kadoka_quest.paths import ASSET_ROOT, DATA_ROOT, SAVE_ROOT, ensure_runtime_directories
    from observations import observe
    from runtime_driver import RuntimeDriver

    ensure_runtime_directories()

    initial_ids = sorted(path.parent.name for path in (SAVE_ROOT / "monsters").glob("*/monster.json"))
    # Salt resumed fixtures with their existing IDs. Restarting the fresh-save
    # UUID sequence would otherwise immediately collide with saved starters.
    identity_rng = random.Random(f"e2e-identities:{request['seed']}:{json.dumps(initial_ids)}")

    def next_identity() -> UUID:
        return UUID(int=identity_rng.getrandbits(128), version=4)

    pygame.init()
    try:
        pygame.display.set_mode((1, 1))
        with ExitStack() as stack:
            stack.enter_context(patch.object(pygame.time, "get_ticks", clock.ticks))
            stack.enter_context(patch("kadoka_quest.data.monsters.uuid4", next_identity))
            stack.enter_context(patch("kadoka_quest.apps.game.uuid4", next_identity))
            stack.enter_context(patch("kadoka_quest.data.savedata.datetime", SimpleNamespace(now=clock.datetime_now)))
            # A game-only scenario must fail rather than secretly launch/fake a
            # second application. Multi-app ranch flows belong to Issue #204.
            stack.enter_context(patch(
                "kadoka_quest.apps.manager_process_service.ManagerProcessService.open",
                side_effect=RuntimeError("External manager launch needs a multi-app E2E driver (#204)"),
            ))
            driver = RuntimeDriver(request["seed"], clock)
            checkpoints = {"initial": observe(driver, driver.save_root)}
            for index, step in enumerate(request["steps"]):
                label = ""
                try:
                    if not isinstance(step, dict):
                        raise ValueError("step must be an object")
                    label = str(step.get("label", ""))
                    if label and label in {*checkpoints, "final"}:
                        raise ValueError(f"Duplicate/reserved checkpoint label: {label}")
                    driver.execute(step)
                    if label:
                        checkpoints[label] = observe(driver, driver.save_root)
                except Exception as error:
                    context = label or (step.get("kind", "?") if isinstance(step, dict) else "?")
                    raise RuntimeError(
                        f"Step {index} ({context}) failed: {error}"
                    ) from error
            checkpoints["final"] = observe(driver, driver.save_root)
            paths["save"] = driver.save_root
            return {
                "seed": request["seed"], "start_ms": request["start_ms"],
                "paths": {name: str(path) for name, path in paths.items()},
                "data_root": str(DATA_ROOT), "asset_root": str(ASSET_ROOT),
                "composition_root": "kadoka_quest.apps.game.KadokaQuest",
                "input_adapter": "kadoka_quest.ui.runtime_input_adapter.RuntimeInputAdapter",
                "sdl_driver": pygame.display.get_driver(), "frames": driver.frames,
                "checkpoints": checkpoints,
            }
    finally:
        pygame.quit()


if __name__ == "__main__":
    report = run(json.load(sys.stdin))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
