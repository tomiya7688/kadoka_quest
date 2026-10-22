# {
#   責務: [generate_sample_data: サンプル生成の実装を読み込み、出力先をリポジトリのdataへ設定します]
#   フィールド: []
# }
from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
IMPL_PATH = Path(__file__).with_name("_generate_sample_data_impl.py")


# {
#   責務: [main: 同梱サンプルJSONを再生成する実装へ、正規dataディレクトリを渡して実行します]
#   処理: [1: 同梱サンプルJSONを再生成する実装へ、正規dataディレクトリを渡して実行します]
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
