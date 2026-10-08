"""自傷付き単体魔法の純粋予測を実Godotで測定します。実セーブは使用しません。"""
# {
#   責務: [check_gdscript_self_damage_magic: 自傷予測の時間・敵HP/術者HP/MP予測・入力保持を検査する開発専用CLIです]
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
#   責務: [SelfDamageMagicBenchmark: 自傷付き魔法の計測条件と数値結果検証を所有します]
#   フィールド: [
#     godot: 使用する実Godotのパス（str）
#     configuration: 継承元が所有する反復条件と契約選択（dict）
#   ]
# }
class SelfDamageMagicBenchmark(MagicSkillBenchmark):
    # {
    #   責務: [__init__: 通常魔法と共通の計測条件に自傷契約の選択を加えます]
    #   処理: [
    #     1: 共用MagicSkillBenchmarkで反復条件を初期化します
    #     2: 共有プローブの自傷魔法契約を選択します
    #   ]
    #   引数: [
    #     self: 自傷予測計測の所有者
    #     godot: Godotのパス（str）
    #     arguments: 反復・サンプル・事前実行数（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        # 起動・一時JSON・診断検査は共有し、Playerへ開発ツール依存を追加しない。
        super().__init__(godot, arguments)
        self.configuration["self_damage"] = True

    # {
    #   責務: [_check_output: 時間上限と自傷を含む数値予測および元資源の保持を照合します]
    #   処理: [
    #     1: 実Godotの標準出力から自傷魔法の計測結果を読みます
    #     2: 時間上限・敵HP800/術者HP80/残MP2の予測・元資源保持を判定します
    #   ]
    #   引数: [
    #     self: 自傷予測計測の所有者
    #     output: Godotの標準出力（str）
    #   ]
    #   戻り値: [status: 全条件一致なら0、失敗または結果欠落なら1（int）]
    # }
    def _check_output(self, output: str) -> int:
        # 高速な拒否や自傷を省略した計算を、正常な予測性能と判定しない。
        for line in output.splitlines():
            if not line.startswith("KADOKA_MAGIC_SKILL_RESULT="):
                continue
            result = json.loads(base64.b64decode(line.split("=", 1)[1]))
            quote = result["quote"]
            passed = (result["microseconds"] <= 3000 and quote["ok"] and result["input_preserved"]
                      and (result["current_mp"], result["target_hp"], result["actor_hp"]) == (20, 1000, 100)
                      and (quote["remaining_mp"], quote["remaining_hp"], quote["remaining_actor_hp"]) == (2, 800, 80)
                      and (quote["dealt"], quote["self_damage"], quote["self_dealt"]) == (200, 20, 20))
            print(f"{'OK' if passed else 'FAIL'} Godot self-damage magic quote {result['microseconds']:.2f}us <= 3000us "
                  f"[{result['iterations']} iterations, {result['samples']} samples, {result['warmup']} warmup; no writes]")
            return 0 if passed else 1
        print("FAIL: missing Godot self-damage magic result")
        return 1


# {
#   責務: [main: CLI条件とGodot実行先を検証し、自傷付き魔法の性能計測へ委譲します]
#   処理: [
#     1: CLIの反復条件とGodotの実行ファイルを確認します
#     2: Godot未指定なら未検証、指定済みなら自傷魔法の予測計測を実行します
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
    return SelfDamageMagicBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
