"""Read JSON-like runtime/save observations without changing game progress."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from kadoka_quest.data.jsonio import read_json


def mob_observation(mob: dict) -> dict:
    keys = ("id", "name", "species_id", "x", "y", "direction", "ai", "spawn", "next_move_tick")
    return {key: mob[key] for key in keys if key in mob}


def combatant_observation(member) -> dict:
    return {
        "monster": member.record.monster, "ai": member.record.ai,
        "stats": member.stats, "hp": member.hp, "mp": member.mp,
        "status_effects": member.status_effects,
        "action_history": member.action_history, "fled": member.fled,
    }


def battle_observation(session) -> dict | None:
    battle = session.battle
    if battle is None:
        return None
    return {
        "outcome": battle.outcome, "round_number": battle.round_number,
        "learning_enabled": battle.learning_enabled, "log": battle.log,
        "allies": [combatant_observation(member) for member in battle.allies],
        "enemies": [combatant_observation(member) for member in battle.enemies],
        "selection": session.selection, "auto": session.auto,
        "playback": session.playback, "visible_log_count": session.visible_log_count,
        "next_log_tick": session.next_log_tick, "action_line": session.action_line,
        "finalized": session.finalized, "simulation": session.simulation,
    }


def observe(driver, save_root: Path) -> dict:
    game = driver.game
    # Do not call movement.position(): it can snap/mutate completed movement.
    result = {
        "clock_ms": driver.clock.now, "running": driver.running,
        "mode": game.mode, "status": game.status,
        "map_id": game.map_data["id"],
        "player": {"x": game.player_x, "y": game.player_y, "direction": game.player_direction},
        "state": game.state,
        "party_ids": [member.monster_id for member in game.party()],
        "monsters": [{"monster": record.monster, "ai": record.ai}
                     for record in game.monsters.list_records()],
        "fixed_mobs": [mob_observation(mob) for mob in game.home_npcs],
        "wild_mobs": [mob_observation(mob) for mob in game.hidden_monsters],
        "password": {"active": game.password_session.active,
                     "input": game.password_session.input_text,
                     "message": game.password_session.message},
        "battle": battle_observation(game.battle_session),
        "saved_files": {path.relative_to(save_root).as_posix(): read_json(path)
                        for path in sorted(save_root.rglob("*.json"))},
    }
    return deepcopy(result)
