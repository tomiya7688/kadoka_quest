# GDScriptの状態付与付き単体物理スキル予測

## 背景・目的・対応範囲

物理ダメージ予測と状態付与予測を別々に成功扱いすると、攻撃で倒した対象へ付与したり、不正な付与条件でもダメージだけを採用したりする危険があります。status_physical_skill_contractは両契約を共用し、実ダメージdealtが正で攻撃後HPも正の場合だけ、一件付与を予測します。定義/数値/状態のどれかが不正なら、契約は部分結果を返しません。

本単位はMP付き単体physicalの純粋準備/予測です。正規skills.jsonにはstatus_effectを持つスキルがないため、対応範囲は独立したMOD形式で確認します。契約は正規スキルのIDや内容を変更しません。魔法・複数対象・自傷・回避・反撃・属性耐性・実HPMP/状態更新・行動予約・AI・画面・保存は本単位に含みません。

## 開発者の定義準備と入力例

開発者は、既存物理の対応キーにstatus_effect辞書を加えた定義を、schema_version=1/skills配列へ配置してください。次は検証用MOD定義で、正規スキル追加の指示ではありません。

```json
{
  "schema_version": 1,
  "skills": [{
    "id": "mod_bleed_hit",
    "display_name": "出血打撃",
    "kind": "physical",
    "mp_cost": 3,
    "status_effect": {"id": "bleeding", "display_name": "出血", "chance": 0.4}
  }]
}
```

開発者はGodotの検証スクリプトの関数内で、Contract=preload("res://engine/status_physical_skill_contract.gd")を構築し、prepare(document, "mod_bleed_hit")へ上の辞書を渡してください。prepareはIDの一意性と物理定義を既存physical_skill_contractで検証し、状態定義を既存status_apply_contractで検証します。prepareの成功結果は独立したskill辞書です。

prepareはpower/critical_multiplierの省略値1と、既存物理と同じMP整数化を補います。prepareはstatus_effectのchanceや拡張情報を保持し、入力原本を変更しません。attack/defend・MPなし・kind違い・欠落/重複ID・未知のスキル効果は拒否します。status_effectがない対応物理定義はstatus_effect_requiredです。status_effect={}は既存付与契約の正常なIDなしとして扱います。

## 判定準備と結果予測

開発者は成功したskillと、次のような最新の投影済み数値/状態を渡してください。defenseは状態補正済みの実効防御力です。契約は既に付与されている出血等から防御力を再計算しません。能力補正・種族/装備の状態耐性再構築は呼出元の別責務です。

```json
{
  "attack": 100,
  "defense": 50,
  "target_hp": 1000,
  "current_mp": 100,
  "critical_roll": 0.5,
  "variance": 1.0,
  "status_effects": ["poison"],
  "status_resistance_level": "weak",
  "status_roll": 0.49
}
```

quote_damage(skill, request)は、上の例で物理79ダメージ・対象残HP921・消費後MP97を予測します。対象が生存するので基礎確率0.4/weak耐性から付与確率0.5を得て、roll0.49が未満なら毒の後へ出血一件を予測します。結果はok=true、scope:status_physical_skill_quote、physical、status、status_eligibleです。physicalは既存physical_skill_quote、statusは既存status_apply_quoteを維持します。

開発者は付与乱数を決める前に、status_rollキーを除いたrequestをprepare_quote(skill, request)へ渡してください。prepare_quoteは同じ明示critical_roll/varianceで物理結果を予測し、statusのroll_required/確率/独立候補を返します。準備のscopeはstatus_physical_skill_preparationです。prepare_quoteはstatus_rollをnull/false/0でも拒否します。どちらの入口も乱数を生成しません。

契約はdealt<=0ならstatus_eligible=false/outcome:no_damage、正のダメージで対象残HP0ならstatus_eligible=false/outcome:target_defeatedを返します。契約はこの場合の付与確率を0、roll_requiredをfalseとし、現在状態一覧を保持します。致死やID重複/無効でも、指定済みの不正status_rollは拒否します。非致死で正の付与確率がある場合は、確率1でも明示した0以上1未満の有限status_rollが必要です。

status_effectsは明示した現在一覧で、省略時に空へ補完しません。status_resistance_level省略はnormalです。状態IDの空白・重複・六段階耐性・未知耐性・確率補正・候補のchance除去・表示名/解除可否の補完は[純粋付与契約](GDScript状態付与予測契約.md)を共用します。状態の持続時間や能力低下等の拡張情報は保持するだけで実行しません。

## 拒否・コピー・計算範囲

契約は未知の定義/要求キーをfalse/0/空でも拒否します。契約は検証済みのstatus_effectだけを物理定義の一時投影から除き、他の未対応効果を黙って無視しません。従来物理のprepare/quote_damageはstatus_effectを引き続き拒否します。スキルIDをattackに置き換える処理はありません。

契約は選択候補だけを浅く投影し、一覧全体の再帰コピーを行いません。一覧選択は一回の投影と既存の一意検索による線形処理です。状態ネストと物理数値投影は深いコピー前に共用JSON検査を通し、Object・循環・過深・非文字列キー・非有限/精度超過を拒否します。原本・要求・返却ネストの編集は互いに伝播しません。

契約は物理と現在MPを確認した後に、現在状態/付与判定値を検証します。MP不足はinsufficient_mpで、現在状態やrollの不正より先に拒否します。定義の不正や数値投影の非JSON値はそれ以前の検査です。契約は拒否時にphysical/statusの部分結果を返しません。共用契約の拒否理由は保持します。

新しい入力/結果は内部の実行時形式です。契約は数値Session七キー/個体六キー・保存JSON/schemaを変更しません。予測のHP/MP/状態一覧を外部の実状態上書き命令として使わないでください。実適用は[予約付き状態付与](GDScript予約付き状態付与契約.md)等の所有者へ、別の行動単位で接続してください。

## 検証方法と完了確認

開発者はリポジトリルートで使えるGodot/Pythonを指定し、次を実行してください。共用fixtureは要求と個体/AI/items/party/stateの保存ダミーのbyte保持を確認します。正規JSONは読取専用で、開始前後のbyteも確認します。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_status_physical.py tests/test_gdscript_physical_skill.py tests/test_gdscript_status_apply.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_physical.py
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_physical_skill.py
```

テストは実Python _attackを学習なし・反撃なし・明示乱数で呼び、実HP減少と状態付与・付与乱数要否を実Godotへ照合します。テストはPython個体の既存状態による防御補正と、予測の補正済みdefenseを一致させます。消費後MPは純粋予測式の比較で、実MP消費の証拠ではありません。定義準備/ID・正規データ対応範囲・不正/未知/native値・致死roll・MP不足順・原本/返却独立性も確認します。

性能検査は非致死79ダメージ・残HP921/MP97・出血一件成功を毎回予測し、固定原本と実結果を照合します。標準20000回・7サンプル・2000回事前実行で、一予測中央値3000us以内が上限です。致死/重複/拒否だけの高速結果で通過しません。起動/I/O・一覧prepare・実更新/予約・能力/耐性再構築・AI・描画・保存は測りません。

Godot未指定のskip/終了コード2は未検証です。開発者はGodotを指定して再実行してください。解析/実行診断・期待値不一致・時間超過は失敗です。付与付き攻撃の実行準備/習得・Session/Application行動接続・魔法/全体・実GUI・配布export・全E2E・リモートCIは未接続/未検証です。

[既存物理契約](GDScript物理スキル予測契約.md) / [形式](FORMATS.md) / [コード入口](CODEMAP.md) / [移行単位](ワークフロー/GDScript移行実装単位.md)
