# GDScript教会の復活地点登録契約（#226）

## 責務と導線

正規churchイベントをEnter/Space/Eで調べる。Sceneはplain reviveを `application/church_registration.gd` へ委譲する。`engine/revive_point_contract.gd` は地点検証・通行規則・stateの1キー変更計画、既存Dataはread-onlyマップと名前付きstateのguarded保存を所有する。UI/rendererは保存・回復・復活を決めない。

はじまりの街は（18,10）、ロクター村は（14,9）から上を向く。保存先は既存の選択中Godot名前付きセーブだけ。未保存なら先にF5を案内し、教会から初期保存/初期個体を勝手に生成しない。Python savedata/active.jsonへ自動接続しない。

## 地点・保存

- reviveは辞書、map_id/nameは空でない文字列、x/yは有限の整数値（JSON由来の整数float可、bool/文字列不可）が必要。名前や座標を補間/自動修正しない。map_idのパス/未知IDは既存Data読込で拒否する。
- 対象マップのid一致・寸法/行列/events配列をDataで確認し、純粋契約がイベント座標・対象ブロック定義・範囲/地形/岩や看板などのblockingイベントを確認する。型違いの寸法をint変換で黙認しない。初期NPC配置は現在占有ではなく、今回は復活先へ実移動しない。
- 既存stateのrevive_pointだけをイベントの辞書コピーに置換する。入力地点の未知キーもPython FieldProgressStore.register_churchと同様に保持する。旧revive_pointの未知キーを新地点へ合成しない。
- 保存済み位置/方向/current_party/flags/未知stateキー、既存個体/学習済みAI/items/parties/metaは保持する。未保存のフィールド位置もこの操作では保存しない。schema/方向/revive_pointを省略した旧stateを読めるが、登録以外の欠損キーは挿入しない。
- 同じ辞書が登録済みならstateを再出力しない。所有数・保存スロット数に制限を追加せず、登録からパーティ/モブ/会話/時計を初期化しない。暗号/一覧/編成/プリセット中とechoキーでは教会操作を漏らさない。

## 失敗と確認

beginで既存state/digestと検証済み地点を捕捉し、commitでstateを再読込してdigestを比較、復活先コンテンツを読込・検証する。既存save_profileも書込直前の期待digest/リンク拒否を使い、一時ファイルからstateを置換する。失敗時に以前のstateを削除/修復/巻き戻ししない。再調査で最新stateを使う。

成功の表示は、保存後のload_positionと期待state全体の照合から行う。書込後に外部変更を検出した場合はok:false/saved:trueと確認失敗を明示する。savedはDataが書込成功を返したかを示し、外部変更後の期待内容保持を保証しない。並行writerの完全排他や検証後〜置換の競合窓解消を主張しない。実stateの破損/未対応schema/復元できない位置/リンクも理由付き拒否する。

## 未接続と検証

今回の成功はcheckpoint登録だけ。プレイヤーを移動させず、HP回復・全滅判定・戦闘・実際の敗北→教会復活は未接続と表示する。復活地点の再起動保持は、敗北復活の動作検証ではない。

`tests/test_gdscript_church.py` →開発者専用 `gdscript/tests/run_church_probe.gd` で、実Scene/正規2教会/実E・Enter・Space/再起動、同一再登録、旧形式、Python StateStore/FieldProgressStore、未知キー/AI/items/party/原本保持を専用コピーで検証する。不正地点/マップ/JSON、外部更新、書込前digest再照合・書込後確認、modal/echoも検証する。書込前後の外部変更/虚偽の成功返却はテスト専用Data fault注入。

実Windowsの読込可能・置換不可ハンドルでは以前のstate保持/所有一時ファイル清掃/解除後の再試行/同一地点の書込不要を、private junctionではリンク拒否を確認する。実セーブは使わない。手動画面の視認性、IME、配布exportは未検証。次の#227は戦闘個体HP/MP・生死状態で、実敗北復活を代用しない。
