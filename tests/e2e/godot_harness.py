"""Godot版のE2Eシナリオを、実セーブと分離した保存先で本物のGodotプロセスとして実行します。"""
# {
#   責務: [godot_harness: Godot版の起動画面へ実入力を送るシナリオを、実行ごとに新しいGodotプロセスで起動し、同じ専用保存先を再起動の間で引き継ぎます]
#   フィールド: [
#     PROJECT_ROOT: リポジトリ直下のパス（Path）
#     GODOT: 使用するGodotの実行ファイル。未設定ならNone（str | None）
#     DRIVER: Godot側のE2E操作スクリプトのres://パス（str）
#     _IMPORTED: このpytest実行中に資源importを済ませたGodot実行ファイルの集合（set[str]）
#   ]
# }
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import shutil
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GODOT = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
DRIVER = "res://tests/e2e_driver.gd"
_IMPORTED: set[str] = set()


# {
#   責務: [ensure_imported: 新しいcheckoutでもフォントや画像を読めるよう、Godotの資源importをpytestの実行ごとに一度だけ行います]
#   処理: [
#     1: 同じGodotで実行済みなら何もしません
#     2: エディターのheadless importを、資源数に合わせた長めの上限時間で実行し、失敗を例外にします
#   ]
#   引数: [work: importの作業フォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
def ensure_imported(work: Path) -> None:
    # importは全資源を走査して遅いため、シナリオごとではなくpytestの実行中に一度だけ行います。
    if str(GODOT) in _IMPORTED:
        return
    completed = subprocess.run(
        [str(GODOT), "--headless", "--path", str(PROJECT_ROOT / "gdscript"), "--editor", "--import", "--quit"],
        cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, check=False,
    )
    if completed.returncode or "SCRIPT ERROR" in completed.stderr:
        raise RuntimeError(f"Godot import failed ({completed.returncode}):\n{completed.stdout}\n{completed.stderr}")
    _IMPORTED.add(str(GODOT))


# {
#   責務: [GodotScenarioRunner: 一つのテストが使う専用保存先を所有し、シナリオを実行するたびに新しいGodotプロセスを起動します]
#   フィールド: [
#     root: このテスト専用の作業フォルダ（Path）
#     save_root: Godot版の保存先。再起動の間で引き継ぎます（Path）
#     timeout: 一回のGodotプロセスの上限秒数（float）
#     runs: 実行したシナリオの回数（int）
#   ]
# }
class GodotScenarioRunner:
    # {
    #   責務: [__init__: 専用の作業フォルダと保存先を用意します]
    #   処理: [1: 作業フォルダを作り、保存先のパスを決めます。保存先はGodotが必要になったときに作ります]
    #   引数: [
    #     self: 専用保存先を所有するGodotScenarioRunner
    #     root: このテスト専用の作業フォルダ（Path）
    #     timeout: 一回のGodotプロセスの上限秒数（float）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, root: Path, *, timeout: float = 180) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.save_root = self.root / "gdscript-saves"
        self.timeout = timeout
        self.runs = 0

    # {
    #   責務: [run: 一つのシナリオを新しいGodotプロセスで実行し、観測結果を返します。前回の実行の保存先を引き継ぐため、二回目以降の実行はゲームの再起動になります]
    #   処理: [
    #     1: シナリオJSONを作業フォルダへ書き、セーブ名の環境変数を外した専用環境を作ります
    #     2: 固定60fpsのheadless Godotで起動画面からシナリオを実行します
    #     3: 実行エラーや操作の失敗を例外にし、成功時は観測結果を返します
    #   ]
    #   引数: [
    #     self: 専用保存先を所有するGodotScenarioRunner
    #     steps: e2e_driver.gdへ渡す操作の一覧（list[dict]）
    #   ]
    #   戻り値: [result: ラベルごとの観測結果checkpoints（dict）]
    # }
    def run(self, steps: list[dict]) -> dict:
        ensure_imported(self.root)
        self.runs += 1
        request = self.root / f"scenario-{self.runs}.json"
        request.write_text(json.dumps({"steps": steps}, ensure_ascii=False), encoding="utf-8")
        # KADOKA_GDSCRIPT_SAVE_NAMEがあるとタイトルを飛ばすため、利用者と同じ起動になるよう外します。
        environment = {key: value for key, value in os.environ.items() if key != "KADOKA_GDSCRIPT_SAVE_NAME"}
        environment.update(KADOKA_CONTENT_ROOT=str(PROJECT_ROOT), KADOKA_GDSCRIPT_SAVE_ROOT=str(self.save_root),
                           KADOKA_SAVE_DIR=str(self.root / "python-saves"))
        # 固定fpsでフレームごとの経過時間を一定にし、長押しの反復回数を実行速度に依存させません。
        completed = subprocess.run(
            [str(GODOT), "--headless", "--fixed-fps", "60", "--path", str(PROJECT_ROOT / "gdscript"),
             "--script", DRIVER, "--", str(request)],
            cwd=self.root, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=self.timeout, check=False,
        )
        result = None
        for line in completed.stdout.splitlines():
            if line.startswith("KADOKA_E2E_RESULT="):
                result = json.loads(base64.b64decode(line.split("=", 1)[1]).decode("utf-8"))
        if result is None or "SCRIPT ERROR" in completed.stderr or "ERROR:" in completed.stderr:
            raise RuntimeError(f"Godot E2E failed ({completed.returncode}):\n{completed.stdout[-2000:]}\n{completed.stderr}")
        if not result["ok"] or completed.returncode:
            raise RuntimeError(f"Godot E2E step failed: {result.get('error')}\n{json.dumps(result.get('checkpoints'), ensure_ascii=False)}")
        return result["checkpoints"]

    # {
    #   責務: [saved_states: 専用保存先にある各セーブのstate.jsonを、セーブ名ごとに読みます]
    #   処理: [1: 保存先直下のフォルダのうちstate.jsonを持つものだけを読み、内容を返します]
    #   引数: [self: 専用保存先を所有するGodotScenarioRunner]
    #   戻り値: [result: セーブ名とstate.jsonの内容の対応（dict[str, dict]）]
    # }
    def saved_states(self) -> dict[str, dict]:
        if not self.save_root.is_dir():
            return {}
        return {
            folder.name: json.loads((folder / "state.json").read_text(encoding="utf-8"))
            for folder in sorted(self.save_root.iterdir()) if (folder / "state.json").is_file()
        }

    # {
    #   責務: [saved_files: 専用保存先の全ファイルの内容を、相対パスごとに読みます]
    #   処理: [1: 保存先以下の全ファイルを読み、別のセーブが変更されていないかの比較に使える形で返します]
    #   引数: [self: 専用保存先を所有するGodotScenarioRunner]
    #   戻り値: [result: 相対パスとファイル内容の対応（dict[str, bytes]）]
    # }
    def saved_files(self) -> dict[str, bytes]:
        if not self.save_root.is_dir():
            return {}
        return {path.relative_to(self.save_root).as_posix(): path.read_bytes()
                for path in sorted(self.save_root.rglob("*")) if path.is_file()}
