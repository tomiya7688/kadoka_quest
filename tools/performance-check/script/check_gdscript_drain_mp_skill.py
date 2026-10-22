"""吸MP付き単体魔法の純粋予測を実Godotで測定します。実セーブは使用しません。"""
# {
#   責務: [check_gdscript_drain_mp_skill: 吸MP予測の時間・敵HP/敵MP/術者MP・入力保持を検査する開発専用CLIです]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil

from check_gdscript_magic_skill import MagicSkillBenchmark


# {
#   責務: [DrainMpSkillBenchmark: 共用反復条件と吸MP予測の数値結果検証を所有します]
#   フィールド: [
#     godot: 使用する実Godotのパス（str）
#     configuration: 継承元が所有する反復条件と契約選択（dict）
#   ]
# }
class DrainMpSkillBenchmark(MagicSkillBenchmark):
    # {
    #   責務: [__init__: 共用の計測条件に吸MP契約の選択を加えます]
    #   処理: [
    #     1: 共用MagicSkillBenchmarkで反復条件を初期化します
    #     2: 共有プローブの吸MP契約を選択します
    #   ]
    #   引数: [
    #     self: 吸MP予測計測の所有者
    #     godot: Godotのパス（str）
    #     arguments: 反復・サンプル・事前実行数（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        # 起動・一時JSON・診断検査は共用し、Playerへ開発ツール依存を加えない。
        super().__init__(godot, arguments)
        self.configuration["drain_mp"] = True

    # {
    #   責務: [_check_output: 時間上限・HP975/術者MP19/敵MP66・MP移転量・元資源保持を照合します]
    #   処理: [
    #     1: 実Godotの標準出力から吸MP計測結果を読みます
    #     2: 時間上限と実予測値および入力不変を判定します
    #   ]
    #   引数: [
    #     self: 吸MP予測計測の所有者
    #     output: Godotの標準出力（str）
    #   ]
    #   戻り値: [status: 全条件一致なら0、失敗または結果欠落なら1（int）]
    # }
    def _check_output(self, output: str) -> int:
        # 高速な拒否やMP移転を省略した予測を、正常な性能と判定しない。
        for line in output.splitlines():
            if not line.startswith("KADOKA_MAGIC_SKILL_RESULT="):
                continue
            result = json.loads(base64.b64decode(line.split("=", 1)[1]))
            quote = result["quote"]
            passed = (result["microseconds"] <= 3000 and quote["ok"] and result["input_preserved"]
                      and (result["current_mp"], result["actor_max_mp"], result["target_mp"], result["target_hp"]) == (10, 30, 80, 1000)
                      and (quote["remaining_hp"], quote["remaining_mp"], quote["remaining_target_mp"]) == (975, 19, 66)
                      and (quote["mp_after_payment"], quote["drained_mp"], quote["recovered_mp"]) == (5, 14, 14))
            print(f"{'OK' if passed else 'FAIL'} Godot drain-MP quote {result['microseconds']:.2f}us <= 3000us "
                  f"[{result['iterations']} iterations, {result['samples']} samples, {result['warmup']} warmup; no writes]")
            return 0 if passed else 1
        print("FAIL: missing Godot drain-MP result")
        return 1


# {
#   責務: [main: CLI条件とGodot実行先を検証し、吸MP予測の性能計測へ委譲します]
#   処理: [
#     1: CLIの反復条件とGodot実行ファイルを確認します
#     2: Godot未指定なら未検証、指定済みなら吸MP予測を計測します
#   ]
#   引数: []
#   戻り値: [status: 成功0・失敗1・Godot未指定による未検証2（int）]
# }
def main() -> int:
    # Godotがない場合に、実計算の性能を検証済みとして扱わない。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    arguments = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    return DrainMpSkillBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
