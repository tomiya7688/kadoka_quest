# {
#   責務: [generate_sample_data: generate・sample・データの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
IMPL_PATH = Path(__file__).with_name("_generate_sample_data_impl.py")


# {
#   責務: [main: generate・sample・データのエントリ処理を実行する]
#   処理: [1: generate・sample・データのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
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
