# {
#   責務: [hidden_enemy_controller: 非表示・敵・controllerの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import random

from kadoka_engine.field_ai import choose_field_ai
from kadoka_engine.chase_traffic import ChaseTraffic
from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.wild_spawn import draw_wild_spawn, relative_spawn_weights


# {
#   責務: [HiddenEnemyController: Own wild field-enemy population, vision, and timed movement.]
#   フィールド: [
#     field: フィールド
#     rng: 乱数供給元
#     chase_interval_ms: chase・interval・ミリ秒
#     wander_interval_ms: wander・interval・ミリ秒
#     vision_range: vision・range
#     monsters: モンスター一覧
#     map_data: マップ・データ
#     blocks: ブロック定義
#     traffic: traffic
#   ]
# }
class HiddenEnemyController:
    """Own wild field-enemy population, vision, and timed movement.

    The historical class name remains for compatibility; UI owns visibility.
    """

    # {
    #   責務: [__init__: 非表示・敵・controllerが利用する初期状態と依存を設定する]
    #   処理: [1: 非表示・敵・controllerが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     field: フィールド（FieldEngine）
    #     rng: 乱数供給元（random.Random）
    #     chase_interval_ms: chase・interval・ミリ秒（int）
    #     wander_interval_ms: wander・interval・ミリ秒（int）
    #     vision_range: vision・range（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(
        self,
        field: FieldEngine,
        rng: random.Random,
        chase_interval_ms: int = 320,
        wander_interval_ms: int = 950,
        vision_range: int = 8,
    ) -> None:
        self.field = field
        self.rng = rng
        self.chase_interval_ms = max(1, int(chase_interval_ms))
        self.wander_interval_ms = max(1, int(wander_interval_ms))
        self.vision_range = max(0, int(vision_range))
        self.monsters: list[dict] = []
        self.map_data: dict = {}
        self.blocks: dict[str, dict] = {}
        self.traffic = ChaseTraffic(field)

    # {
    #   責務: [set_world: マップ状態を設定する]
    #   処理: [1: マップ状態を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_data: マップ・データ（dict）
    #     blocks: ブロック定義（dict[str, dict]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def set_world(self, map_data: dict, blocks: dict[str, dict]) -> None:
        if map_data is not self.map_data:
            self.traffic.clear()
        self.map_data = map_data
        self.blocks = blocks
        self.field.set_world(map_data, blocks)

    # {
    #   責務: [spawn_options: 非表示・敵・controllerの出現・optionsを求める]
    #   処理: [1: 非表示・敵・controllerの出現・optionsを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     flags: flags（dict）
    #   ]
    #   戻り値: [result: 非表示・敵・controllerの出現・optionsを求めるための結果（list[dict]）]
    # }
    def spawn_options(self, flags: dict) -> list[dict]:
        return [
            entry
            for entry in self.map_data.get("spawns", [])
            if entry.get("species_id") != "ball_slime"
            and (not entry.get("requires_flag") or flags.get(entry["requires_flag"], False))
        ]

    # {
    #   責務: [reset: 非表示・敵・controllerの初期状態へ戻す]
    #   処理: [1: 非表示・敵・controllerの初期状態へ戻す]
    #   引数: [
    #     self: 処理対象インスタンス
    #     player_position: 主人公・座標（tuple[int, int]）
    #     flags: flags（dict）
    #     now: 現在時刻（int）
    #     species_ai_weights: 種族・AI・重み一覧（dict | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def reset(
        self, player_position: tuple[int, int], flags: dict, now: int,
        species_ai_weights: dict | None = None,
    ) -> None:
        self.monsters = []
        self.traffic.clear()
        options = self.spawn_options(flags)
        if not options:
            return
        player = (int(player_position[0]), int(player_position[1]))
        spawn_tiles = [
            (x, y)
            for y, row in enumerate(self.map_data["tiles"])
            for x, block_id in enumerate(row)
            if self.blocks.get(block_id, {}).get("enemy_spawnable")
            and self.blocks.get(block_id, {}).get("enemy_walkable")
            and (x, y) != player
        ]
        self.rng.shuffle(spawn_tiles)
        population = min(
            len(spawn_tiles),
            max(12, min(24, int(self.map_data["width"] * self.map_data["height"]) // 60)),
        )
        weights = relative_spawn_weights(options)
        for x, y in spawn_tiles[:population]:
            spawn = draw_wild_spawn(self.rng, options, weights, self.map_data.get("pop_rate", 100))
            if spawn is None:
                continue
            self.monsters.append(
                {
                    "x": x,
                    "y": y,
                    "spawn": dict(spawn),
                    "ai": choose_field_ai(
                        self.rng,
                        spawn.get("field_ai_weights"),
                        self.map_data.get("field_ai_weights"),
                        (species_ai_weights or {}).get(spawn["species_id"]),
                    ),
                    "direction": "front",
                    "next_move_tick": int(now) + self.wander_interval_ms,
                }
            )

    # {
    #   責務: [find_at: atを探す]
    #   処理: [1: atを探す]
    #   引数: [
    #     self: 処理対象インスタンス
    #     position: 座標（tuple[int, int]）
    #   ]
    #   戻り値: [result: atを探すための結果（dict | None）]
    # }
    def find_at(self, position: tuple[int, int]) -> dict | None:
        return next(
            (
                monster
                for monster in self.monsters
                if (int(monster["x"]), int(monster["y"]))
                == (int(position[0]), int(position[1]))
            ),
            None,
        )

    # {
    #   責務: [remove: 非表示・敵・controllerを取り除く]
    #   処理: [1: 非表示・敵・controllerを取り除く]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster: モンスター（dict）
    #   ]
    #   戻り値: [result: 非表示・敵・controllerを取り除くための結果（bool）]
    # }
    def remove(self, monster: dict) -> bool:
        if monster not in self.monsters:
            return False
        self.monsters.remove(monster)
        self.traffic.release(id(monster))
        return True

    # {
    #   責務: [sees_player: 非表示・敵・controllerのsees・主人公を求める]
    #   処理: [1: 非表示・敵・controllerのsees・主人公を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster: モンスター（dict）
    #     player_position: 主人公・座標（tuple[int, int]）
    #   ]
    #   戻り値: [result: 非表示・敵・controllerのsees・主人公を求めるための結果（bool）]
    # }
    def sees_player(self, monster: dict, player_position: tuple[int, int]) -> bool:
        monster_x, monster_y = int(monster["x"]), int(monster["y"])
        player_x, player_y = (int(value) for value in player_position)
        if monster_x != player_x and monster_y != player_y:
            return False
        distance = abs(monster_x - player_x) + abs(monster_y - player_y)
        if distance > self.vision_range:
            return False
        return self.field.has_clear_axis_path(
            (monster_x, monster_y),
            (player_x, player_y),
            "enemy_walkable",
        )

    # {
    #   責務: [move: 非表示・敵・controllerを移動する]
    #   処理: [1: 非表示・敵・controllerを移動する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster: モンスター（dict）
    #     player_position: 主人公・座標（tuple[int, int]）
    #     visible_positions: visible・positions（set[tuple[int, int]]）
    #     traffic: traffic（ChaseTraffic | None）
    #   ]
    #   戻り値: [result: 非表示・敵・controllerを移動するための結果（bool）]
    # }
    def move(
        self,
        monster: dict,
        player_position: tuple[int, int],
        visible_positions: set[tuple[int, int]],
        traffic: ChaseTraffic | None = None,
    ) -> bool:
        # Legacy callers may still construct actors without an assigned AI.
        ai = monster.get("ai", "chase")
        sees_player = self.sees_player(monster, player_position)
        monster["sees_player"] = sees_player
        monster["chasing_player"] = ai == "chase" and sees_player
        if traffic is not None and ai == "chase":
            if sees_player:
                monster["chase_target"] = player_position
                monster["chase_until"] = traffic.now + 4000
            remembered = (
                monster.get("chase_target") == player_position
                and traffic.now < monster.get("chase_until", 0)
                and abs(int(monster["x"]) - player_position[0])
                + abs(int(monster["y"]) - player_position[1]) <= self.vision_range + 4
            )
            monster["chasing_player"] = sees_player or remembered
        if traffic is not None and not monster["chasing_player"]:
            traffic.release(id(monster))
            monster.pop("chase_target", None)
            monster.pop("chase_until", None)
        if ai == "idle":
            return False
        monster_x, monster_y = int(monster["x"]), int(monster["y"])
        player_x, player_y = (int(value) for value in player_position)
        if monster["chasing_player"]:
            dx = 0 if monster_x == player_x else (1 if player_x > monster_x else -1)
            dy = 0 if monster_y == player_y else (1 if player_y > monster_y else -1)
            directions = [(dx, dy), (0, 0)]
        else:
            directions = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]
            self.rng.shuffle(directions)
        occupied = {(player_x, player_y)} | visible_positions | {
            (int(other["x"]), int(other["y"])) for other in self.monsters if other is not monster
        }
        if traffic is not None and monster["chasing_player"]:
            x, y = traffic.plan(
                id(monster), (monster_x, monster_y), (player_x, player_y),
                occupied, visible_positions, self.chase_interval_ms,
            )
            directions = [(x - monster_x, y - monster_y)]
        for dx, dy in directions:
            x, y = monster_x + dx, monster_y + dy
            if self.field.tile_allows(x, y, "enemy_walkable") and (x, y) not in occupied:
                monster["x"], monster["y"] = x, y
                monster["direction"] = self.field.direction_for_step(
                    dx, dy, str(monster.get("direction", "front"))
                )
                if traffic is not None and monster["chasing_player"] and (dx or dy):
                    traffic.record(id(monster), (monster_x, monster_y))
                return bool(dx or dy)
        return False

    # {
    #   責務: [move_all: allを移動する]
    #   処理: [1: allを移動する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     player_position: 主人公・座標（tuple[int, int]）
    #     visible_positions: visible・positions（set[tuple[int, int]]）
    #   ]
    #   戻り値: [result: moved（bool）]
    # }
    def move_all(
        self,
        player_position: tuple[int, int],
        visible_positions: set[tuple[int, int]],
    ) -> bool:
        traffic = self._begin_traffic(self.traffic.now + self.chase_interval_ms)
        moved = False
        for monster in list(self.monsters):
            moved = self.move(monster, player_position, visible_positions, traffic) or moved
        return moved

    # {
    #   責務: [_begin_traffic: trafficを開始する]
    #   処理: [1: trafficを開始する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: trafficを開始するための結果（ChaseTraffic | None）]
    # }
    def _begin_traffic(self, now: int) -> ChaseTraffic | None:
        if now < self.traffic.now:
            for monster in self.monsters:
                monster.pop("chase_target", None)
                monster.pop("chase_until", None)
        chasers = [monster for monster in self.monsters if monster.get("ai", "chase") == "chase"]
        self.traffic.begin(now, {id(monster) for monster in chasers})
        return self.traffic if len(chasers) > 1 or any("chase_target" in m for m in chasers) else None

    # {
    #   責務: [update: 非表示・敵・controllerを更新する]
    #   処理: [1: 非表示・敵・controllerを更新する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     player_position: 主人公・座標（tuple[int, int]）
    #     visible_positions: visible・positions（set[tuple[int, int]]）
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: moved（bool）]
    # }
    def update(
        self,
        player_position: tuple[int, int],
        visible_positions: set[tuple[int, int]],
        now: int,
    ) -> bool:
        traffic = self._begin_traffic(int(now))
        moved = False
        for monster in list(self.monsters):
            if int(now) < int(monster.get("next_move_tick", 0)):
                continue
            moved = self.move(monster, player_position, visible_positions, traffic) or moved
            interval = self.chase_interval_ms if monster.get("chasing_player") else self.wander_interval_ms
            monster["next_move_tick"] = int(now) + interval
        return moved
