from __future__ import annotations

from dataclasses import dataclass

from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.fixed_mob_controller import FixedMobController
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController
from kadoka_engine.player_field_controller import PlayerFieldController


@dataclass
class FieldSession:
    """Own one live field's engine and actors without duplicating their state.

    The engine owns the world references; controllers retain their own actor
    state. Loading, saving, and progress-dependent population resets remain
    application operations, not session I/O.
    """

    field: FieldEngine
    player: PlayerFieldController
    fixed_mobs: FixedMobController
    hidden_enemies: HiddenEnemyController

    def __post_init__(self) -> None:
        self.replace_field(self.field)

    def replace_field(self, field: FieldEngine) -> None:
        self.field = field
        self.fixed_mobs.field = field
        self.hidden_enemies.field = field
        self.set_world(field.map_data, field.blocks)

    @property
    def map_data(self) -> dict:
        return self.field.map_data

    @property
    def blocks(self) -> dict[str, dict]:
        return self.field.blocks

    def set_world(self, map_data: dict, blocks: dict[str, dict]) -> None:
        self.field.set_world(map_data, blocks)
        self.hidden_enemies.set_world(map_data, blocks)

    def enter_map(self, map_data: dict, x: int, y: int) -> None:
        """Rebind the loaded world and snap actor position before repopulation."""
        self.set_world(map_data, self.blocks)
        self.player.snap(x, y)
