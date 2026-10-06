# GDScript移行の実装単位

現在の最優先の開発方針はGDScript版への移行。通常の移行作業は `gdscript` と `priority: p1` を付け、同じP1の他作業より先に扱う。P0は待たせられない緊急障害の復旧だけに残す。移行完了またはユーザーの方針変更時に、この優先枠を見直す。

既存のマップ/移動/位置保存、初期個体・一覧、現在編成、プリセットはローカル実装済み。#10/#111はディレクトリの境界であり、GDScript本体の全機能移植を追うIssueではない。未移植機能は以下の小単位で進める。

| Issue | 実装単位 | 依存 | 状態 |
| --- | --- | --- | --- |
| [#218](https://github.com/tomiya7688/kadoka_quest/issues/218) | 牧場台帳→既存一覧/編成/プリセット | 既存のGodot管理画面 | ローカル実装済み（未push、検証はver#76） |
| [#219](https://github.com/tomiya7688/kadoka_quest/issues/219) | Lv別基礎能力値・習得スキル | 既存の個体/種族読込 | ローカル実装済み（未push、検証はver#77） |
| [#220](https://github.com/tomiya7688/kadoka_quest/issues/220) | ＋選択・装備制限/補正 | #219 | ローカル実装済み（未push、検証はver#78） |
| [#221](https://github.com/tomiya7688/kadoka_quest/issues/221) | 通常攻撃・防御・会心の数値契約 | #220 | ローカル実装済み（未push、検証はver#79） |
| [#222](https://github.com/tomiya7688/kadoka_quest/issues/222) | 固定モブの時間周期移動/占有 | 既存のFieldEngine/Session | ローカル実装済み（未push、検証はver#80） |
| [#223](https://github.com/tomiya7688/kadoka_quest/issues/223) | 会話デッキと正面での移動停止 | #222 | ローカル実装済み（未push、検証はver#81） |
| [#224](https://github.com/tomiya7688/kadoka_quest/issues/224) | 湧き場の7文字暗号入力/仮想キーボード | #223 | ローカル実装済み（未push、検証はver#82） |
| [#225](https://github.com/tomiya7688/kadoka_quest/issues/225) | 暗号一致後のまる/かどか取得・保存 | #224 | ローカル実装済み（未push、検証はver#83） |
| [#226](https://github.com/tomiya7688/kadoka_quest/issues/226) | 教会イベントの復活地点登録・保存 | 既存の名前付き保存/#225までのScene | ローカル実装済み（未push、検証はver#84） |
| [#227](https://github.com/tomiya7688/kadoka_quest/issues/227) | 戦闘個体のHP/MP・生死状態 | #219/#220/#221と#226までの移行 | ローカル実装済み（未push、検証はver#85） |
| [#228](https://github.com/tomiya7688/kadoka_quest/issues/228) | ラウンドの行動順・実行可否契約 | #227 | 次の未対応単位 |

各IssueのGoal / Required / Acceptance / Read scopeを正とし、ここへ詳細仕様を複写しない。上の移行順はGitHubのblocked-byにも登録した。#224の一致結果を#225の保存確認後の成功へ接続した。#226は復活地点の登録だけで、実際の敗北→教会復活を代用しない。#227は補正済み能力値から戦闘実行時状態への契約を準備し、#228で行動順/最新の生存者による実行可否へ進む。戦闘Scene/全スキル/AI/勝敗はさらに後続へ分ける。別の未移植機能（野生/個体編集/各エディタ/export等）は、前提が明らかになった段階で同様に起票する。この表だけでゲーム全体の移植を完了できるとは扱わない。

## 進め方

1. リモート取得と作業ツリー確認後、P0の緊急性を確認する。通常はP1のgdscript単位から依存順に1件選ぶ。
2. `start_task.bat` の候補がローカル実装済みなら再実装せず、この表・コミット・Issueの進捗を確認して次の未対応単位へ進む。
3. 未移植機能を代替の成功処理で埋めず、純粋engine / data I/O / application調停 / UIを分ける。既存JSONを直接使い、実セーブを検証に使わない。
4. 実GodotとPython正本の比較、関連/全テストと更新履歴を残す。手動画面・export未検証は区別する。
5. ローカル実装済みとGitHubにコード反映済みを区別する。未pushの間はIssueを閉じず、ローカルコミットと検証範囲を記録する。push/PR/完了操作は明示的な指示に従う。
