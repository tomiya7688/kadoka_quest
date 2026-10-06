"""Command-driven application coordination shared by runtime screens."""
# {
#   責務: [__init__: Command-driven application coordination shared by runtime screens.]
#   フィールド: []
# }

from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.application.command_bus import CommandBus


# {
#   責務: [__getattr__: 要求された属性名に対応する公開オブジェクトを遅延解決する]
#   処理: [1: 要求された属性名に対応する公開オブジェクトを遅延解決する]
#   引数: [name: 名前（str）]
#   戻り値: [result: 実行時・orchestrator（型注釈なし）]
# }
def __getattr__(name: str):
    # Command apps import this package's plain types before they are initialized.
    # Importing the orchestrator eagerly would import those apps again.
    if name == "RuntimeOrchestrator":
        from kadoka_quest.application.runtime_orchestrator import RuntimeOrchestrator

        return RuntimeOrchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["AppCommand", "CommandBus", "RuntimeOrchestrator"]
