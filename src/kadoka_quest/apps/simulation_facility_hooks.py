from __future__ import annotations

import pygame

from kadoka_quest.apps.manager_process_service import ManagerProcessService
from kadoka_quest.apps.simulation_roster_service import SimulationRosterService
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.paths import IMPORT_ROOT, PROJECT_ROOT, SAVE_ROOT


def _components(session):
    process = getattr(session, "_simulation_facility_process", None)
    roster = getattr(session, "_simulation_facility_roster", None)
    if process is None:
        process = ManagerProcessService(
            PROJECT_ROOT / "simulation_manager.py",
            frozen_argument="--simulation-manager",
        )
        session._simulation_facility_process = process
    if roster is None:
        roster = SimulationRosterService(
            SAVE_ROOT / "simulation",
            session.repository,
            IMPORT_ROOT / "simulation",
        )
        session._simulation_facility_roster = roster
    return process, roster


def open_simulation_manager(session) -> None:
    process, _ = _components(session)
    if process.open() == "already_running":
        session.status = "模擬戦受付は既に開いています。"
        return
    session.status = "模擬戦受付を開きました。対戦相手を編成してください。"


def refresh_simulation_if_closed(session) -> None:
    process, roster = _components(session)
    if not process.consume_closed():
        return
    opponents = roster.consume_battle_request()
    if not opponents:
        session.status = "模擬戦受付を閉じました。"
        return
    allies = session.party()
    if not allies:
        session.status = "現在パーティが空なので模擬戦を開始できません。"
        return
    battle = BattleEngine(
        session.repository,
        allies,
        opponents,
        session.rng,
        learning_enabled=False,
    )
    session.battle_session.begin(battle, pygame.time.get_ticks(), simulation=True)
    session.mode = "battle"
    session.status = "模擬戦を開始。AI学習・経験値・通常報酬は発生しません。"


def install_simulation_facility_hooks(game_class) -> None:
    if getattr(game_class, "_simulation_facility_hooks_installed", False):
        return

    original_handle_battle_command = game_class.handle_battle_command

    def handle_battle_command(session, command: str) -> None:
        if getattr(session, "simulation", False) and command in {"scout", "item"}:
            battle = getattr(session, "battle", None)
            if battle is None or battle.outcome or getattr(session, "battle_playback", False):
                return
            log_start = len(battle.log)
            if command == "scout":
                battle.log.append("模擬戦ではスカウトできない。")
            else:
                battle.log.append("模擬戦では消費アイテムを使用できない。")
            session.start_battle_playback(log_start)
            if not session.battle_playback:
                session.finalize_battle_if_needed()
            return
        original_handle_battle_command(session, command)

    game_class.open_simulation_manager = open_simulation_manager
    game_class.refresh_simulation_if_closed = refresh_simulation_if_closed
    game_class.handle_battle_command = handle_battle_command
    game_class._simulation_facility_hooks_installed = True
