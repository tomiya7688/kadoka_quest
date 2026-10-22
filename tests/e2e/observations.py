"""Read JSON-like runtime/save observations without changing game progress."""
# {
#   責務: [observations: Read JSON-like runtime/save observations without changing game progress.]
#   フィールド: []
# }

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from kadoka_quest.data.jsonio import read_json
from kadoka_quest.data.savedata import SaveDataManager
from kadoka_quest.paths import SAVEDATA_ROOT


# {
#   責務: [mob_observation: observationsのモブ・observationを求める]
#   処理: [1: observationsのモブ・observationを求める]
#   引数: [mob: モブ（dict）]
#   戻り値: [result: observationsのモブ・observationを求めるための結果（dict）]
# }
def mob_observation(mob: dict) -> dict:
    keys = ("id", "name", "species_id", "x", "y", "direction", "ai", "spawn", "next_move_tick")
    return {key: mob[key] for key in keys if key in mob}


# {
#   責務: [combatant_observation: observationsの戦闘個体・observationを求める]
#   処理: [1: observationsの戦闘個体・observationを求める]
#   引数: [member: 個体]
#   戻り値: [result: observationsの戦闘個体・observationを求めるための結果（dict）]
# }
def combatant_observation(member) -> dict:
    return {
        "monster": member.record.monster, "ai": member.record.ai,
        "stats": member.stats, "hp": member.hp, "mp": member.mp,
        "status_effects": member.status_effects,
        "action_history": member.action_history, "fled": member.fled,
    }


# {
#   責務: [battle_observation: observationsの戦闘・observationを求める]
#   処理: [1: observationsの戦闘・observationを求める]
#   引数: [session: セッション]
#   戻り値: [result: observationsの戦闘・observationを求めるための結果（dict | None）]
# }
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


# {
#   責務: [observe: observationsのobserveを求める]
#   処理: [1: observationsのobserveを求める]
#   引数: [
#     driver: driver
#     save_root: 保存・基準ディレクトリ（Path）
#   ]
#   戻り値: [result: observationsのobserveを求めるための結果（dict）]
# }
def observe(driver, save_root: Path) -> dict:
    game = driver.game
    saves = SaveDataManager(SAVEDATA_ROOT)
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
        "render": driver.last_render,
        "launcher_runs": driver.launcher_runs,
        "active_save": saves.active_name(),
        "saved_profiles": {
            name: {path.relative_to(saves.profile_root(name)).as_posix(): read_json(path)
                   for path in sorted(saves.profile_root(name).rglob("*.json"))}
            for name in saves.list_names()
        },
        "saved_files": {path.relative_to(save_root).as_posix(): read_json(path)
                        for path in sorted(save_root.rglob("*.json"))},
    }
    return deepcopy(result)
