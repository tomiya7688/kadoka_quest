# GDScript固定モブ移動契約 (#222)

Python正本は `src/kadoka_engine/fixed_mob_controller.py / grid_movement.py`。既存map.json/blocksを読み、正規JSON・画像・実セーブは変更しない。

## 責務と時間

- 純粋 `engine/fixed_mob_controller.gd`: 初期配置、移動先/占有、周期/確率、補間値。時刻とrandom adapterを注入し、時計・UI・ファイルを参照しない。
- `engine/field_random.gd`: Godotの乱数アダプタ。Pythonとseed列は互換ではない。比較は同じroll値と方向順を注入する。
- `application/field_session.gd`: フィールド有効時間をdelta秒からミリ秒へ累積。小数部分を保持し、判定だけ整数化。map入場時に初期化する。
- Scene: 主人公の入力に関係なく毎processでadvance。個体一覧/編成/プリセットが開いていれば時計・モブ・補間・主人公移動を止める。閉じた後にmodal滞在時間分を加算しない。
- renderer: plain snapshotの `display_x/display_y` を描くだけ。描画/再描画でRNG・移動・時刻を変更しない。

## 移動と初期化

`move_interval_ms` は最低100ms。締切に達したupdateで1回だけ判定し、次回はnow+interval。遅いframeで追いつき連続移動しない。idle/通行不能/確率失敗でも締切を更新する。

idleは停止。randomは4方向をshuffle、chaseは横→縦の接近候補→shuffleした残りの4方向。未知AIはPythonと同じrandom相当。`move_chance` は0〜100へclampし、randrange(100)がそれ未満のときだけ進む。idle、またはモブの正面マスにプレイヤーがいればRNGを使わず停止する（既存Pythonの基本移動規則）。話しかけた際の振り向き/会話デッキは#223。

`player_walkable`、境界、blockingイベント、プレイヤー、他の固定モブを避け、移動先の整数マスを即時予約する。表示は元位置から180msのsmoothstep補間で移動する。途中で再移動する場合は現在の補間位置から始める。interval/chanceが既存JSONの移動速度/頻度であり、新しいspeedキーや戦闘speedステータスを導入しない。

初期配置は原本のdeep copy。enabled=falseを除外し、respawn_on_map_enter=falseで既存 `map_id:npc_id` がdespawned_fixed_mobsにあれば除外する。それ以外は原本の初期地点へ戻り、移動回数/締切をリセットする。プレイヤー/既配置モブとの重複、壁/通行止め/範囲外の初期地点は、上から行単位で最初の空きマスへ移す。空きがなければ配置せずwarningsへ理由を返す。

Pythonの現在のmoveはblockingイベントを判定せず、resetは不正配置/空きのない場合の重複を残す。この2点はIssueの占有条件を優先してGodot側で強化した。正常配置のPython比較と、強化点のテストは分ける。Python runtimeの挙動を今回変更したとは扱わない。

## 保存と未移植

モブ移動中の位置/締切/回数/時計/RNG/補間をJSONへ書かない。保存は現在のモブの整数座標による占有を検証する。読込は地形/通行止めを検証した後にプレイヤーを先に配置し、重なる初期モブを再配置する。モブの元のマスが空いていればそこでF5保存/F9復元/再起動できる。プレイヤーの座標を勝手に修復しない。

既存消滅フラグは読込のみで、新しい消滅フラグは生成しない。固定モブ会話/消滅イベント、固定戦闘、野生敵/接触戦闘、暗号取得、戦闘AIの実装成功を装わない。

## 検証

`tests/test_gdscript_fixed_mobs.py` は実Godot runnerで正常配置の時刻/RNG/方向/回数/締切/補間をPythonと比較する。正規まる/かどか設定、初期化/再入場/消滅フラグ、全blocking台帳、占有/満員、実Sceneの停止中更新と管理modal停止、補間中の移動先占有、保存/別プロセス復元、JSON/個体/AIのbyte不変を専用コピーで検証する。Godot未指定のskipは成功証拠にしない。

開発専用 `tools/performance-check/script/check_gdscript_fixed_mobs.py` は24体のupdate+snapshotを実headless Godotで測る。Python性能ガード/UPDも既存退行検査として実行するが、いずれも手動ウィンドウの視認性・FPS・export済みbuildの証拠ではない。
