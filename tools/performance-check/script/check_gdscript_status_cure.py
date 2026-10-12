"""治療予測/保持と実行を測ります。--cure-healは統合予測、--status-stateは個体状態更新、--cure-contextは定義選択、--session-statusは開始/読取、--cure-actionは八体の実回復/MP消費/毒解除です。実セーブは使いません。"""
# {
#   責務: [check_gdscript_status_cure: 治療予測・状態保持/更新・定義選択・実治療の時間と実結果を検査する開発専用CLIです]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]


# {
#   責務: [StatusCureBenchmark: 反復条件と実Godotの起動・治療予測/状態保持/定義選択/実治療の結果検査を所有します]
#   フィールド: [
#     godot: 計測するGodot実行ファイルのパス（str）
#     configuration: 反復・サンプル・事前実行回数の独立した辞書（dict）
#   ]
# }
class StatusCureBenchmark:
    # {
    #   責務: [__init__: 指定されたGodotとCLIの反復条件を保持します]
    #   処理: [1: 可変CLIオブジェクトではなく、計測に必要な値だけを取り出します]
    #   引数: [
    #     self: 治療予測・状態更新・定義選択の計測条件を持つ所有者
    #     godot: 実Godotのパス（str）
    #     arguments: iterations/samples/warmupと排他的cure_heal/status_state/cure_context/session_status/cure_actionのCLI条件（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        self.godot = godot
        self.configuration = {"performance": True, "iterations": max(1, arguments.iterations),
                              "samples": max(1, arguments.samples), "warmup": max(0, arguments.warmup),
                              "cure_heal": getattr(arguments, "cure_heal", False),
                              "status_state": getattr(arguments, "status_state", False),
                              "cure_context": getattr(arguments, "cure_context", False),
                              "session_status": getattr(arguments, "session_status", False),
                              "cure_action": getattr(arguments, "cure_action", False)}

    # {
    #   責務: [run: 専用JSONで治療/状態更新/定義選択の実Godotプローブを起動し、診断と計測結果を確認します]
    #   処理: [1: 専用JSONの一時領域でプローブを呼び、診断がなければ結果検査へ委譲します]
    #   引数: [self: 計測先と反復条件を持つ所有者]
    #   戻り値: [status: 正常結果と性能条件を満たせば0、診断や条件不一致なら1（int）]
    # }
    def run(self) -> int:
        # 利用者の個体・AI・保存データを読み書きせず、計測要求だけを一時ファイルにする。
        with tempfile.TemporaryDirectory(prefix="kadoka-cure-performance-") as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(self.configuration), encoding="utf-8")
            process = subprocess.run(
                [self.godot, "--headless", "--path", str(ROOT / "gdscript"), "--script",
                 "res://tests/run_status_cure_probe.gd", "--", str(path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
            )
        # 高速な解析失敗や拒否結果を、正常な治療/状態更新/定義選択の性能と扱わない。
        if process.returncode or "SCRIPT ERROR" in process.stderr or "ERROR:" in process.stderr:
            print(process.stderr + process.stdout)
            return 1
        return self._check_output(process.stdout)

    # {
    #   責務: [_check_output: 計測区分ごとの正常結果・原本保持・時間上限を照合します]
    #   処理: [1: 定義選択区分は八体/千件と選択定義、治療区分は毒一件治療とHP/MPまたは状態の前後一覧を確認します]
    #   引数: [
    #     self: 治療予測・状態更新・定義選択の性能条件を持つ所有者
    #     output: 実Godotの標準出力（str）
    #   ]
    #   戻り値: [status: 全条件一致なら0、結果欠落や不一致なら1（int）]
    # }
    def _check_output(self, output: str) -> int:
        for line in output.splitlines():
            if not line.startswith("KADOKA_STATUS_CURE_RESULT="):
                continue
            result = json.loads(base64.b64decode(line.split("=", 1)[1]))
            if self.configuration["cure_action"]:
                passed = self._valid_action_result(result)
                if result.get("ok") is False:
                    print(f"FAIL: {result.get('reason')}")
                    return 1
                print(f"{'OK' if passed else 'FAIL'} Godot cure-heal action {result['microseconds']:.2f}us <= 3000us "
                      f"[{result['iterations']} iterations, {result['samples']} samples, {result['warmup']} warmup; 8 actors; new setup each 8 actions]")
                return 0 if passed else 1
            if self.configuration["session_status"]:
                passed = self._valid_session_result(result)
                print(f"{'OK' if passed else 'FAIL'} Godot session status startup+read {result['microseconds']:.2f}us <= 3000us "
                      f"[{result['iterations']} iterations, {result['samples']} samples, {result['warmup']} warmup; 8 actors; no save writes]")
                return 0 if passed else 1
            if self.configuration["cure_context"]:
                passed = self._valid_context_result(result)
                print(f"{'OK' if passed else 'FAIL'} Godot cure-heal context selection {result['microseconds']:.2f}us <= 3000us "
                      f"[{result['iterations']} iterations, {result['samples']} samples, {result['warmup']} warmup; 8 actors, 1000 definitions; no save writes]")
                return 0 if passed else 1
            quote = result["quote"]
            original = result["original_effects"]
            # 4件中の候補2を除く一件治療を確認し、候補なしや拒否だけで通過させない。
            passed = (0 <= result["microseconds"] <= 3000 and result["input_preserved"] and quote["ok"]
                      and len(original) == 4 and original[2]["id"] == "poison"
                      and (quote["candidate_index"], quote["cured"], quote["cured_name"], quote["roll_required"]) == (2, True, "毒", True)
                      and quote["remaining_status_effects"] == [original[0], original[1], original[3]])
            if self.configuration["cure_heal"]:
                # 最大HPで制限された実回復量とMP消費まで一致した統合経路だけを合格にする。
                passed = passed and self._valid_heal_result(result)
            label = "cure-heal skill quote" if self.configuration["cure_heal"] else "status-cure quote"
            if self.configuration["status_state"]:
                passed = passed and self._valid_state_result(result)
                label = "combatant status lifecycle"
            print(f"{'OK' if passed else 'FAIL'} Godot {label} {result['microseconds']:.2f}us <= 3000us "
                  f"[{result['iterations']} iterations, {result['samples']} samples, {result['warmup']} warmup; no save writes]")
            return 0 if passed else 1
        print("FAIL: missing Godot status-cure result")
        return 1

    # {
    #   責務: [_valid_heal_result: 治療付き回復が回復上限30・実回復10・残MP6を返し、入力を保持したか確認します]
    #   処理: [1: 固定定義・固定資源要求と統合予測のHP/MP数値を照合します]
    #   引数: [
    #     self: 計測区分と反復条件を持つ所有者
    #     result: 実Godotから復号した計測結果（dict）
    #   ]
    #   戻り値: [passed: 定義・資源入力と期待した回復/MP消費が一致すればTrue（bool）]
    # }
    def _valid_heal_result(self, result: dict) -> bool:
        quote = result["quote"]
        definition = result.get("original_definition")
        request = result.get("original_request")
        return (definition == {"id": "spirit_recover", "display_name": "精霊回復", "kind": "heal",
                               "mp_cost": 4, "heal_ratio": 0.03, "status_cure_chance": 0.03}
                and request == {"current_mp": 10, "target_hp": 990, "target_max_hp": 1000,
                                "roll": 0.02, "status_effects": result["original_effects"]}
                and quote.get("scope") == "cure_heal_skill_quote"
                and (quote.get("heal_amount"), quote.get("healed"), quote.get("remaining_hp"),
                     quote.get("mp_cost"), quote.get("remaining_mp")) == (30, 10, 1000, 4, 6))

    # {
    #   責務: [_valid_state_result: 新規状態の開始・予測非変更・一件実解除と、結果一覧を照合します]
    #   処理: [1: 開始一覧4件・予測前後不変・実解除後3件と、予測/実更新の区分を照合します]
    #   引数: [
    #     self: 状態ライフサイクルの計測条件を持つ所有者
    #     result: 実Godotから復号したライフサイクル観測（dict）
    #   ]
    #   戻り値: [passed: 開始・予測・更新・読み取りの期待条件がすべて一致すればTrue（bool）]
    # }
    def _valid_state_result(self, result: dict) -> bool:
        quote = result["quote"]
        expected_initial = {"status_effects": result["original_effects"]}
        expected_after = {"status_effects": quote["remaining_status_effects"]}
        return (quote.get("scope") == "combatant_status_cure"
                and result.get("started") == {"ok": True, "snapshot": expected_initial}
                and result.get("after_quote") == expected_initial
                and result.get("after") == expected_after
                and result.get("prediction") == {**quote, "scope": "status_cure_quote"})


    # {
    #   責務: [_valid_context_result: 千件定義からの治療付き回復選択が正規化結果・八体・原本保持・時間上限に一致したか確認します]
    #   処理: [1: 選択定義の必須数値・参加数/索引数・準備と入力の不変・中央値を照合します]
    #   引数: [
    #     self: 定義選択の計測条件を持つ所有者
    #     result: 実Godotから復号した定義選択の計測結果（dict）
    #   ]
    #   戻り値: [passed: 全期待条件が一致すればTrue（bool）]
    # }
    def _valid_context_result(self, result: dict) -> bool:
        return (0 <= result.get("microseconds", -1) <= 3000
                and result.get("actors") == 8 and result.get("definitions") == 1000
                and result.get("input_preserved") is True and result.get("prepared_preserved") is True
                and result.get("selected") == {"ok": True, "skill": {
                    "id": "spirit_recover", "display_name": "精霊回復", "kind": "heal", "mp_cost": 4,
                    "heal_ratio": 0.03, "status_cure_chance": 0.03}})


    # {
    #   責務: [_valid_session_result: 状態付き開始・八体の初期状態読取・数値資源保持と計測上限を照合します]
    #   処理: [1: 正常開始と個別/全体読取を入力に照合し、拒否や状態欠落を高速な成功と扱いません]
    #   引数: [
    #     self: 計測条件の所有者
    #     result: 実Godotから復号した計測結果（dict）
    #   ]
    #   戻り値: [passed: 開始・読取・原本保持・時間上限がすべて一致すればTrue（bool）]
    # }
    def _valid_session_result(self, result: dict) -> bool:
        snapshots = result.get("original_snapshots", {})
        statuses = result.get("original_statuses", {})
        numeric = result.get("numeric", {})
        # 固定八体そのものを照合し、入力/出力が共に壊れた自己一致を通過させない。
        expected = {side: [{"identity": {"id": f"member_{index}", "species_id": "slime", "name": f"member_{index}"},
                            "stats": {"hp": 100, "mp": 100, "attack": 10, "defense": 10, "magic": 10, "speed": 10},
                            "hp": 100, "mp": 100, "alive": True, "fled": False} for index in range(4)]
                    for side in ("allies", "enemies")}
        return (snapshots == expected and 0 <= result.get("microseconds", -1) <= 3000 and result.get("actors") == 8
                and result.get("input_preserved") is True
                and all(len(snapshots.get(side, [])) == 4 and len(statuses.get(side, {})) == 4
                        for side in ("allies", "enemies"))
                and numeric == {"phase": "between_rounds", "round": 0, "cursor": 0, "order": [],
                                "pending": None, "teams": snapshots, "scope": "base_battle_cursor"}
                and result.get("started") == {"ok": True, "session": numeric}
                and result.get("statuses") == {"teams": statuses, "scope": "battle_status_only"}
                and all(effects == [{"id": "lock", "removable": False},
                                    {"id": "poison", "metadata": {"deck": [1, {"kept": True}]}}, "sleep"]
                        for side in statuses.values() for effects in side.values())
                and result.get("single") == {"ok": True, "snapshot": {
                    "status_effects": statuses.get("allies", {}).get("member_0")}})


    # {
    #   責務: [_valid_action_result: 実回復・MP消費・毒解除の全反復成功と八体の最終資源/状態・性能を照合します]
    #   処理: [1: 固定数値と状態の実結果を確認し、拒否や候補なしの高速計測を通過させません]
    #   引数: [
    #     self: 計測条件の所有者
    #     result: 実Godotから復号した専用行動計測結果（dict）
    #   ]
    #   戻り値: [passed: 全期待値と一行動3000us以内が一致すればTrue（bool）]
    # }
    def _valid_action_result(self, result: dict) -> bool:
        expected_count = self.configuration["iterations"] * self.configuration["samples"] + self.configuration["warmup"]
        statuses = {side: {str(index): [{"id": "lock", "removable": False}, "sleep"] for index in range(4)}
                    for side in ("allies", "enemies")}
        numeric = result.get("numeric", {})
        last = result.get("last", {})
        teams = {side: [{"identity": {"id": str(index), "species_id": "slime", "name": "test"},
                         "stats": {"hp": 1000000000, "mp": 1000000000, "attack": 10, "defense": 10, "magic": 10, "speed": 1},
                         "hp": 900000001, "mp": 999999994, "fled": False, "alive": True} for index in range(4)]
                 for side in ("allies", "enemies")}
        order = [{"side": side, "id": str(index)} for side in ("allies", "enemies") for index in range(4)]
        expected_numeric = {"phase": "round_finished", "round": 1, "cursor": 8, "order": order,
                            "pending": None, "teams": teams, "scope": "base_battle_cursor"}
        return (numeric == expected_numeric and last.get("session") == numeric
                and 0 <= result.get("microseconds", -1) <= 3000 and result.get("actors") == 8
                and result.get("completed") == expected_count and expected_count % 8 == 0
                and result.get("input_preserved") is True and numeric.get("phase") == "round_finished"
                and result.get("statuses") == {"teams": statuses, "scope": "battle_status_only"}
                and last.get("statuses") == result["statuses"]
                and last.get("cure", {}).get("remaining_status_effects") == [{"id": "lock", "removable": False}, "sleep"]
                and last.get("ok") is True and last.get("executed") is True
                and last.get("scope") == "explicit_cure_heal_skill_only"
                and (last.get("spent_mp"), last.get("healed")) == (6, 1)
                and last.get("cure", {}).get("cured") is True and last.get("cure", {}).get("cured_name") == "poison")


# {
#   責務: [main: CLI条件とGodot実行先を確認し、治療予測・状態保持・定義選択・治療付き実行の計測へ委譲します]
#   処理: [1: 反復条件を解析し、実Godot指定済みなら計測、未指定なら未検証を返します]
#   引数: []
#   戻り値: [status: 成功0・失敗1・Godot未指定の未検証2（int）]
# }
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--cure-heal", action="store_true", help="一件治療と最大HP制限付きHP回復の統合予測を測定します")
    mode.add_argument("--status-state", action="store_true", help="専用の状態開始・予測・一件治療・読み取りを測定します")
    mode.add_argument("--cure-context", action="store_true", help="八体・千件の準備済み索引から治療付き回復定義の選択を測定します")
    mode.add_argument("--session-status", action="store_true", help="八体の明示状態付きSession開始と個別/全体読取を毎反復で測定します")
    mode.add_argument("--cure-action", action="store_true", help="八体の実回復/MP消費/毒解除を測ります。総行動数は8の倍数にしてください")
    arguments = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    # Godotがない環境では、計測したように成功を返しません。
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    return StatusCureBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
