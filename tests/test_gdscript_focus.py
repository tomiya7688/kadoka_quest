# {
#   責務: [test_gdscript_focus: Godotの選択フォーカス規則のprobeを通常のpytest検査へ接続します。]
#   フィールド: []
# }
from __future__ import annotations

import subprocess

import pytest

from test_gdscript_bootstrap import GODOT, ROOT, run_godot


# {
#   責務: [test_real_godot_focus_rules: 実Godotで主要部品のフォーカス輪郭とキーボード・ゲームパッドの移動操作を検証します。]
#   処理: [
#     1: フォントを読めるよう資源importを実行します。
#     2: フォーカスのprobeを隔離起動し、失敗一覧が空であることを確認します。
#   ]
#   引数: [tmp_path: 実セーブと分離したGodot検査用フォルダ]
#   戻り値: [result: なし]
# }
@pytest.mark.skipif(not GODOT, reason="KADOKA_GODOT_EXECUTABLEまたはGodotのPATH設定が必要です。")
def test_real_godot_focus_rules(tmp_path):
    imported = subprocess.run(
        [str(GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--editor", "--import", "--quit"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    assert imported.returncode == 0, imported.stdout + imported.stderr
    result = run_godot("res://tests/run_focus_probe.gd", tmp_path)
    assert result == {"ok": True, "failures": []}
