# {
#   責務: [test_chase_traffic: test・chase・trafficの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import random

from kadoka_engine.chase_traffic import ChaseTraffic
from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController


# {
#   責務: [world: test・chase・trafficのマップ状態を求める]
#   処理: [1: test・chase・trafficのマップ状態を求める]
#   引数: [rows: rows]
#   戻り値: [result: test・chase・trafficのマップ状態を求めるための結果（型注釈なし）]
# }
def world(rows):
    data = {"width": len(rows[0]), "height": len(rows), "tiles": [list(row) for row in rows], "spawns": []}
    blocks = {".": {"enemy_walkable": True}, "#": {"enemy_walkable": False}}
    field = FieldEngine(data, blocks)
    return data, blocks, field


# {
#   責務: [fork: test・chase・trafficのforkを求める]
#   処理: [1: test・chase・trafficのforkを求める]
#   引数: []
#   戻り値: [result: test・chase・trafficのforkを求めるための結果（型注釈なし）]
# }
def fork():
    return world([
        "##########", "##########", "#........#", "#...###..#",
        "#........#", "##########", "##########",
    ])


# {
#   責務: [test_reservations_divert_next_chaser_to_other_branch: 検証: reservations divert next chaser to other branch]
#   処理: [1: 検証: reservations divert next chaser to other branch]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_reservations_divert_next_chaser_to_other_branch():
    _, _, field = fork()
    traffic = ChaseTraffic(field)
    traffic.begin(1000, {1, 2})
    first = traffic.plan(1, (3, 3), (8, 3), set(), set(), 320)
    second = traffic.plan(2, (2, 3), (8, 3), {(3, 3)}, set(), 320)
    assert first == (3, 2)
    assert second == (2, 4)
    assert traffic.reserved[(3, 2)] == {1}
    assert traffic.reserved[(2, 4)] == {2}


# {
#   責務: [test_recent_trail_is_soft_and_expires: 検証: recent trail is soft and expires]
#   処理: [1: 検証: recent trail is soft and expires]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_recent_trail_is_soft_and_expires():
    _, _, field = fork()
    traffic = ChaseTraffic(field)
    traffic.begin(1000, {1, 2})
    for x in range(3, 9):
        traffic.record(1, (x, 2))
    assert traffic.plan(2, (3, 3), (8, 3), set(), set(), 320) == (3, 4)
    traffic.begin(2280, {1, 2})
    assert traffic.recent == {}
    assert traffic.reserved == {}
    assert traffic.plan(2, (3, 3), (8, 3), set(), set(), 320) == (3, 2)


# {
#   責務: [test_corridor_reuses_reserved_recent_path_without_freezing: 検証: corridor reuses reserved recent path without freezing]
#   処理: [1: 検証: corridor reuses reserved recent path without freezing]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_corridor_reuses_reserved_recent_path_without_freezing():
    _, _, field = world(["##########", "#........#", "##########"])
    traffic = ChaseTraffic(field)
    traffic.begin(1000, {1, 2})
    assert traffic.plan(1, (3, 1), (8, 1), set(), set(), 320) == (4, 1)
    traffic.record(1, (3, 1))
    # Future occupied/reserved tiles add cost, not an impassable wall.
    assert traffic.plan(2, (2, 1), (8, 1), {(4, 1)}, set(), 320) == (3, 1)
    assert traffic.plan(2, (3, 1), (8, 1), {(4, 1)}, set(), 320) == (3, 1)


# {
#   責務: [test_reservations_survive_non_due_ticks_and_release_removed_owners: 検証: reservations survive non due ticks and release removed owners]
#   処理: [1: 検証: reservations survive non due ticks and release removed owners]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_reservations_survive_non_due_ticks_and_release_removed_owners():
    _, _, field = fork()
    traffic = ChaseTraffic(field)
    traffic.begin(1000, {1, 2})
    traffic.plan(1, (3, 3), (8, 3), set(), set(), 320)
    before = dict(traffic.reserved)
    traffic.begin(1100, {1, 2})
    assert traffic.reserved == before
    traffic.begin(1101, {2})
    assert not traffic.reserved and not traffic.plans
    traffic.record(2, (2, 3))
    traffic.begin(0, {2})
    assert not traffic.recent


# {
#   責務: [enemy: test・chase・trafficの敵を求める]
#   処理: [1: test・chase・trafficの敵を求める]
#   引数: [
#     x: X座標
#     y: Y座標
#     ai: AI
#     due: due
#   ]
#   戻り値: [result: test・chase・trafficの敵を求めるための結果（型注釈なし）]
# }
def enemy(x, y, ai="chase", due=1000):
    return {"x": x, "y": y, "ai": ai, "next_move_tick": due}


# {
#   責務: [setup_controller: test・chase・trafficのsetup・controllerを求める]
#   処理: [1: test・chase・trafficのsetup・controllerを求める]
#   引数: [rows: rows]
#   戻り値: [result: controller（型注釈なし）]
# }
def setup_controller(rows):
    data, blocks, field = world(rows)
    controller = HiddenEnemyController(field, random.Random(148))
    controller.set_world(data, blocks)
    return controller


