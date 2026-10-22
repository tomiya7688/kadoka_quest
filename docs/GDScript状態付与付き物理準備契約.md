# GDScriptの状態付与付き物理スキル実行準備

## 背景・目的・境界

物理ダメージと状態一件の[純粋予測](GDScript状態付与付き物理予測契約.md)だけでは、指定したモンスターの習得・装備許可や、戦闘参加者の初期状態/状態耐性は保証できません。status_physical_skill_contextは、戦闘を開始する前の数値資源・習得/許可装備・定義索引・初期状態・状態耐性を共用契約で検証し、独立した実行準備を返します。

本単位は純粋な準備と定義選択です。準備契約はHP/MP消費、ダメージ、状態付与、行動権取得、Sessionへの保持、Application登録、AI、画面、保存を実行しません。準備結果の非公開保持と最新予約/資源/状態の検査は、[専用の非消費検査](GDScript状態付与付き物理検査契約.md)へ接続しました。初期状態の能力/速度補正、行動可否、ターン末効果も実行しません。数値snapshot六キーとSession七キー、保存JSON/schemaは変更しません。

## 開発者が渡す入力と使い方

開発者はdata/を含むプロジェクトルートを読取専用Repositoryへ指定し、application/combatant_builder.gdのBuilderで保存個体レコードを再構築してください。Builderはレベル別習得・＋選択・装備品側の種族許可を共用し、数値snapshot、skill_ids、許可済みequipment、属性resistancesに加え、独立したstatus_resistancesを返します。Builderは元の個体や学習AIへ書き戻しません。

開発者は、再構築した両陣営をteams、schema_version=1/skills配列の定義一覧をskills、全参加者の明示状態をinitial_statusesとして、engine/status_physical_skill_context.gdのContext.prepare(teams, skills, initial_statuses)へ渡してください。直接の数値要求を使う検証では、各参加者にsnapshot・skill_ids・equipment・status_resistancesを明示してください。status_resistancesの欠落は、全状態normalを表す空辞書と区別して拒否します。

例えば両陣営にID「same」が一体ずついる場合、初期状態は次のように指定します。

```json
{
  "allies": {"same": ["poison", {"id": "mod", "metadata": {"deck": [1, true]}}]},
  "enemies": {"same": []}
}
```

prepareは満HP/MP・未逃走・最大四体/陣営・同陣営ID一意性・習得列・装備許可をphysical_skill_contextへ委譲します。teams/skillsは深いコピー前に共用JSON検査を通し、Object/循環、非有限/精度超過、非文字列辞書キー、深さ32超過を拒否します。未知の選択対象効果を削って成功扱いする処理はありません。

initial_statusesはallies/enemiesだけを持ち、各陣営のID集合が数値参加者と厳密に一致する必要があります。状態なしも[]と指定してください。空の両陣営は空のID辞書を明示します。同じIDでも陣営が違えば状態と耐性は分離します。

## 共用初期状態検証と返却形式

initial_status_map.prepareは、既存の参加者一致検査とstatus_effect_contract.valid_effectsで各状態配列を検証します。状態順序・重複・未知IDとJSON互換拡張情報を保持し、状態候補の選別や付与確率の計算は行いません。治療付き回復も同じ検証へ委譲し、複数の不正一覧があっても数値参加者の順で最初の拒否対象を返します。

prepareがすべて成功した場合の結果はok、snapshots、context、initial_statusesです。snapshotsは両陣営の数値六キーを維持します。contextはmembers/definitionsで、membersの各side/idにはskill_ids・equipment・status_resistancesを保持します。definitionsは重複を残したID別索引で、未選択の未対応定義を勝手に消しません。

準備結果・入力原本・選択結果のネストは独立します。ただし返却contextは編集可能な通常データで、認証情報や不変のSession所有状態ではありません。開発者がcontextを編集すれば、以後の選択に使う習得や定義も変わります。prepareの成功を、戦闘への登録や状態付与の完了として扱わないでください。

## 習得と装備からの定義選択

開発者は、成功したcontextとside/idだけの参加者キー、スキルIDをContext.select(context, actor, skill_id)へ渡してください。selectは開始時の習得を確認し、一意な定義をstatus_physical_skill_contractで検証します。状態辞書status_effectを持つMP付き単体physicalだけを選び、attack/defend、未習得、未知/重複ID、付与なしの通常物理を拒否します。正規skills.jsonには付与定義がないため、選択の互換確認は独立MODで行います。

physical_skill_contextの通常selectと専用select_status_physicalは、習得/装備検証だけを共用します。各公開入口が定義契約を固定し、生の要求からmodeやスクリプトを指定できる入口は追加しません。通常の物理入口はstatus_effectを引き続き拒否します。

