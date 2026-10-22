# {
#   責務: [progress_session: 進行状態・セッションの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from dataclasses import dataclass


# {
#   責務: [ProgressSession: Own the current in-memory save payload, including reload replacement.]
#   フィールド: [state: 状態（dict）]
# }
@dataclass
class ProgressSession:
    """Own the current in-memory save payload, including reload replacement.

    Stores perform I/O; consumers must obtain state at use time rather than
    retaining a dictionary that may have been replaced by a manager reload.
    """

    state: dict
