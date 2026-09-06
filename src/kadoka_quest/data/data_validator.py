from __future__ import annotations

from pathlib import Path

from kadoka_engine.data_validator import DataValidator as EngineDataValidator
from kadoka_quest.paths import DATA_ROOT


class DataValidator(EngineDataValidator):
    """Backward-compatible Kadoka Quest adapter for the reusable validator."""

    def __init__(self, data_root: Path | None = None) -> None:
        super().__init__(Path(data_root or DATA_ROOT))
