from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools" / "code-docs" / "script" / "generate_repo_map.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("repo_map_generator", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repo_map_is_deterministic_and_signature_only() -> None:
    generator = load_generator()
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory)
        (source / "sample.py").write_text(
            "class Example:\n"
            "    def __init__(self, value, flag=False):\n"
            "        self.value = value\n\n"
            "    def hidden_body(self):\n"
            "        return 'implementation body'\n\n"
            "def build(name='x', *, enabled=True):\n"
            "    return Example(name, enabled)\n\n"
            "def _private_helper():\n"
            "    return 1\n",
            encoding="utf-8",
        )

        first = generator.render_repo_map(source)
        second = generator.render_repo_map(source)

    assert first == second
    assert "class Example(value, flag=False)" in first
    assert "def build(name='x', *, enabled=True)" in first
    assert "implementation body" not in first
    assert "hidden_body" not in first
    assert "_private_helper" not in first


def test_repo_map_can_index_the_real_package() -> None:
    generator = load_generator()
    content = generator.render_repo_map(ROOT / "src" / "kadoka_quest")

    assert "`core/battle.py`" in content
    assert "class BattleEngine" in content
    assert "`data/repository.py`" in content
    assert "class GameRepository" in content
    assert "`application/runtime_orchestrator.py`" in content
    assert len(content.encode("utf-8")) < 50000


def test_codemap_points_to_generated_symbol_map() -> None:
    content = (ROOT / "docs" / "CODEMAP.md").read_text(encoding="utf-8")

    assert "docs/generated/REPO_MAP.md" in content
    assert "tools/code-docs/script/generate_repo_map.py" in content
    assert "Primary implementation" in content
    assert "Preferred tests" in content
