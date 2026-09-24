from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProgressSession:
    """Own the current in-memory save payload, including reload replacement.

    Stores perform I/O; consumers must obtain state at use time rather than
    retaining a dictionary that may have been replaced by a manager reload.
    """

    state: dict
