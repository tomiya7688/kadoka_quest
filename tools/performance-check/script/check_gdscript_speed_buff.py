"""ピオラの抽選前期間とMP予測を実Godotで計測します。実セーブは使用しません。"""
# {
#   責務: [check_gdscript_speed_buff: 速度強化予測の時間・期間上下限・残MP・入力保持を検査する開発専用CLIです]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import shutil

from check_gdscript_magic_skill import MagicSkillBenchmark


# {
#   責務: [validate_result: 実Godotの速度強化観測を固定期待値・反復条件・有限時間と照合します]
#   処理: [
#     1: 観測辞書の型と固定予測の全キーを確認します
#     2: 反復条件・入力保持・有限非負時間と、標準判定では3000usの上限を確認します
#   ]
#   引数: [
#     result: 実Godotの観測または検証器の形式テスト用辞書（object）
#     configuration: 要求したiterations/samples/warmupを持つ辞書（dict）
#     check_time: 標準CLIはTrue固定。Falseは少数回プローブの有限性だけを調べるテスト専用です（bool）
#   ]
#   戻り値: [result: すべての条件に一致した場合だけTrueです（bool）]
# }
def validate_result(result: object, configuration: dict, *, check_time: bool = True) -> bool:
    # 失敗結果やboolを数値として受理して、速い拒否を正常予測と誤認しません。
    if not isinstance(result, dict) or type(result.get("microseconds")) not in (int, float):
        return False
    elapsed = result["microseconds"]
    if not math.isfinite(elapsed) or elapsed < 0 or (check_time and elapsed > 3000):
        return False
    expected = {"ok": True, "scope": "speed_buff_quote", "skill_id": "piora", "multiplier": 1.5,
                "duration": {"mode": "range", "minimum": 3, "maximum": 6},
                "target_policy": "lowest_speed_multiplier", "mp_cost": 5, "remaining_mp": 5}
    quote = result.get("quote")
    if not isinstance(quote, dict) or quote != expected or quote.get("ok") is not True:
        return False
    for field in ("multiplier", "mp_cost", "remaining_mp"):
        if type(quote[field]) not in (int, float):
            return False
    for field in ("minimum", "maximum"):
        if type(quote["duration"].get(field)) not in (int, float):
            return False
    # 要求と異なる反復条件や入力破壊を、時間だけで成功にしません。
    for field in ("iterations", "samples", "warmup"):
        if type(result.get(field)) is not int or result[field] != configuration[field]:
            return False
    return (result.get("input_preserved") is True and type(result.get("current_mp")) is int
            and result["current_mp"] == 10 and result.get("target_hp") is None)


# {
#   責務: [SpeedBuffBenchmark: 共用Godot計測の速度強化区分と専用結果検証を所有します]
#   フィールド: [
#     godot: 継承元が保持するGodot実行ファイル（str）
#     configuration: 継承元が保持する反復条件とspeed_buff区分（dict）
#   ]
# }
class SpeedBuffBenchmark(MagicSkillBenchmark):
    # {
    #   責務: [__init__: 共用計測条件に速度強化の契約区分を設定します]
    #   処理: [1: 共用条件を初期化してspeed_buffを有効にします]
    #   引数: [
    #     self: 速度強化計測の所有者
    #     godot: 使用するGodot実行ファイル（str）
    #     arguments: iterations/samples/warmupを持つCLI引数（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        super().__init__(godot, arguments)
        self.configuration["speed_buff"] = True

    # {
    #   責務: [_check_output: 共用プローブ出力を復号し、正常予測と標準時間上限を判定します]
    #   処理: [1: 結果を一件読み取り、固定期待値と時間の検証へ委譲します]
    #   引数: [
    #     self: 速度強化計測条件の所有者
    #     output: Godotプローブの標準出力（str）
    #   ]
    #   戻り値: [status: 全条件成功0、解析失敗・結果欠落・不一致1です（int）]
    # }
    def _check_output(self, output: str) -> int:
        # 共用の起動・診断処理を使い、契約ごとの結果検証だけを置き換えます。
        for line in output.splitlines():
            if not line.startswith("KADOKA_MAGIC_SKILL_RESULT="):
                continue
            try:
                result = json.loads(base64.b64decode(line.split("=", 1)[1], validate=True))
            except (ValueError, UnicodeError):
                print("FAIL: invalid Godot speed-buff result")
                return 1
            passed = validate_result(result, self.configuration)
            elapsed = result.get("microseconds") if isinstance(result, dict) else None
            print(f"{'OK' if passed else 'FAIL'} Godot speed-buff quote {elapsed}us <= 3000us "
                  f"[{self.configuration['iterations']} iterations, {self.configuration['samples']} samples, "
                  f"{self.configuration['warmup']} warmup; no draws/writes]")
            return 0 if passed else 1
        print("FAIL: missing Godot speed-buff result")
        return 1


# {
#   責務: [main: Godot実行先と標準反復条件を確認し、速度強化予測の性能計測へ委譲します]
#   処理: [1: CLI条件を読み、Godot指定時だけ標準の時間上限付き検査を実行します]
#   引数: []
#   戻り値: [status: 成功0・失敗1・Godot未指定による未検証2です（int）]
# }
def main() -> int:
    # 未指定を成功として扱わず、既存予測と同じ反復条件を保持します。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    arguments = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    return SpeedBuffBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
