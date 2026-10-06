# GDScript物理スキル予測契約

## 背景・目的

通常攻撃と基本ぼうぎょを戦闘Sessionへ接続した次の段階として、MPを消費する単体物理スキルが必要になります。通常攻撃APIへ別のスキルをattackとして渡すと、ID別の装備補正やMP消費の意味が変わります。

本単位の目的は、正規スキルの定義と必要なMPを確認し、Python版と同じダメージ数値を予測できるようにすることです。予測APIは資源を変更しません。行動権の取得、最新の生死・習得済みスキルの確認、SessionでのMP支払いとHP適用は後続の実装単位です。

## 手段と責務

- engine/physical_skill_contract.gdは、正規skillsから指定したIDを検証し、MP不足を判定して予測結果を返します。ファイルI/O、Session、AI、描画には依存しません。
- engine/attack_numbers.gdのphysical_damageは、通常攻撃と物理スキルの数値計算を共用します。通常攻撃専用のnormal_attackは引き続きattackだけを受け付けます。
- data/application/UIには接続しません。既存の通常攻撃・基本防御の行動APIと保存形式は変更しません。

## 定義の入力

prepare(document, skill_id)はschema_version=1とskills配列を受け取り、指定IDが一つだけ存在することを確認します。他のスキル定義を削除・修復せず、選択した定義だけを検証します。成功時は独立したskill辞書を返します。

許容する定義キーはid、display_name、description、kind、power、mp_cost、critical_multiplierです。idと空でないdisplay_nameが必要です。表示説明は文字列です。kindはphysical、idはattackとdefend以外です。

mp_costはPythonのintと同じ0方向切捨てで正の整数へ変換します。有限の数値と整数文字列を受け付けますが、ゼロ・負値・bool・欠損・非有限値・精度範囲外を拒否します。powerとcritical_multiplierは省略時1.0です。有限の数値文字列も扱います。有限MODの負の威力や会心倍率を、黙って別の値へ修復しません。

正規のたいあたり、ころがる、つつくを扱います。同じ形式のMODスキルもIDを固定せず扱います。element、target、status_effect、self_damage_ratio、反撃、庇い、全体攻撃、randomなどの未対応指定は、falseや空でも拒否します。

## 予測の要求と結果

quote_damage(definition, request)は、prepare後のskillまたは同形式の定義を再検証します。要求の許容キーは次のとおりです。

| キー | 内容 |
| --- | --- |
| attack / defense / target_hp | 攻撃力、防御力、現在HP。既存の数値変換規則を共用します。 |
| current_mp | 必須の非負整数。JSONの整数値を表すfloatも受け付けますが、小数・文字列・boolは拒否します。 |
| critical_roll / variance | 明示する会心乱数（0以上1未満）と揺らぎ（0.92以上1.08以下）。 |
| attack_multiplier / guard | 省略時1.0の攻撃倍率・物理防御倍率。 |
| power_multiplier / fixed_bonus_damage | 省略時1.0と0の装備数値投影。装備JSONや許可判定そのものではありません。 |

MPが不足している場合はinsufficient_mpを返します。未知キーと不正数値も理由付きで拒否します。要求からpowerやskill_idを上書きできません。

正常な例は次のとおりです。

    definition = {"id":"body_bash","display_name":"たいあたり","kind":"physical","power":1.2,"mp_cost":3}
    request = {"attack":100,"defense":50,"target_hp":1000,"current_mp":10,
               "guard":0.5,"critical_roll":0.5,"variance":1.0}

この入力ではdamage=49、dealt=49、remaining_hp=951、remaining_mp=7を予測します。成功結果にはok、scope:physical_skill_quote、skill_id、mp_cost、remaining_mpと、既存の物理数値結果を含みます。残MPは予測であり、実際に支払ったことを意味しません。

攻撃倍率の0方向切捨て、スキル威力と装備威力の乗算、会心判定、通常時だけの防御減算、基礎値の切捨て、固定追加、物理guardと揺らぎ、最低1、実HP減少の上限をPythonと同じ順序で計算します。会心率はmin(1, (1/16) × critical_multiplier)で、会心時は相手の防御力を無視します。

呼出元は、正規の装備許可・ID別効果から数値を投影してください。通常attack向けの補正を他スキルへ使わないでください。このAPIだけで装備、習得、参加者の生死、逃走、特殊効果の適用許可を判断しないでください。直接の数値契約なので、target_hp=0でも予測できますが、死亡対象へ行動できるという意味ではありません。

## 開発者の実行方法

ゲーム画面からの直接操作はまだありません。これは内部契約と開発者用の検証です。Pythonの検証環境を用意し、実Godotのパスを設定してください。リポジトリのrootで次のコマンドを実行してください。

    $env:KADOKA_GODOT_EXECUTABLE = '<Godot console実行ファイルの絶対パス>'
    & '<検証用Pythonの絶対パス>' -m pytest tests/test_gdscript_physical_skill.py tests/test_gdscript_attack_numbers.py -q
    & '<検証用Pythonの絶対パス>' tools/performance-check/script/check_gdscript_physical_skill.py

テストは専用の一時fixtureを作り、実GodotとPython BattleEngine._attackを比較します。成功時はテスト件数と性能結果を表示します。Godotを指定していない場合は実エンジンテストをskipし、性能検査はexit2/Unverifiedを返します。未指定・失敗を成功として扱わず、パスと診断を確認して再実行してください。

性能検査は標準20000回・7samples・2000warmupの予測一回分の中央値を測り、3ms以内と期待結果・入力不変を確認します。初期起動・定義I/O・warmupは計測外です。Session、描画、AI、FPS、保存性能の代わりにはしません。

## 検証境界と次の実装

正規3スキルと有限MOD、会心境界、guard、装備数値、最低1・HP上限、MP不足・ちょうど消費できる予測、未知効果、非有限値、精度超過、コピー独立性を検証します。比較は実Pythonの物理数値だけで、AI選択や学習、実MP支払いの比較ではありません。

次の単位では、正規定義・習得済みスキル・装備効果を戦闘開始時に準備し、現在offeredのticketと最新資源を再確認して、単一claim→MP支払い→HP適用→finishへ接続します。MP不足や不正要求では資源とcursorを消費しない契約が必要です。

戦闘Scene、全スキル、属性耐性・状態異常、特殊防御、AI、勝敗・報酬・復活、実GUI、配布export、リモートCIはこの単位の完了範囲に含めません。
