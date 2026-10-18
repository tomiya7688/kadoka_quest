# GDScriptの状態による防御力・素早さ補正

## 背景・目的・範囲

付与付き物理のダメージ計算には、出血による防御力低下を反映した数値が必要です。`status_stat_contract.gd` はPythonの `Combatant.defense` と `Combatant.speed` に対応する数値を求めます。予測は元の能力値や状態を変更せず、最新の状態一覧を受け取るたびに再計算します。

本契約は開発者用の純粋な計算APIです。画面から操作する機能ではありません。補正済み防御力は[付与付き単体物理行動](GDScript状態付与付き物理行動契約.md)へ接続しましたが、契約自身はSessionを保持しません。状態補正済み行動順、ほかの攻撃入口、AI、画面への接続は含みません。出血の継続ダメージ、一時倍率の付与・期限管理、攻撃力の一時倍率、耐性再構築も別単位です。白黒GUIとPythonのゲーム動作は変更しません。

## 入力・計算・出力

開発者は `preload("res://engine/status_stat_contract.gd")` の `quote_stats(request)` へ、次の辞書を渡してください。

```json
{
  "defense": 51,
  "speed": 41,
  "speed_multiplier": 1.5,
  "status_effects": ["poison", {"id": "bleeding", "removable": false}]
}
```

`defense` と `speed` は、Lv・＋・装備補正を済ませ、状態補正と一時速度倍率をまだ掛けていない数値です。両値は0以上9007199254740991以下の整数で、整数値のfloatも受理します。数値文字列、bool、負数、小数値は拒否します。

`speed_multiplier` は任意の有限・非負の数値で、省略時は1です。倍率は9007199254740991以下に限定し、文字列やboolを受理しません。倍率0は正常です。呼出元は一時速度倍率を別途保持し、付与・失効を管理してください。

`status_effects` は必須の最新一覧です。共用 `status_effect_contract.valid_effects` が一覧全体を検証した後、補正契約はIDが厳密に `bleeding` と一致する状態を探します。保持済みIDの前後空白は除去しません。文字列と辞書の出血が重複しても、倍率0.9は一度だけ適用します。未知ID、removable、JSON互換の拡張情報は数値を変更しません。

出血時の防御力は `max(0, int(defense * 0.9))`、素早さは `max(1, int(speed * speed_multiplier * 0.9))` です。出血なしでは状態倍率を1にします。補正契約はPythonと同じ乗算順にし、最後だけ0方向へ整数化します。例えば速度3・一時倍率1.5・出血なら、4.05を整数化した4になります。途中の4.5を整数化してから0.9を掛ける処理ではありません。

上の入力に対する成功結果は次のとおりです。成功結果は入力と参照を共有しない辞書です。防御コマンドの物理ダメージ倍率 `guard` は本計算に含めません。

```json
{"ok": true, "scope": "status_stat_quote", "defense": 45, "speed": 55}
```

## 失敗・非変更・計算量

補正契約は要求型、未知キー、defense、speed、speed_multiplier、状態一覧、速度の途中積の順に検証します。不正時は `ok=false` と `reason` の二キーだけを返し、部分的な補正値を返しません。未知キーはfalseや0でも拒否します。

拒否理由は `invalid_status_stat_request`、`unsupported_status_stat_request`、`invalid_base_defense`、`invalid_base_speed`、`invalid_speed_multiplier`、`invalid_status_effects`、`status_stat_precision_exceeded` です。開発者は理由に対応する入力を修正して再実行してください。出血後の値が範囲内でも、速度に一時倍率を掛けた途中積が精度上限を超えた場合は拒否します。

状態一覧の検証は、非有限数値・精度超過・Object・非文字列辞書キー・循環・深さ32超過を拒否します。出血より後ろにある不正要素も拒否します。契約は入力一覧をコピーして保持せず、返却値には二つの整数だけを含めます。検証とID走査は入力の要素数に対して線形です。HPMP、状態一覧、個体AI、保存JSON/schema、数値Sessionの形式は変更しません。

呼出元は、成功結果を補正前の数値として再入力しないでください。専用の付与付き物理行動は最新状態と補正前数値を読み直し、補正済み防御力だけを物理予測へ渡します。本契約の純粋計算テストだけを、各戦闘入口への接続完了の証拠とは扱いません。

## 開発者の検証方法

開発者はリポジトリルートで、使えるPythonとGodotを指定して次を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_status_stats.py tests/test_battle_bleeding.py tests/test_gdscript_status_physical.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_stats.py
```

テストは実Pythonの二つのpropertyと実Godotの予測を比較します。保存ダミーの個体・AI・items・party・stateと要求JSONについて、実Godot起動前後のbyte不変も確認します。性能検査は四状態・重複出血・一時速度倍率1.5で正常予測を反復し、防御45・速度55、固定入力、入力保持を照合します。標準は20000回・7サンプル・2000回事前実行、一予測中央値3000us以内です。起動・I/O・戦闘行動・AI・描画・保存は計測しません。

Godot未指定によるskipまたは終了コード2は未検証です。解析エラー・実行診断・値不一致・性能上限超過は失敗です。開発者は原因を解消して再実行してください。実GUI操作、戦闘接続、配布export、リモートCIは本検証の証拠に含みません。

[付与付き物理予測](GDScript状態付与付き物理予測契約.md) / [形式](FORMATS.md) / [移行計画](ワークフロー/GDScript移行実装単位.md)
