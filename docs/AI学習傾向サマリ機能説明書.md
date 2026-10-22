# AI学習傾向サマリ（Issue #183）

## 範囲

`AiInspector.summarize_tendencies(ai, skills)` は個体の既存AIと、スキルIDをキーにした定義辞書から5行のplain dataを返す。計算は `core/ai_tendencies.py` に委譲し、I/O・pygame・永続キャッシュを持たない。旧 `summarize` APIは維持する。#184で両管理画面へ組込み済み。表示と操作は [個体AI可視化](個体AI可視化機能説明書.md) を参照。

学習アルゴリズム・保存JSON形式は変更しない。プロファイル、作戦、初期 `kind_preferences`、固定 `weights` は学習結果として使わない。

## 指標

| id / 表示名候補 | 使用する学習値 | 正側 / 比較側 |
| --- | --- | --- |
| aggression / 攻撃性 | action_preferences | 攻撃 / その他 |
| healing / 回復優先 | action_preferences | heal / その他 |
| mp_economy / MP節約 | context_preferences の mp:low | MP消費0 / MP消費あり |
| critical_defense / 瀕死時防御 | context_preferences の self:critical | defend・evade / その他 |
| stronger_aggression / 格上への強気 | context_preferences の threat:stronger | 攻撃 / その他 |

攻撃は physical・magic・drain_mp・random。その他の対応種別は heal・defend・evade・buff。field_only、未対応種別、定義不明IDは除外する。MPコスト省略はゲームと同じ0として扱い、不正値はMP節約の分類対象にしない。MODスキルもID名ではなく定義で分類する。

## 値と段階

正側・比較側それぞれの**記録済み**スコアの平均を使う。未記録スキルは平均の分母へ加えず、片側に記録がない場合はその平均を0（未学習の基準値）とする。両側の分類が定義辞書に存在し、少なくとも片側に有効な記録が必要。

学習上限 B は全体1、状況別0.6。入力を ±B に制限し、`round(50 + 50 * (正側平均 - 比較側平均) / (2 * B))` で0～100へ変換する。bool、非数値、NaN/無限大は無視する。

`stage` は 0～19: very_low、20～39: low、40～59: neutral、60～79: high、80～100: very_high。数値は学習の偏りの相対表示であり、行動の選択確率やスキル使用率ではない。実際の推論には作戦・HP・MP・使用可能スキル等も影響する。

## 状態とデータ不足

各行は `id, context, state, observations, value, stage, reason` を持つ。contextは全体指標でnull。

- `unlearned / no_records`: 該当スコアも行動記録もない。値・段階はnull。
- `insufficient / few_observations`: 全体はactions、状況別はcontext_actionsの該当件数が5未満、または件数不明。旧データに状況別スコアだけあって件数がない場合も含む。
- `insufficient / no_comparison`: 比較する2種類の分類が定義辞書にない。
- `insufficient / no_known_preferences`: 対応する有効な学習値がない。
- `ready`: 5件以上かつ上記比較が可能。value・stageを返しreasonはnull。

5件は表示開始の暫定的なしきい値であり、統計的信頼度を保証しない。件数は全行動/状況の合計で、カテゴリごとの使用件数ではない。現保存形式からそれを推定しない。未学習を中立50と混同せず、十分な件数の記録済み0点だけを中立として返す。

都度計算するため学習後に更新され、AIリセット後は未学習へ戻る。余分な派生パラメータをセーブへ追加しない。管理画面は表示中個体のAIとスキル定義を渡す。

## 検証

`tests/test_ai_tendencies.py` は実際の学習呼出し、同種族の履歴差、少数記録、状況別件数、MOD定義、非破壊性、異常値、保存/再読込/リセットを検証する。両管理画面の表示は `tests/test_ai_tendency_ui.py` で検証する。
