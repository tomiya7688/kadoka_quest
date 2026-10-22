# {
#   責務: [test_gdscript_pixel_ui: Godotの共通テーマとモーダル操作probeを通常のpytest検査へ接続します。]
#   フィールド: []
# }
from __future__ import annotations

import subprocess

import pytest

from test_gdscript_bootstrap import GODOT, ROOT, run_godot


# {
#   責務: [test_real_godot_pixel_ui_layout_focus_and_navigation: 日本語フォントをimportした実Godotで、配置・フォーカス・多数項目・かな入力を検証します。]
#   処理: [
#     1: 新規checkoutでもフォントを読めるようGodotの資源importを実行します。
#     2: 既存の隔離起動fixtureでUI専用probeを実行し、失敗一覧が空であることを確認します。
#   ]
#   引数: [tmp_path: 実セーブと分離したGodot検査用フォルダ]
#   戻り値: [result: なし]
# }
@pytest.mark.skipif(not GODOT, reason="KADOKA_GODOT_EXECUTABLEまたはGodotのPATH設定が必要です。")
def test_real_godot_pixel_ui_layout_focus_and_navigation(tmp_path):
    # PNGやTTFのimport生成物を持たない新規checkoutでも、実フォントの描画設定を検査します。
    imported = subprocess.run(
        [str(GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--editor", "--import", "--quit"],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        check=False,
    )
    assert imported.returncode == 0, imported.stdout + imported.stderr
    assert "SCRIPT ERROR" not in imported.stderr, imported.stderr
    result = run_godot("res://tests/run_pixel_ui_probe.gd", tmp_path)
    assert result == {"ok": True, "failures": []}
