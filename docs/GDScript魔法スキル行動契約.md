# GDScriptのMP付き単体魔法行動契約

## 背景・目的・範囲

GDScriptの魔法予測はHP/MPを変更しないため、そのままでは魔法を実行できません。この単位は、正規データからの準備と、Sessionの最新予約・資源へ単体魔法を一度だけ適用する経路を追加します。戦闘画面・AI選択・学習は接続しません。

通常魔法の入口は正規weakenと同形式のMODに対応します。自傷付きmetal_burstは別の[自傷魔法行動契約](GDScript自傷魔法行動契約.md)の専用入口を使います。この通常入口では自傷・吸MP・ランダム・状態異常・回避・反撃・全体攻撃を拒否します。未対応のキーは値がfalse・0・空でも拒否し、効果を省略した成功にしません。

## 責務と開始情報

- combatant_builderは既存のレベル・＋選択・装備許可の再構築に、種族species.jsonの読込と属性耐性の準備を加えます。種族定義は構築処理の存続中だけ共用します。
- elemental_resistanceは種族resistancesへ許可済み装備resistance_stepsを反映します。段階順はweak→normal→strong→immune→absorbです。補正量はPythonと同じ整数変換後に加え、段階の両端で止めます。省略はnormal、未知名は補正時だけnormalを基準にします。＋選択は正本Pythonでも耐性を変えません。
- magic_skill_contextは既存physical_skill_contextの開始情報検証だけを共用し、物理スキル選択は呼びません。習得・許可装備・定義ID索引・耐性を独立コピーで保持します。共用検証の失敗reasonには既存のphysicalという名前が残ります。
- magic_skill_actionは最新の行動予約と資源を検証し、MP・HPの更新をSessionへ委譲します。battle_session_applicationは準備と行動処理への委譲だけを担当します。

開始情報は両陣営それぞれ最大4体で、各個体はsnapshot・skill_ids・equipment・resistancesを持ちます。資源snapshotは従来のidentity・stats・hp・mp・fled・aliveの6キーだけです。新規の保存キーやJSON形式は追加しません。開始時HP/MPは最大値、fled=falseでSessionと一致する必要があります。開始後の再設定や定義差替えは拒否します。

## 行動要求と適用手順

開発者は初期化済みbattle_session_applicationへ、next_actorが提示した未取得のticketと、敵のside/idを指定してください。

```gdscript
var result = battle.resolve_magic_skill({
    "ticket": offered["pending"]["ticket"],
    "target": {"side": "enemies", "id": "enemy"},
    "skill_id": "weaken",
    "variance": 1.0
})
```

要求はこの4キーだけです。会心値・威力・MP・耐性・装備・防御倍率を追加して上書きできません。varianceは有限値の0.92〜1.08で、既存数値契約の数値文字列変換にも対応します。乱数源はActionへ持ち込まず、呼出元が揺らぎを明示します。

行動処理は、現在offeredのticket・習得・一意な対応定義・許可装備・敵対象・最新MP/HPを更新なしで確認します。成功した場合だけ、一回分のclaim→実MP支払い→HP適用→finishを同期実行します。途中にawaitやcallbackを挟みません。

魔法は物理防御力・会心・基本ぼうぎょの軽減・装備の物理用power_multiplierを使いません。選択IDのpower_multiplierは既知の有限数値として検証だけ行い、正本Pythonと同様に魔法威力へ加えません。固定追加ダメージは通常ダメージだけへ適用し、無効・吸収では使いません。数値式は[魔法予測契約](GDScript魔法スキル予測契約.md)と共用します。

## HP回復と結果

無効でもMPは消費します。属性吸収では対象HPを回復し、最大HPとの差分までで止めます。満タンでもMPは消費し、実回復量は0です。死亡した敵を魔法の対象にできないため、吸収で敵を蘇生しません。

combatant_state.healとSession.healは非負の正規整数を受ける数値資源操作です。不正値・非有限値・精度上限超過を拒否し、逃走を解除しません。この低水準操作自体には蘇生可否や教会移動の方針を持たせず、魔法行動側で生存対象を制限します。

実行成功はok=true・executed=true・scope=explicit_magic_skill_only・numbers・spent_mp・sessionを返します。numbersには最新HPからの予測、属性名・既知判定・実ダメージまたは実回復量・残MPがあります。返却値の編集はSessionや開始情報を変更しません。

不正要求・未習得・MP不足・未対応効果・死亡対象・使用済み/取得済みticketはok=falseとreasonで拒否します。claim前の拒否は提示中の予約と資源を保持するため、開発者は同じ予約で別の対応行動を指定できます。予約後に行動者が死亡・逃走した場合や敵が不在になった場合は、Sessionが予約を取り消し、ok=true・executed=falseを返します。MPは払いません。

## 開発者の検証方法

リポジトリのルートで、利用できるGodotとPythonを指定してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_magic_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_magic_action.py
```

テストは専用data/assets・個体/AI/items/partyを使い、Pythonの選択だけを固定して実MP支払いと魔法のHP変化を比較します。7種族のレベル・許可装備からの耐性再構築、段階補正、拒否と取消、コピー独立性、8体のラウンド間MP保持を確認します。利用者の実セーブを書きません。

性能検査は8体Sessionの次行動取得→検証→claim→MP→HP→finishを1行動ずつ測り、8行動ごとのラウンド準備を含めます。標準20000回・7サンプル・2000回warmup、中央値3ms以内に加え、実MP消費と通常・無効・吸収・強耐性のHP変化を確認します。起動・読込・開始時再構築・描画・AI・保存・8行動一括の性能は計測しません。

Godot未指定によるスキップや性能CLIの終了コード2は未検証です。開発者はGodotを指定して再実行してください。解析/実行エラー、資源不一致、時間超過は検証失敗です。開発者はreasonと診断を確認し、原本を自動補修せず入力や実装を修正してください。

## この単位で保証しないこと

全スキル、AI推論・学習、戦闘画面、演出、野生遭遇、勝敗・報酬・教会復活、実GUI、配布export、リモートCIは保証しません。ローカル実装と公開反映は別であり、この単位はIssue作成・状態変更・push・PRを行いません。

[コードの入口](CODEMAP.md) / [GDScript開発案内](../gdscript/README.md)