成功したselectは独立skillと、選択IDの装備power_multiplier/fixed_bonus_damageを返します。選択ID以外の補正は混ぜず、未知の選択ID効果はfalse/0/空でも拒否します。数値変換は既存の物理契約と共用します。MP支払可否は実行時の最新資源で判断するため、本準備は開始時の満MPだけを検証し、実MP支払いを行いません。

ID索引は準備時に一度だけ作ります。個々の選択は全カタログを再走査せず、選択IDの候補と個体の習得/装備だけを確認します。prepareの全JSON/参加者検証は開始時の処理で、毎行動のホットパスへ持ち込みません。

## 種族の状態耐性と属性耐性の分離

status_resistance.prepareは種族のstatus_resistancesを検証し、省略時だけ空辞書へ補完します。状態IDは空でない文字列、耐性名は文字列を要求します。検証は未知の文字列耐性名も保持し、付与確率の解釈は既存status_apply_contractへ任せます。省略IDはnormal、未知の耐性文字列も現行付与契約と同じ通常倍率で扱い、absorb/reflect/immuneは付与を無効にします。

PythonのBattleDataLoaderは状態耐性を種族から取得し、装備resistance_stepsは属性耐性だけへ反映します。Godot Builderも同じ種族読込キャッシュから属性耐性と状態耐性を別々に構築します。＋選択・装備の属性段階を状態耐性へ加算せず、装備品に状態耐性の新パラメータも導入しません。

### 正規説明と耐性値の既存相違

data/species/metal_slime/species.jsonの説明は「毒以外の状態異常に弱い」としていますが、現在のstatus_resistances.bleedingはimmuneで、Python正本も出血を無効にします。本単位は、説明を根拠に耐性バランスを変更せず、現行JSONとPythonの実際の再構築結果へ合わせています。説明と数値のどちらを仕様として変更するかは未確定のため、正規データの文言/値は保持し、この相違を明示します。

## 失敗条件と再試行

prepareの拒否はok=falseとreason、初期状態では必要なside/idを返します。失敗時にsnapshots/context/initial_statusesの部分成功は返しません。共用資源/習得/装備/初期状態の理由は保持し、準備入力を自動補修しません。teams/skillsの非JSON値はinvalid_status_physical_payload、状態耐性の欠落/型不正はinvalid_status_resistancesです。

selectの不正索引形式はinvalid_physical_context、不正参加者キーはinvalid_actor_key、参加者不在はactor_missing、未習得はskill_not_learnedです。定義・装備の拒否理由は専用予測/既存物理と共用します。開発者は拒否理由に該当する入力を修正して再準備/再選択してください。拒否時に資源/状態/予約/保存を更新する処理はありません。

## 検証の実行方法と未接続範囲

開発者はリポジトリルートで使えるPython/Godotを指定し、次を実行してください。実セーブではなく、共用fixtureの要求と個体/AI/items/party/stateの保存ダミーを使い、正規JSONも読取専用でbyte保持を確認します。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_status_physical_context.py tests/test_gdscript_cure_heal_context.py tests/test_gdscript_physical_action.py tests/test_gdscript_magic_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_physical.py --context
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --cure-context
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_physical_action.py
```

テストは正規八種族と未装備/スライムのけん/かるい服の再構築結果を実Pythonへ照合し、スライムLv6/7の習得境界を確認します。Lv別選択テストは正規body_bashのコピーへ状態効果を足した比較用MODで、正規スキルの変更ではありません。初期状態の厳密一致/拒否順、同ID陣営分離、未知情報、JSON/native不正値、選択拒否、入力/返却独立性も確認します。

--contextは八体/千定義を一度準備し、標準20000回・7サンプル・2000回事前実行で選択の中央値3000us以内を確認します。検査は固定した付与定義・装備倍率2/加算3・初期状態/耐性・数値六キー・原本保持を別の期待値へ照合し、高速拒否だけでは通過しません。起動/I/O、索引作成/初期状態検証、HPMP実更新、予約、AI、描画、保存は測りません。

Godot未指定のskip/性能終了コード2は未検証です。開発者はGodotを指定して再実行してください。解析/実行診断、期待値不一致、時間超過は失敗です。専用開始・Applicationの非消費検査と、状態補正済み防御で実更新する[専用行動](GDScript状態付与付き物理行動契約.md)は接続しました。AI・画面は未接続で、実GUI、配布export、全E2E、リモートCIは未検証です。

[予測契約](GDScript状態付与付き物理予測契約.md) / [治療付き回復準備](GDScript治療付き回復準備契約.md) / [戦闘資源](GDScript戦闘個体状態契約.md) / [形式](FORMATS.md) / [入口一覧](CODEMAP.md) / [移行単位](ワークフロー/GDScript移行実装単位.md)
