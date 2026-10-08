"""MP付き単体HP回復の純粋予測を実Godotで測定します。実セーブは使用しません。"""
# {
#   責務: [check_gdscript_heal_skill: HP回復予測の時間・上限量・実回復量・残HP/MP・入力保持を検査する開発専用CLIです]
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
#   責務: [HealSkillBenchmark: 共用の反復条件とHP回復予測の数値結果検証を所有します]
#   フィールド: [
#     godot: 継承元が所有するGodot実行ファイルのパス（str）
#     configuration: 継承元が所有する反復条件と契約区分の辞書（dict）
#   ]
# }
class HealSkillBenchmark(MagicSkillBenchmark):
    # {
    #   責務: [__init__: 共用の計測条件にHP回復契約の選択を加えます]
    #   処理: [1: 共用計測条件を初期化し、heal区分を有効にします]
    #   引数: [
    #     self: HP回復計測の所有者
    #     godot: Godotのパス（str）
    #     arguments: 反復条件（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        # 一時JSON・起動・解析診断・結果検査の入口を共用する。
        super().__init__(godot, arguments)
        self.configuration["heal"] = True

    # {
    #   責務: [_check_output: 時間上限と回復上限量220・実回復100・残HP1000/MP4・元資源保持を照合します]
    #   処理: [1: 実Godotの観測を読み、時間・数値・入力不変のすべてを判定します]
    #   引数: [
    #     self: HP回復計測の所有者
    #     output: Godotの標準出力（str）
    #   ]
    #   戻り値: [status: 全条件一致なら0、失敗または結果欠落なら1（int）]
    # }
    def _check_output(self, output: str) -> int:
        # 高速に拒否しただけの実行や、最大HPを超えて回復する結果は成功にしない。
        for line in output.splitlines():
            if not line.startswith("KADOKA_MAGIC_SKILL_RESULT="):
                continue
            result = json.loads(base64.b64decode(line.split("=", 1)[1]))
            quote = result["quote"]
            passed = (result["microseconds"] <= 3000 and quote["ok"] and result["input_preserved"]
                      and (result["current_mp"], result["target_hp"]) == (10, 900)
                      and (quote["heal_amount"], quote["healed"], quote["remaining_hp"], quote["remaining_mp"]) == (220, 100, 1000, 4))
            print(f"{'OK' if passed else 'FAIL'} Godot heal-skill quote {result['microseconds']:.2f}us <= 3000us "
                  f"[{result['iterations']} iterations, {result['samples']} samples, {result['warmup']} warmup; no writes]")
            return 0 if passed else 1
        print("FAIL: missing Godot heal-skill result")
        return 1


# {
#   責務: [main: CLI条件とGodot実行先を確認し、HP回復予測の性能計測へ委譲します]
#   処理: [1: CLIの反復条件を読み、Godot指定済みなら計測し、未指定なら未検証を返します]
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
    return HealSkillBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