# {
#   責務: [test_runtime_chasers_take_separate_routes_and_finish_detour: 検証: runtime chasers take separate routes and finish detour]
#   処理: [1: 検証: runtime chasers take separate routes and finish detour]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_runtime_chasers_take_separate_routes_and_finish_detour():
    controller = setup_controller(["##########", "#........#", "#........#", "#........#", "##########"])
    leader, follower = enemy(4, 2), enemy(3, 2)
    controller.monsters = [leader, follower]
    assert controller.update((8, 2), set(), 1000)
    assert (leader["x"], leader["y"]) == (5, 2)
    assert follower["y"] != 2
    for now in range(1320, 4000, 320):
        controller.update((8, 2), set(), now)
        positions = {(m["x"], m["y"]) for m in controller.monsters}
        assert len(positions) == 2 and (8, 2) not in positions
    assert abs(follower["x"] - 8) + abs(follower["y"] - 2) == 1


# {
#   責務: [test_runtime_corridor_leader_and_follower_both_advance: 検証: runtime corridor leader and follower both advance]
#   処理: [1: 検証: runtime corridor leader and follower both advance]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_runtime_corridor_leader_and_follower_both_advance():
    controller = setup_controller(["###########", "#.........#", "###########"])
    leader, follower = enemy(4, 1), enemy(2, 1)
    controller.monsters = [leader, follower]
    for now in (1000, 1320, 1640):
        assert controller.update((9, 1), set(), now)
        assert leader["x"] > follower["x"]
    assert (leader["x"], follower["x"]) == (7, 5)


# {
#   責務: [test_first_sighting_is_required_and_memory_expires_or_target_moves: 検証: first sighting is required and memory expires or target moves]
#   処理: [1: 検証: first sighting is required and memory expires or target moves]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_first_sighting_is_required_and_memory_expires_or_target_moves():
    controller = setup_controller(["##########", "#........#", "#........#", "#........#", "##########"])
    a, b = enemy(4, 2), enemy(3, 2)
    controller.monsters = [a, b]
    controller.update((8, 2), set(), 1000)
    assert b["y"] != 2 and b["chase_target"] == (8, 2)
    controller.update((8, 2), set(), 1320)
    assert b["chasing_player"] and not b["sees_player"]
    controller.update((8, 2), set(), 6000)
    assert not b["chasing_player"] and "chase_target" not in b
    a.update(x=4, y=2, next_move_tick=7000)
    b.update(x=3, y=2, next_move_tick=7000)
    controller.update((8, 2), set(), 7000)
    controller.update((7, 3), set(), 7320)
    assert not b["sees_player"] and not b["chasing_player"]


# {
#   責務: [test_unseen_chasers_do_not_acquire_hidden_player_or_change_idle_random_ai: 検証: unseen chasers do not acquire hidden player or change idle random ai]
#   処理: [1: 検証: unseen chasers do not acquire hidden player or change idle random ai]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_unseen_chasers_do_not_acquire_hidden_player_or_change_idle_random_ai():
    controller = setup_controller(["##########", "#........#", "#........#", "#........#", "##########"])
    controller.monsters = [enemy(2, 1), enemy(3, 1), enemy(4, 1, "idle"), enemy(5, 1, "random")]
    controller.update((8, 3), set(), 1000)
    assert all(not m["chasing_player"] and "chase_target" not in m for m in controller.monsters)
    assert (controller.monsters[2]["x"], controller.monsters[2]["y"]) == (4, 1)


# {
#   責務: [test_planner_never_enters_fixed_mob_or_reserved_current_occupancy: 検証: planner never enters fixed mob or reserved current occupancy]
#   処理: [1: 検証: planner never enters fixed mob or reserved current occupancy]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_planner_never_enters_fixed_mob_or_reserved_current_occupancy():
    _, _, field = fork()
    traffic = ChaseTraffic(field)
    traffic.begin(1000, {1, 2})
    assert traffic.plan(1, (3, 3), (8, 3), {(3, 2)}, {(3, 4)}, 320) == (2, 3)
    # On an enclosed tile waiting is safe, regardless of traffic costs.
    assert traffic.plan(2, (3, 3), (8, 3), {(3, 2)}, {(3, 4), (2, 3)}, 320) == (3, 3)


# {
#   責務: [test_reset_clears_traffic_even_on_empty_spawn_map: 検証: reset clears traffic even on empty spawn map]
#   処理: [1: 検証: reset clears traffic even on empty spawn map]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_reset_clears_traffic_even_on_empty_spawn_map():
    controller = setup_controller(["....."])
    controller.traffic.begin(1000, {1})
    controller.traffic.record(1, (0, 0))
    controller.reset((4, 0), {}, 1000)
    assert not controller.traffic.recent and not controller.traffic.plans


# {
#   責務: [test_blocked_goals_and_large_maps_finish_with_bounded_search: 検証: blocked goals and large maps finish with bounded search]
#   処理: [1: 検証: blocked goals and large maps finish with bounded search]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_blocked_goals_and_large_maps_finish_with_bounded_search():
    _, _, field = world(["." * 200 for _ in range(200)])
    traffic = ChaseTraffic(field)
    target = (150, 150)
    fixed = {(149, 150), (151, 150), (150, 149), (150, 151)}
    calls = 0
    original = field.tile_allows
    # {
    #   責務: [counted: test・chase・trafficのcountedを求める]
    #   処理: [1: test・chase・trafficのcountedを求める]
    #   引数: [args: args]
    #   戻り値: [result: test・chase・trafficのcountedを求めるための結果（型注釈なし）]
    # }
    def counted(*args):
        nonlocal calls
        calls += 1
        return original(*args)
    field.tile_allows = counted
    assert traffic.plan(1, (1, 1), target, set(), fixed, 320) == (1, 1)
    assert calls <= 256 * 4
