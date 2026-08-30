from __future__ import annotations

from pathlib import Path
import struct
import zlib

from kadoka_quest.data.repository import GameRepository, STAT_KEYS


class SpeciesCreator:
    """Build and persist a complete, editable monster-species scaffold."""

    def __init__(self, repository: GameRepository, asset_root: Path) -> None:
        self.repository = repository
        self.asset_root = Path(asset_root)

    @staticmethod
    def validate_id(species_id: str) -> str:
        value = str(species_id).strip()
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        if not value or any(character not in allowed for character in value):
            raise ValueError("Species id may contain only lowercase letters, digits, _ and -")
        return value

    @staticmethod
    def normalize_color(value: str) -> str:
        clean = str(value).strip().lstrip("#")
        if len(clean) != 6:
            raise ValueError("Appearance color must be #RRGGBB")
        try:
            int(clean, 16)
        except ValueError as error:
            raise ValueError("Appearance color must be #RRGGBB") from error
        return f"#{clean.upper()}"

    def build_draft(
        self,
        species_id: str = "new_monster",
        display_name: str = "新しいモンスター",
        color: str = "#808080",
    ) -> tuple[dict, dict, dict, dict]:
        species_id = self.validate_id(species_id)
        color = self.normalize_color(color)
        base_path = f"characters/{species_id}"
        definition = {
            "schema_version": 1,
            "id": species_id,
            "display_name": str(display_name).strip() or species_id,
            "description": "モンスターエディターで作成した種族。",
            "family": "custom",
            "appearance": {"type": "color", "value": color, "symbol": "?"},
            "ai_profile": "normal",
            "experience_curve": "normal",
            "recruit": {"scoutable": True, "boss": False},
            "resistances": {},
            "defeat_message": None,
            "portrait_path": f"{base_path}/portrait.png",
            "field_sprite_path": f"{base_path}/field_front.png",
            "field_sprites": {
                direction: f"{base_path}/field_{direction}.png"
                for direction in ("front", "right", "left", "back")
            },
        }
        levels = {}
        for level in range(1, 101):
            levels[str(level)] = {
                "attack": 8 + (level - 1) * 3,
                "defense": 8 + (level - 1) * 3,
                "speed": 8 + (level - 1) * 3,
                "magic": 8 + (level - 1) * 3,
                "hp": 30 + (level - 1) * 6,
                "mp": 12 + (level - 1) * 4,
            }
        stats = {"schema_version": 1, "levels": levels}
        skills = {
            "schema_version": 1,
            "learnset": [
                {"level": 1, "skill_id": "attack"},
                {"level": 3, "skill_id": "defend"},
            ],
        }
        plus = {
            "schema_version": 1,
            "max_stage": 10,
            "stages": [self._plus_stage(species_id, stage) for stage in range(1, 11)],
        }
        return definition, stats, skills, plus

    @staticmethod
    def _plus_stage(species_id: str, stage: int) -> dict:
        options = []
        for branch, stat, base in (("hp", "hp", 12), ("attack", "attack", 8)):
            option = {
                "id": f"{species_id}_plus_{stage}_{branch}",
                "label": f"{stat} +{base + stage * 3}",
                "kind": "stat_add",
                "stat": stat,
                "value": base + stage * 3,
            }
            if stage > 1:
                option["requires_any"] = [f"{species_id}_plus_{stage - 1}_{branch}"]
            options.append(option)
        return {"stage": stage, "options": options}

    def create(self, definition: dict, stats: dict, skills: dict, plus: dict) -> str:
        species_id = self.validate_id(str(definition.get("id", "")))
        if species_id in self.repository.list_species_ids():
            raise ValueError(f"Species already exists: {species_id}")
        color = self.normalize_color(str(definition.get("appearance", {}).get("value", "#808080")))
        if set(stats.get("levels", {})) != {str(level) for level in range(1, 101)}:
            raise ValueError("Species stats must contain levels 1 through 100")
        if any(set(stats["levels"][str(level)]) != set(STAT_KEYS) for level in range(1, 101)):
            raise ValueError("Every level must contain all six stats")

        definition["id"] = species_id
        definition["appearance"]["value"] = color
        self._rewrite_paths(definition, species_id)
        self._rewrite_plus_ids(plus, species_id)
        self.repository.save_species_definition(definition)
        self.repository.save_species_stats(species_id, stats)
        self.repository.save_species_skills(species_id, skills)
        self.repository.save_species_plus(species_id, plus)
        self._write_placeholder_images(definition, color)
        return species_id

    @staticmethod
    def _rewrite_paths(definition: dict, species_id: str) -> None:
        base_path = f"characters/{species_id}"
        definition["portrait_path"] = f"{base_path}/portrait.png"
        definition["field_sprite_path"] = f"{base_path}/field_front.png"
        definition["field_sprites"] = {
            direction: f"{base_path}/field_{direction}.png"
            for direction in ("front", "right", "left", "back")
        }

    @staticmethod
    def _rewrite_plus_ids(plus: dict, species_id: str) -> None:
        for stage in plus.get("stages", []):
            stage_number = int(stage.get("stage", 1))
            for index, option in enumerate(stage.get("options", [])):
                suffix = str(option.get("stat", f"option_{index + 1}"))
                option["id"] = f"{species_id}_plus_{stage_number}_{suffix}"
                if stage_number > 1:
                    option["requires_any"] = [f"{species_id}_plus_{stage_number - 1}_{suffix}"]
                else:
                    option.pop("requires_any", None)

    def _write_placeholder_images(self, definition: dict, color: str) -> None:
        rgb = tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
        paths = {
            "portrait": str(definition["portrait_path"]),
            **{direction: str(path) for direction, path in definition["field_sprites"].items()},
        }
        for direction, relative_path in paths.items():
            pixels = self._placeholder_pixels(rgb, direction)
            self._write_rgba_png(self.asset_root / relative_path, 64, 64, pixels)

    @staticmethod
    def _placeholder_pixels(rgb: tuple[int, int, int], direction: str) -> bytes:
        pixels = bytearray(64 * 64 * 4)
        for y in range(64):
            for x in range(64):
                dx = (x - 31.5) / 25.0
                dy = (y - 33.0) / 27.0
                if dx * dx + dy * dy > 1.0:
                    continue
                offset = (y * 64 + x) * 4
                pixels[offset:offset + 4] = bytes((*rgb, 255))
        if direction != "back":
            eyes = [(24, 27), (40, 27)]
            if direction == "left":
                eyes = [(23, 27)]
            elif direction == "right":
                eyes = [(41, 27)]
            for center_x, center_y in eyes:
                for y in range(center_y - 3, center_y + 4):
                    for x in range(center_x - 2, center_x + 3):
                        offset = (y * 64 + x) * 4
                        pixels[offset:offset + 4] = bytes((20, 24, 30, 255))
        return bytes(pixels)

    @staticmethod
    def _write_rgba_png(path: Path, width: int, height: int, pixels: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        def chunk(kind: bytes, payload: bytes) -> bytes:
            return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

        rows = b"".join(
            b"\x00" + pixels[y * width * 4:(y + 1) * width * 4]
            for y in range(height)
        )
        content = b"\x89PNG\r\n\x1a\n"
        content += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        content += chunk(b"IDAT", zlib.compress(rows, 9))
        content += chunk(b"IEND", b"")
        path.write_bytes(content)
