import pytest

from .harness import ScenarioRunner


@pytest.fixture
def scenario_runner(tmp_path):
    return ScenarioRunner(tmp_path / "e2e")
