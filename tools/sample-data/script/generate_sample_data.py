from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
IMPL_PATH = Path(__file__).with_name("_generate_sample_data_impl.py")


def main() -> None:
    spec = importlib.util.spec_from_file_location("kadoka_sample_data_impl", IMPL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load sample-data implementation: {IMPL_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DATA = REPO_ROOT / "data"
    module.main()


if __name__ == "__main__":
    main()
