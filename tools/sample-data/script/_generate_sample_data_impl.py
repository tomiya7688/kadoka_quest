"""Regenerate the bundled sample JSON. This intentionally overwrites sample data."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STATS = ("attack", "defense", "speed", "magic", "hp", "mp")


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def level_table(base: list[int], final: list[int]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for level in range(1, 101):
        ratio = (level - 1) / 99
        result[str(level)] = {
            key: round(start + (end - start) * ratio)
            for key, start, end in zip(STATS, base, final)
        }
    return result


def plus_stages(species_id: str, focus: tuple[str, str], skill_id: str) -> list[dict]:
    first, second = focus
    stages = []
    previous_paths = {"a": None, "b": None, "c": None}
    for stage in range(1, 11):
        options = [
            {
                "id": f"{species_id}_plus_{stage}_{first}",
                "label": f"{first} +{12 + stage * 3}",
                "kind": "stat_add",
                "stat": first,
                "value": 12 + stage * 3,
            },
            {
                "id": f"{species_id}_plus_{stage}_{second}",
                "label": f"{second} +{10 + stage * 3}",
                "kind": "stat_add",
                "stat": second,
                "value": 10 + stage * 3,
            },
            {
                "id": f"{species_id}_plus_{stage}_special",
                "label": f"専用強化 {stage}",
                "kind": "skill" if stage in {4, 7, 10} else "stat_multiplier",
                "skill_id": skill_id,
                "stat": "speed",
                "value": 1.04,
            },
        ]
        for index, key in enumerate(("a", "b", "c")):
            if stage > 1:
                options[index]["requires_any"] = [previous_paths[key]]
            previous_paths[key] = options[index]["id"]
        stages.append({"stage": stage, "options": options})
    return stages


SPECIES = {
    "hero": {
        "name": "主人公",
        "description": "平均的に高い能力とメンタル系無効を持つ人間。全体攻撃は持たない。",
        "family": "human",
        "color": "#F4D35E",
        "symbol": "H",
        "base": [18, 17, 16, 14, 52, 24],
        "final": [390, 370, 345, 310, 820, 430],
        "equipment": ["sword", "clothes", "staff"],
        "ai": "normal",
        "skills": [(1, "attack"), (3, "defend"), (8, "focus"), (14, "healy"), (22, "counter"), (30, "protect"), (42, "cheer"), (60, "spirit_recover")],
        "resistances": {"mental": "immune"},
        "focus": ("attack", "hp"),
        "plus_skill": "attack",
        "scoutable": False,
        "xp_curve": "normal",
    },
    "slime": {
        "name": "スライム",
        "description": "癖が少なく安定した標準的なスライム。",
        "family": "slime",
        "color": "#42A5F5",
        "symbol": "S",
        "base": [11, 10, 12, 9, 36, 19],
        "final": [285, 275, 300, 250, 650, 390],
        "equipment": ["clothes", "staff"],
        "ai": "normal",
        "skills": [(1, "attack"), (3, "defend"), (7, "body_bash"), (18, "small_heal")],
        "resistances": {"ice": "strong", "fire": "weak"},
        "focus": ("hp", "defense"),
        "plus_skill": "body_bash",
        "scoutable": True,
        "xp_curve": "normal",
    },
    "ball_slime": {
        "name": "ボールスライム",
        "description": "能力値は低めだが素早く器用。最初の相棒で、所有ゼロなら再獲得できる。",
        "family": "slime",
        "color": "#F28C28",
        "symbol": "B",
        "base": [9, 8, 17, 10, 31, 24],
        "final": [245, 225, 390, 275, 570, 455],
        "equipment": ["sword", "clothes", "staff"],
        "ai": "support",
        "skills": [(1, "attack"), (2, "roll"), (4, "defend"), (8, "piora"), (14, "small_heal"), (24, "weaken")],
        "resistances": {"wind": "strong"},
        "focus": ("speed", "magic"),
        "plus_skill": "small_heal",
        "scoutable": False,
        "reacquire": "home_from_start",
        "xp_curve": "easy",
    },
    "metal_slime": {
        "name": "メタルスライム",
        "description": "高防御・低HP。雷以外の魔法に強いが、毒以外の状態異常に弱い。",
        "family": "slime",
        "color": "#AAB4BE",
        "symbol": "M",
        "base": [10, 30, 18, 13, 13, 22],
        "final": [285, 690, 430, 350, 230, 430],
        "equipment": ["sword", "clothes"],
        "ai": "normal",
        "skills": [(1, "attack"), (1, "defend"), (5, "fluid_defense"), (9, "poke"), (16, "piora"), (35, "metal_burst")],
        "resistances": {"fire": "strong", "ice": "strong", "wind": "strong", "light": "strong", "dark": "strong", "thunder": "normal", "poison": "normal", "mental": "weak", "paralysis": "weak"},
        "focus": ("defense", "speed"),
        "plus_skill": "metal_burst",
        "scoutable": True,
        "xp_curve": "hard",
    },
    "ghost": {
        "name": "ふつうのおばけ",
        "description": "防御と光に弱いが、回避とMP妨害に優れる通常のおばけ。",
        "family": "ghost",
        "color": "#B39DDB",
        "symbol": "G",
        "base": [8, 6, 14, 16, 33, 31],
        "final": [230, 180, 350, 390, 590, 560],
        "equipment": ["clothes", "staff"],
        "ai": "trickster",
        "skills": [(1, "attack"), (3, "vanish"), (7, "avoid_light"), (13, "possess"), (22, "defend")],
        "resistances": {"light": "weak", "dark": "strong", "mental": "strong"},
        "focus": ("magic", "speed"),
        "plus_skill": "possess",
        "scoutable": True,
        "xp_curve": "normal",
    },
    "maru": {
        "name": "まる",
        "description": "戦闘ではかなり抜けている丸いおばけ。変な物を拾う探索要員。",
        "family": "round_ghost",
        "color": "#F6F2E8",
        "symbol": "○",
        "base": [5, 4, 11, 6, 48, 42],
        "final": [155, 125, 285, 175, 780, 680],
        "equipment": ["clothes", "staff"],
        "ai": "maru",
        "skills": [(1, "attack"), (1, "pick_up_maru"), (5, "vanish"), (18, "possess")],
        "resistances": {"light": "weak", "mental": "strong"},
        "focus": ("hp", "mp"),
        "plus_skill": "pick_up_maru",
        "scoutable": False,
        "reacquire": "ghost_home_password",
        "xp_curve": "very_easy",
        "defeat": "まるはつかれて動けなくなった。",
        "portrait_path": "characters/maru/portrait.png",
        "field_sprite_path": "characters/maru/field.png",
        "field_sprites": {direction: f"characters/maru/field_{direction}.png" for direction in ("front", "right", "left", "back")},
    },
    "kadoka": {
        "name": "かどか",
        "description": "みかんをよく拾い、まれに柿を持ってくる丸いおばけ。",
        "family": "round_ghost",
        "color": "#D9F0FF",
        "symbol": "K",
        "base": [6, 4, 12, 7, 47, 43],
        "final": [170, 130, 300, 185, 760, 700],
        "equipment": ["clothes", "staff"],
        "ai": "kadoka",
        "skills": [(1, "attack"), (1, "pick_up_kadoka"), (5, "vanish"), (18, "possess")],
        "resistances": {"light": "weak", "mental": "strong"},
        "focus": ("mp", "hp"),
        "plus_skill": "pick_up_kadoka",
        "scoutable": False,
        "reacquire": "ghost_home_password",
        "xp_curve": "very_easy",
        "defeat": "かどかは疲れてしまった。",
        "portrait_path": "characters/kadoka/portrait.png",
        "field_sprite_path": "characters/kadoka/field.png",
        "field_sprites": {direction: f"characters/kadoka/field_{direction}.png" for direction in ("front", "right", "left", "back")},
    },
    "dice_slime": {
        "name": "サイコロスライム",
        "description": "高水準だがサイコロ依存が強い、物語クリア後の特別なスライム。",
        "family": "slime",
        "color": "#F7F7F7",
        "symbol": "⚄",
        "base": [14, 14, 15, 13, 43, 24],
        "final": [365, 350, 375, 340, 735, 450],
        "equipment": ["sword", "clothes", "staff"],
        "ai": "dice",
        "skills": [(1, "attack"), (1, "defend"), (2, "roll"), (8, "piora"), (14, "dice_strike"), (34, "dice_magic")],
        "resistances": {"mental": "normal"},
        "focus": ("attack", "speed"),
        "plus_skill": "dice_strike",
        "scoutable": False,
        "reacquire": "home_after_story",
        "xp_curve": "normal",
        "defeat": "サイコロスライムは目を回してしまった。",
    },
}


SKILLS = [
    {"id": "attack", "display_name": "こうげき", "kind": "physical", "power": 1.0, "mp_cost": 0},
    {"id": "defend", "display_name": "ぼうぎょ", "kind": "defend", "damage_multiplier": 0.5, "mp_cost": 0},
    {"id": "body_bash", "display_name": "たいあたり", "kind": "physical", "power": 1.2, "mp_cost": 3},
    {"id": "roll", "display_name": "ころがる", "kind": "physical", "power": 1.1, "mp_cost": 2},
    {"id": "small_heal", "display_name": "小回復", "kind": "heal", "heal_ratio": 0.22, "mp_cost": 6},
    {"id": "weaken", "display_name": "ちからぬき", "kind": "magic", "power": 0.55, "element": "mental", "mp_cost": 5},
    {"id": "piora", "display_name": "ピオラ", "kind": "buff", "speed_multiplier": 1.5, "duration": [3, 6], "mp_cost": 5},
    {"id": "fluid_defense", "display_name": "流体防御", "kind": "evade", "physical": True, "lock_physical_next_turn": True, "mp_cost": 4},
    {"id": "poke", "display_name": "つつく", "kind": "physical", "power": 0.8, "critical_multiplier": 2.0, "mp_cost": 1},
    {"id": "metal_burst", "display_name": "メタルバースト", "kind": "magic", "power": 2.0, "element": "metal", "self_damage_ratio": 0.1, "mp_cost": 18},
    {"id": "avoid_light", "display_name": "光を避ける", "kind": "evade", "element": "light", "mp_cost": 3},
    {"id": "vanish", "display_name": "見えなくなる", "kind": "evade", "physical": True, "mp_cost": 4},
    {"id": "possess", "display_name": "とりつく", "kind": "drain_mp", "power": 0.25, "mp_power": 0.14, "element": "mental", "mp_cost": 5},
    {"id": "pick_up_maru", "display_name": "変なものを拾う", "kind": "field", "field_only": True, "loot_table": "maru_junk", "mp_cost": 5},
    {"id": "pick_up_kadoka", "display_name": "ものを拾う", "kind": "field", "field_only": True, "loot_table": "kadoka_fruit", "mp_cost": 5},
    {"id": "dice_strike", "display_name": "サイコロパンチ", "kind": "random", "roll_kind": "physical", "power": 1.0, "mp_cost": 6},
    {"id": "dice_magic", "display_name": "サイコロ魔法", "kind": "random", "roll_kind": "magic", "element": "arcane", "power": 1.0, "mp_cost": 12},
    {"id": "focus", "display_name": "ためる", "kind": "buff", "target": "self", "attack_multiplier": 1.5, "mp_cost": 2},
    {"id": "healy", "display_name": "ヒアリー", "kind": "heal", "heal_ratio": 0.1, "mp_cost": 5},
    {"id": "counter", "display_name": "反撃のかまえ", "kind": "defend", "damage_multiplier": 0.75, "counter": True, "mp_cost": 3},
    {"id": "protect", "display_name": "かばう", "kind": "defend", "damage_multiplier": 0.75, "protect_ally": True, "mp_cost": 3},
    {"id": "cheer", "display_name": "おうえん", "kind": "buff", "attack_multiplier": 1.2, "mp_cost": 3},
    {"id": "spirit_recover", "display_name": "きあいでなおす", "kind": "heal", "heal_ratio": 0.03, "status_cure_chance": 0.03, "mp_cost": 4},
]


EQUIPMENT = [
    {"id": "ken", "display_name": "けん", "category": "sword", "description": "通常攻撃を1.5倍で判定。", "stat_multipliers": {"speed": 0.8}, "skill_modifiers": {"attack": {"power_multiplier": 1.5}}},
    {"id": "light_cloth", "display_name": "かるい服", "category": "clothes", "description": "軽い防具。", "stat_multipliers": {"defense": 1.15, "speed": 0.92}},
    {"id": "wood_staff", "display_name": "木の杖", "category": "staff", "description": "魔法を少し強める。", "stat_multipliers": {"magic": 1.2, "speed": 0.9}},
    {"id": "metal_claw", "display_name": "メタル爪", "category": "sword", "description": "メタル狩り用の固定追加ダメージ。", "stat_multipliers": {"attack": 1.05, "speed": 0.88}, "fixed_bonus_damage": 3},
    {"id": "heavy_weight", "display_name": "重り", "category": "sword", "description": "強力だがとても遅くなる。", "stat_multipliers": {"attack": 1.35, "speed": 0.55}},
    {"id": "light_ward", "display_name": "光よけの布", "category": "clothes", "description": "光への弱点を補う。", "stat_multipliers": {"speed": 0.88}, "resistance_steps": {"light": 1}},
]


BLOCKS = [
    {"id": "grass", "display_name": "草地", "player_walkable": True, "enemy_spawnable": True, "enemy_walkable": True, "appearance": {"type": "color", "value": "#4E9F3D"}},
    {"id": "path", "display_name": "道", "player_walkable": True, "enemy_spawnable": False, "enemy_walkable": True, "appearance": {"type": "color", "value": "#C8B27D"}},
    {"id": "forest", "display_name": "深い森", "player_walkable": False, "enemy_spawnable": True, "enemy_walkable": True, "appearance": {"type": "color", "value": "#1F5D32"}},
    {"id": "water", "display_name": "水", "player_walkable": False, "enemy_spawnable": False, "enemy_walkable": False, "appearance": {"type": "color", "value": "#2878B5"}},
    {"id": "wall", "display_name": "岩壁", "player_walkable": False, "enemy_spawnable": False, "enemy_walkable": False, "appearance": {"type": "color", "value": "#4A4A4A"}},
    {"id": "safe", "display_name": "安全地帯", "player_walkable": True, "enemy_spawnable": False, "enemy_walkable": False, "appearance": {"type": "color", "value": "#8BCF9C"}},
    {"id": "town", "display_name": "街の石畳", "player_walkable": True, "enemy_spawnable": False, "enemy_walkable": False, "appearance": {"type": "color", "value": "#C7BDA5"}},
    {"id": "ranch_floor", "display_name": "牧場の床", "player_walkable": True, "enemy_spawnable": False, "enemy_walkable": False, "appearance": {"type": "color", "value": "#D8C18E"}},
    {"id": "fence", "display_name": "柵", "player_walkable": False, "enemy_spawnable": False, "enemy_walkable": False, "appearance": {"type": "color", "value": "#795548"}},
]


def bordered_tiles(width: int, height: int, fill: str = "grass") -> list[list[str]]:
    tiles = [[fill for _ in range(width)] for _ in range(height)]
    for x in range(width):
        tiles[0][x] = tiles[height - 1][x] = "wall"
    for y in range(height):
        tiles[y][0] = tiles[y][width - 1] = "wall"
    return tiles


def make_starting_town() -> dict:
    width, height = 36, 24
    tiles = bordered_tiles(width, height, "town")
    for y in range(13, 16):
        for x in range(width):
            tiles[y][x] = "path"
    for y in range(9, 16):
        for x in range(17, 20):
            tiles[y][x] = "path"
    for y in range(4, 9):
        for x in range(14, 23):
            tiles[y][x] = "wall"
    tiles[9][18] = "path"
    for y in range(4, 10):
        for x in range(4, 13):
            tiles[y][x] = "fence"
    tiles[10][8] = "path"
    return {
        "schema_version": 1,
        "id": "starting_town",
        "display_name": "はじまりの街",
        "width": width,
        "height": height,
        "tile_size": 32,
        "start": {"x": 18, "y": 14},
        "tiles": tiles,
        "spawns": [],
        "events": [
            {"id": "starting_town_sign", "x": 25, "y": 14, "type": "message", "blocking": True, "text": "東へ進むとはじまりの森。"},
            {"id": "starting_town_church", "x": 18, "y": 9, "type": "church", "text": "はじまりの街の教会。ここを復活地点にしました。", "revive": {"map_id": "starting_town", "x": 18, "y": 11, "name": "はじまりの街の教会"}},
            {"id": "ranch_sign", "x": 6, "y": 11, "type": "message", "blocking": True, "text": "モンスター牧場　個体管理とパーティ編成はこちら。"},
            {"id": "to_starting_ranch", "x": 8, "y": 10, "type": "transition", "activation": "interact", "text": "モンスター牧場へ入りました。", "target": {"map_id": "starting_ranch", "x": 14, "y": 17}},
            {"id": "to_starting_forest", "x": 35, "y": 14, "type": "transition", "target": {"map_id": "greenwood", "x": 1, "y": 6}},
        ],
    }


def make_starting_ranch() -> dict:
    width, height = 28, 20
    tiles = bordered_tiles(width, height, "ranch_floor")
    tiles[19][14] = "path"
    for x in range(4, 24):
        tiles[8][x] = "fence"
    tiles[8][14] = "ranch_floor"
    for y in range(3, 8):
        for x in range(13, 16):
            tiles[y][x] = "path"
    tiles[5][14] = "fence"
    return {
        "schema_version": 1,
        "id": "starting_ranch",
        "display_name": "モンスター牧場",
        "width": width,
        "height": height,
        "tile_size": 32,
        "start": {"x": 14, "y": 17},
        "tiles": tiles,
        "spawns": [],
        "events": [
            {"id": "ranch_manager", "x": 14, "y": 5, "type": "open_manager", "blocking": True, "text": "牧場台帳を開きます。個体管理とパーティ編成ができます。"},
            {"id": "ranch_help", "x": 9, "y": 10, "type": "message", "text": "牧場台帳では所有モンスター、AI、現在パーティ、編成プリセットを管理できます。"},
            {"id": "leave_starting_ranch", "x": 14, "y": 19, "type": "transition", "target": {"map_id": "starting_town", "x": 8, "y": 11}},
        ],
    }


def make_starting_forest() -> dict:
    width, height = 48, 32
    tiles = bordered_tiles(width, height)
    for y in range(5, 8):
        for x in range(width):
            tiles[y][x] = "path"
    tiles[6][width - 1] = "path"
    for y in range(6, 25):
        for x in range(25, 28):
            tiles[y][x] = "path"
    for y in range(13, 20):
        for x in range(34, 43):
            tiles[y][x] = "water"
    for y in range(20, 28):
        for x in range(4, 14):
            if (x + y) % 3:
                tiles[y][x] = "forest"
    for y in range(3, 6):
        for x in range(3, 9):
            tiles[y][x] = "safe"
    return {
        "schema_version": 1,
        "id": "greenwood",
        "display_name": "はじまりの森",
        "width": width,
        "height": height,
        "tile_size": 32,
        "start": {"x": 6, "y": 5},
        "tiles": tiles,
        "spawns": [
            {"species_id": "slime", "weight": 72, "min_level": 2, "max_level": 5},
            {"species_id": "ghost", "weight": 23, "min_level": 3, "max_level": 6},
            {"species_id": "metal_slime", "weight": 5, "min_level": 5, "max_level": 8}
        ],
        "events": [
            {"id": "back_to_starting_town", "x": 0, "y": 6, "type": "transition", "target": {"map_id": "starting_town", "x": 34, "y": 14}},
            {"id": "forest_sign", "x": 8, "y": 6, "type": "message", "blocking": True, "text": "東へ進むと新緑の森。"},
            {"id": "orange_tree", "x": 30, "y": 7, "type": "message", "text": "みかんが実っている。みかんを1個手に入れた。"},
            {"id": "to_fresh_forest", "x": 47, "y": 6, "type": "transition", "target": {"map_id": "fresh_forest", "x": 2, "y": 15}}
        ],
    }


def make_fresh_forest() -> dict:
    width, height = 48, 32
    tiles = bordered_tiles(width, height)
    for y in range(14, 17):
        for x in range(width):
            tiles[y][x] = "path"
    for y in range(15, 27):
        for x in range(21, 24):
            tiles[y][x] = "path"
    for y in range(4, 12):
        for x in range(6, 15):
            if (x * 2 + y) % 4:
                tiles[y][x] = "forest"
    for y in range(20, 27):
        for x in range(31, 42):
            if (x + y) % 3:
                tiles[y][x] = "forest"
    for y in range(5, 10):
        for x in range(36, 43):
            tiles[y][x] = "water"
    tiles[27][22] = "wall"
    return {
        "schema_version": 1,
        "id": "fresh_forest",
        "display_name": "新緑の森",
        "width": width,
        "height": height,
        "tile_size": 32,
        "start": {"x": 2, "y": 15},
        "tiles": tiles,
        "spawns": [
            {"species_id": "slime", "weight": 48, "min_level": 5, "max_level": 9},
            {"species_id": "ghost", "weight": 42, "min_level": 6, "max_level": 10},
            {"species_id": "metal_slime", "weight": 10, "min_level": 8, "max_level": 12}
        ],
        "events": [
            {"id": "fresh_forest_sign", "x": 8, "y": 15, "type": "message", "blocking": True, "text": "東へ進むと第二の村、ロクター村。"},
            {"id": "ghost_home_note", "x": 20, "y": 26, "type": "message", "blocking": True, "text": "『まるへ　この岩から入るんだよ　かどか　へいわなすみか』"},
            {"id": "ghost_home_rock", "x": 22, "y": 27, "type": "transition", "activation": "interact", "blocking": True, "text": "岩を調べると、隠された入口からおばけの住処へ入った。", "target": {"map_id": "ghost_home", "x": 2, "y": 9}},
            {"id": "back_to_starting_forest", "x": 0, "y": 15, "type": "transition", "target": {"map_id": "greenwood", "x": 46, "y": 6}},
            {"id": "to_rokuta_village", "x": 47, "y": 15, "type": "transition", "target": {"map_id": "rokuta_village", "x": 2, "y": 12}}
        ]
    }


def make_rokuta_village() -> dict:
    width, height = 36, 24
    tiles = bordered_tiles(width, height, "safe")
    for y in range(11, 14):
        for x in range(width):
            tiles[y][x] = "path"
    for y in range(4, 20):
        for x in range(13, 16):
            tiles[y][x] = "path"
    for y in range(4, 8):
        for x in range(10, 19):
            tiles[y][x] = "wall"
    tiles[8][14] = "path"
    for y in range(5, 10):
        for x in range(25, 32):
            tiles[y][x] = "water"
    return {
        "schema_version": 1,
        "id": "rokuta_village",
        "display_name": "ロクター村",
        "width": width,
        "height": height,
        "tile_size": 32,
        "start": {"x": 2, "y": 12},
        "tiles": tiles,
        "spawns": [],
        "events": [
            {"id": "rokuta_sign", "x": 6, "y": 12, "type": "message", "blocking": True, "text": "第二の村　ロクター村"},
            {"id": "rokuta_church", "x": 14, "y": 8, "type": "church", "text": "ロクター教会。ここを復活地点にしました。", "revive": {"map_id": "rokuta_village", "x": 14, "y": 10, "name": "ロクター教会"}},
            {"id": "back_to_fresh_forest", "x": 0, "y": 12, "type": "transition", "target": {"map_id": "fresh_forest", "x": 46, "y": 15}}
        ]
    }


def make_ghost_home() -> dict:
    width, height = 24, 18
    tiles = bordered_tiles(width, height, "safe")
    tiles[9][0] = "path"
    for y in range(3, 8):
        for x in range(15, 21):
            tiles[y][x] = "water"
    return {
        "schema_version": 1,
        "id": "ghost_home",
        "display_name": "おばけの住処",
        "width": width,
        "height": height,
        "tile_size": 32,
        "start": {"x": 2, "y": 9},
        "tiles": tiles,
        "spawns": [],
        "events": [
            {"id": "ghost_spring", "x": 17, "y": 7, "type": "password_spring", "text": "水の湧き場だ。7文字のあいことばを入力できる。"},
            {"id": "leave_ghost_home", "x": 0, "y": 9, "type": "transition", "target": {"map_id": "fresh_forest", "x": 22, "y": 26}}
        ]
    }


def main() -> None:
    write(DATA / "skills" / "skills.json", {"schema_version": 1, "skills": SKILLS})
    write(DATA / "equipment" / "equipment.json", {"schema_version": 1, "equipment": EQUIPMENT})
    for block in BLOCKS:
        write(DATA / "blocks" / f"{block['id']}.json", {"schema_version": 1, **block})
    maps = (make_starting_town(), make_starting_ranch(), make_starting_forest(), make_fresh_forest(), make_rokuta_village(), make_ghost_home())
    for map_data in maps:
        write(DATA / "maps" / map_data["id"] / "map.json", map_data)

    for species_id, config in SPECIES.items():
        recruit = {"scoutable": config["scoutable"], "boss": False}
        if config.get("reacquire"):
            recruit["reacquire_rule"] = config["reacquire"]
            recruit["ownership_cap_for_reacquire"] = 1
        definition = {
            "schema_version": 1,
            "id": species_id,
            "display_name": config["name"],
            "description": config["description"],
            "family": config["family"],
            "appearance": {"type": "color", "value": config["color"], "symbol": config["symbol"]},
            "equipment_categories": config["equipment"],
            "ai_profile": config["ai"],
            "experience_curve": config["xp_curve"],
            "recruit": recruit,
            "resistances": config["resistances"],
            "defeat_message": config.get("defeat"),
        }
        definition["portrait_path"] = config.get("portrait_path", f"characters/{species_id}/portrait.png")
        definition["field_sprite_path"] = config.get("field_sprite_path", f"characters/{species_id}/field.png")
        definition["field_sprites"] = config.get(
            "field_sprites",
            {direction: f"characters/{species_id}/field_{direction}.png" for direction in ("front", "right", "left", "back")},
        )
        folder = DATA / "species" / species_id
        write(folder / "species.json", definition)
        write(folder / "stats.json", {"schema_version": 1, "levels": level_table(config["base"], config["final"])})
        write(folder / "skills.json", {"schema_version": 1, "learnset": [{"level": level, "skill_id": skill} for level, skill in config["skills"]]})
        write(folder / "plus.json", {"schema_version": 1, "max_stage": 10, "stages": plus_stages(species_id, config["focus"], config["plus_skill"])})


if __name__ == "__main__":
    main()

