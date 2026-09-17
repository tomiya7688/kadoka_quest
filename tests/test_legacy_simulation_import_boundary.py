from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_monster_import_service_keeps_legacy_simulation_behind_adapter() -> None:
    service_source = (PROJECT_ROOT / "src/kadoka_quest/apps/monster_import_service.py").read_text(encoding="utf-8")
    legacy_source = (PROJECT_ROOT / "src/kadoka_quest/apps/legacy_simulation_import_service.py").read_text(encoding="utf-8")

    assert "self.monsters.discover_external" not in service_source
    assert "learning_enabled=False" not in service_source
    assert "LegacySimulationImportService" in service_source
    assert "self.monsters.discover_external" in legacy_source
    assert "learning_enabled=False" in legacy_source
