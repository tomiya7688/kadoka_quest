"""Launch each scenario in a fresh process before runtime path imports."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKER = Path(__file__).with_name("worker.py")


class ScenarioRunner:
    """Own disposable runs; never reuse a caller's active save/import paths."""

    def __init__(self, base_dir: Path, *, timeout: float = 30) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def run(
        self,
        steps: list[dict],
        *,
        seed: int = 7,
        start_ms: int = 0,
        data_dir: Path | None = None,
        asset_dir: Path | None = None,
        save_fixture: Path | None = None,
    ) -> dict:
        root = Path(tempfile.mkdtemp(prefix="scenario-", dir=self.base_dir))
        save = root / "profile"
        if save_fixture is not None:
            shutil.copytree(save_fixture, save)
        environment = os.environ.copy()
        environment.update({
            "KADOKA_PROJECT_ROOT": str(PROJECT_ROOT),
            "KADOKA_DATA_DIR": str(Path(data_dir or PROJECT_ROOT / "data").resolve()),
            "KADOKA_ASSET_DIR": str(Path(asset_dir or PROJECT_ROOT / "assets").resolve()),
            "KADOKA_SAVE_DIR": str(save),
            "KADOKA_SAVEDATA_ROOT": str(root / "savedata"),
            "KADOKA_IMPORT_DIR": str(root / "imports"),
            "SDL_VIDEODRIVER": "dummy",
            "SDL_AUDIODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": str(PROJECT_ROOT / "src"),
        })
        request = {"root": str(root), "seed": seed, "start_ms": start_ms, "steps": steps}
        completed = subprocess.run(
            [sys.executable, str(WORKER)],
            input=json.dumps(request, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=self.timeout,
            env=environment,
            cwd=root,
        )
        if completed.returncode:
            raise RuntimeError(
                f"E2E worker failed ({completed.returncode}) in {root}\n"
                f"{completed.stderr}\n{completed.stdout}"
            )
        try:
            return json.loads(completed.stdout)
        except ValueError as error:
            raise RuntimeError(f"Invalid E2E report: {completed.stdout}\n{completed.stderr}") from error
