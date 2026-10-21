# GDScript速度強化スキルの純粋予測契約

## 背景・目的

低水準の速度所有者は、倍率の保持・再付与・期限切れ復元に対応しています。ピオラを戦闘へ接続する前に、スキル定義の対応範囲と抽選前の期間条件を検証する必要があります。

`gdscript/engine/speed_buff_contract.gd` は、正規ピオラと互換MOD定義から、倍率・期間条件・対象方針・消費後MPを予測します。速度強化予測は純粋な計算であり、実MP・速度倍率・残り期間・予約・セーブを変更しません。

## 呼び出し元と責務

開発者は `prepare(document, skill_id)` へスキル一覧を渡してください。prepareは共用の一覧選択でschema_version=1・指定IDの存在と一意性を確認し、速度強化の検証へ委譲します。

開発者は `quote_buff(definition, {"current_mp": 10})` へ定義と現在MPを渡してください。quote_buffは直接渡された定義も再検証し、MP不足を拒否してから抽選前の予測を返します。現在MPは、0以上9007199254740991以下の整数または整数値のfloatで指定してください。現在MPのbool・文字列・小数部分・非有限値は拒否します。

速度強化の定義検証・期間条件の補正は本契約が担当します。実倍率の最大値更新と期限経過は既存の[速度所有者](GDScript一時速度強化保持契約.md)が担当し、[予約付き付与](GDScript予約付き速度強化契約.md)と[ラウンド終端](GDScript速度強化ラウンド終端契約.md)の規則を本契約へ複写しません。

## 対応する定義

速度強化定義は、id・display_name・kind・speed_multiplier・mp_costと、任意のdescription・duration・targetだけを持ちます。

- 速度強化定義のkindはbuff、idは空でない文字列で、attack/defendは使用できません。
- 速度強化定義のspeed_multiplierは正の有限数値で、mp_costは0方向へ整数化した結果が正になる値です。共用数値変換は数値文字列を受け付けます。mp_costの文字列は整数表記に限定します。
- 速度強化定義の数値変換は、絶対値9007199254740991を超える値、bool、非有限値を拒否します。
- 速度強化定義のtarget省略時は、生存友軍の現在速度倍率が最小の個体を選ぶPythonの方針をtarget_policy=lowest_speed_multiplierとして返します。target=selfならtarget_policy=selfを返します。本契約は個体を選びません。同値時の選択順や生存確認は、この予測の実装済み範囲ではありません。
- 速度強化定義の未知キーは、値がfalse/0/nullでも拒否します。攻撃強化・全体対象・治療・状態付与・属性効果を省略して成功とすることはありません。

検証済みskillは原本と独立したコピーです。検証済みskillの倍率とMP消費は数値へ、durationはnull・正整数・補正済み二要素配列へ正規化します。duration省略時も検証済みskillへduration=nullを加えます。

## 抽選前の期間条件

| duration入力 | 予測のduration条件 |
| --- | --- |
| 省略またはnull | mode=untimed、minimum/maximum=nullです。 |
| 有限単値 | Pythonのintと同じ0方向切捨ての後、最低1へ補正し、mode=fixedと同値のminimum/maximumを返します。 |
| 二要素配列 | 両端を0方向へ整数化し、minimum=max(1, 下端)、maximum=max(minimum, 上端)としてmode=rangeを返します。 |

期間の数値文字列は整数表記に限定します。配列要素にも単値と同じ型・有限性・精度上限を適用します。配列の要素数が二以外の場合、不正型、変換不能、非有限値、精度超過の場合はinvalid_speed_buff_durationを返します。

Pythonの期間処理は一部の不正期間を無期限へ読み替え、三要素以上の配列では先頭二要素だけを使います。本契約は、その不正入力の読み替えや余分な要素の無視を引き継がず、理由付き拒否に限定します。対応する有限単値・二要素範囲の補正は実Pythonと照合します。

範囲のmaximumは抽選時の上端も含みます。本契約は乱数源を呼ばず、範囲内の一期間を選択しません。固定期間と無期限の場合も、実付与を実行するわけではありません。

## 正規ピオラの結果と失敗

正規ピオラの倍率は1.5、期間は[3, 6]、消費MPは5です。現在MP10でのquote_buffは、次の独立した辞書を返します。

```json
{
  "ok": true,
  "scope": "speed_buff_quote",
  "skill_id": "piora",
  "multiplier": 1.5,
  "duration": {"mode": "range", "minimum": 3, "maximum": 6},
  "target_policy": "lowest_speed_multiplier",
  "mp_cost": 5,
  "remaining_mp": 5
}
```

失敗結果はok=falseとreasonだけを返し、部分的な倍率・MP予測を返しません。MP不足はinsufficient_mp、未知の要求キーはunsupported_speed_buff_requestです。定義・一覧・期間・資源の不正は、それぞれ具体的なreasonで区別します。呼び出し元は失敗理由に対応する定義または要求を修正してから再実行してください。

## 開発者の確認方法

本契約には利用者が直接操作する画面はありません。開発者はリポジトリルートでKADOKA_GODOT_EXECUTABLEへ使用できるGodotを設定し、実セーブと独立した保存先を指定して次のテストを実行してください。

```text
python -m pytest tests/test_gdscript_speed_buff.py
python tools/performance-check/script/check_gdscript_speed_buff.py
```

実Godotプローブは正規定義・互換MOD・MP境界・拒否・入力不変・返却値の独立性を確認します。Python比較は実際の_buff_durationへ明示した乱数戻り値を渡し、抽選上下限と単値補正を照合します。

標準性能CLIは20000回・7サンプル・2000回事前実行で予測一回を測り、中央値3000us以内と固定予測・元MP10・入力保持・反復条件を要求します。Godot未指定は終了コード2の未検証です。少数回のテスト実測や検証器テストの合成時間は、標準性能検査の成功証拠と区別します。

期間抽選・対象選択・習得/装備確認・MP実消費・予約付き行動への接続・AI・戦闘画面は未接続です。既存の魔法・HP回復入口は引き続き速度強化定義を拒否します。保存JSONとPythonゲーム処理は変更しません。
