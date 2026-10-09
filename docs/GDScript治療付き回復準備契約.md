# GDScriptの治療付きHP回復の実行準備

例えば正規HeroはLv60で精霊回復（spirit_recover）を習得します。開発者がLv59とLv60の個体レコードを既存Builderで再構築して渡すと、この準備契約は両方の開始情報を受理しますが、Lv59による精霊回復の選択は未習得として拒否します。Lv60なら、習得と許可装備を確認した独立したスキル定義を返します。この選択ではMP消費・HP回復・状態治療を実行しません。

この単位の目的は、[治療付き回復予測](GDScript治療付き回復予測契約.md)を今後のSession実適用へ渡す前に、参加者・習得・許可装備・定義と明示初期状態を検証することです。状態を持つ種族や個体の保存形式は新設せず、状態所有者のSession保持と行動予約による実治療は後続へ分けます。

## 開発者が渡す入力と使い方

開発者は、data/を含むプロジェクトルートで初期化した読取専用Repositoryと既存CombatantBuilderから両陣営を再構築してください。Builderの結果をallies/enemiesのteamsへ、正規スキル一覧をskillsへ渡します。正規Lv別習得・＋選択・装備許可の再構築は既存処理へ委譲し、この純粋engineはファイルを読みません。個体レコードのlevelだけを準備処理へ渡す入口ではありません。

その上で、すべての参加者について初期状態をside/id別に明示してください。例えば両陣営にID「same」が一体ずついる場合、次の初期状態を渡します。

```json
{
  "allies": {
    "same": [
      {"id": "lock", "removable": false},
      {"id": "poison", "metadata": {"deck": [1, {"kept": true}]}},
      "sleep"
    ]
  },
  "enemies": {"same": []}
}
```

開発者はengine/cure_heal_skill_context.gdを読み込んだContextから`Context.prepare(teams, skills, initial_statuses)`を呼んでください。成功後は`Context.select(prepared["context"], {"side": "allies", "id": "same"}, "spirit_recover")`で習得済み定義を選びます。味方の状態と敵の空状態は同じIDでも分離します。通常HP回復を選ぶ場合は既存heal_skill_context.selectを使ってください。その通常入口は治療付き定義を引き続き拒否します。

| prepareへの入力 | 必須条件と扱い |
| --- | --- |
| teams | allies/enemies別の参加者列です。各参加者はsnapshot・skill_ids・equipmentを持ちます。既存回復準備と同じ満HP/MP・未逃走・参加数/同陣営ID一意性・習得列・許可装備の検証を使います。 |
| skills | schema_version=1とskills配列を持つJSON由来の正規/互換MOD定義です。開始時にID別索引を作り、選択時に指定IDの一意性と対応効果を検証します。未選択定義の未対応効果は選択済みとして扱いません。 |
| initial_statuses | allies/enemiesだけを持つ辞書です。各陣営の辞書は、その陣営の参加者ID集合と厳密に一致し、各値は状態配列です。状態なしも[]と明示します。 |

初期状態の欠落・余分なID・余分な外側キーは拒否し、空配列を暗黙補完しません。両陣営が空なら初期状態は`{"allies": {}, "enemies": {}}`です。一つの陣営内で同じIDを重複参加させることはできません。

## 状態情報と独立コピーの境界

各初期状態配列の検証とコピーは[状態治療予測契約](GDScript状態治療予測契約.md)へ委譲します。文字列/辞書の順序・未知MOD ID・重複状態・JSON互換の拡張情報を保持し、付与/継続効果を実装済みとは扱いません。認識キーの型不正、非有限値、Object、循環、整数交換精度超過、深さ32超過を拒否します。ここで使う候補選択は一覧の検証であり、治療の成立判定や状態除去は行いません。

成功したprepareはok=trueと次の独立したデータを返します。

| 結果キー | 内容と利用上の境界 |
| --- | --- |
| snapshots | 両陣営の数値開始情報です。identity/stats/hp/mp/fled/aliveの六キーを維持します。 |
| context | 個体別の習得/装備情報とスキルのID別索引です。選択にはこの辞書を渡します。 |
| initial_statuses | 検証済みのside/id別初期状態です。生きた状態所有者やSessionへの登録ではありません。 |

