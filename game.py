from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from kadoka_quest.apps.game import KadokaQuest, main
from kadoka_quest.apps.simulation_facility_hooks import install_simulation_facility_hooks

install_simulation_facility_hooks(KadokaQuest)


if __name__ == "__main__":
    main()
