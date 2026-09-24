"""Command-driven application coordination shared by runtime screens."""

from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.application.command_bus import CommandBus


def __getattr__(name: str):
    # Command apps import this package's plain types before they are initialized.
    # Importing the orchestrator eagerly would import those apps again.
    if name == "RuntimeOrchestrator":
        from kadoka_quest.application.runtime_orchestrator import RuntimeOrchestrator

        return RuntimeOrchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["AppCommand", "CommandBus", "RuntimeOrchestrator"]