返却辞書は入力原本から独立した、編集可能な通常データです。入力側のネスト編集は準備結果へ伝播せず、選択結果のskillを編集しても元contextは変わりません。ただし返却context自体を編集すれば、以後の選択に使う情報も変わります。不変のSession所有状態や改ざん不能な認証情報として扱わないでください。状態保持には別の[戦闘状態一覧契約](GDScript戦闘状態一覧契約.md)が必要であり、そのSession接続は未実装です。

## スキルと装備の選択条件

selectはside/idだけを持つ参加者キーと、空でないスキルIDを受けます。準備済み個体のskill_idsにIDがあり、そのIDに対応する定義が一つだけで、専用の治療付き回復契約に適合する場合だけ独立skillを返します。attack/defend、未習得、通常HP回復定義、未知/重複定義をこの入口では選択できません。

治療付き定義の必須表示名・kind:heal・正のmp_cost・有限status_cure_chanceなどは[治療付き回復予測契約](GDScript治療付き回復予測契約.md)を正とします。heal_skill_contextの専用入口へ委譲し、通常回復と同じ習得/装備検証を共用します。要求側から検証スクリプトや切替モードを指定する入口は追加しません。

選択IDの装備skill_modifiersは既知の攻撃用power_multiplierだけを許可します。power_multiplierと装備fixed_bonus_damageは不正数値を拒否しますが、Python正本と同様に回復量へ適用しません。未対応の回復補正や未知キーをfalse・0・空でも捨てず拒否します。他IDの修飾情報を今回の回復へ混ぜません。

## 拒否結果と再試行

prepareの拒否はok=falseとreason、必要に応じside/idを返し、snapshots/context/initial_statusesの部分成功は返しません。外側形式不正はinvalid_initial_statuses、ID集合不一致はstatus_context_mismatch、個体内の状態不正は共用契約のinvalid_status_effectsです。開始資源・習得列・許可装備・一覧形式の拒否理由は既存回復準備から返します。

selectの不正開始情報はinvalid_heal_context、不正参加者キーはinvalid_actor_key、参加者欠落はactor_missing、未習得はskill_not_learnedです。未知の装備補正はunsupported_heal_equipment、数値/型不正はinvalid_heal_equipmentです。定義拒否は専用契約の理由を返します。開発者は該当入力を確認し、検証済み情報から再準備/再選択してください。元入力や保存JSONを自動補修しません。初期状態と習得情報を行動要求で上書きする処理もありません。

## 検証の実行と完了確認

開発者はリポジトリルートで使えるGodotとPythonを指定して、次の検証を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_cure_heal_context.py tests/test_gdscript_heal_action.py tests/test_gdscript_cure_heal_skill.py tests/test_gdscript_combatant_status.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --cure-context
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_magic_action.py --heal
```

実Godotテストは正規HeroのLv59/60を既存Builderで再構築し、習得差と定義選択を照合します。初期状態の厳密一致、同IDの陣営分離、空状態、未知情報/ネストの独立保持、不正開始/選択の診断なし拒否、通常回復入口の治療拒否を確認します。正規JSON・専用要求と個体/AI/items/party/stateの保存ダミーはbyte保持を確認し、実セーブは使用しません。

--cure-contextは八体・千件定義を一度だけ準備してから、治療付き定義の選択だけを標準20000回・7サンプル・2000回事前実行で測定します。一回中央値3000us以内と、精霊回復の正常定義・参加数/索引数・準備/入力保持のすべてが一致した場合だけ成功します。初期状態検証・索引構築・起動/I/O・HP/MP実更新・Session・描画・AIの時間は含みません。--healは共用検証を使う既存HP回復行動の回帰性能です。

Godot未指定のテストスキップや性能終了コード2は未検証です。開発者はGodotを指定して再実行してください。解析/実行診断、期待値不一致、性能上限超過は失敗です。治療付き回復のSession実適用・行動票・状態付与/継続効果・AI・戦闘画面・実GUI・配布export・リモートCIはこの単位の検証対象ではありません。正規data/assets、数値snapshot、保存JSON/schemaは変更しません。

[コードの入口](CODEMAP.md) / [移行実装単位](ワークフロー/GDScript移行実装単位.md)
