# GDScript固定モブ会話契約 (#223)

正本はPython `FixedMobController.next_dialogue` と `FieldEventApplication.resolve_interaction`。map.jsonの固定モブdialogue配列をread-onlyで使い、新しいJSON形式を作らない。

## 責務と規則

- `engine/dialogue_deck.gd`: 文字列カードの検証、空白除去、一巡/再抽選。shuffle注入型でファイル/時計/UIへ依存しない。
- `engine/fixed_mob_controller.gd`: 各モブの独立したカード残数/前回台詞と、話しかけた際の向きを所有。移動と同じRNGアダプタを使う。
- `application/field_session.gd`: プレイヤーの正面マスだけからモブを選び、なければ従来のイベント選択へ戻る。同じ場所にモブとイベントがあればモブ優先。
- Scene: Enter/Space/Eの押下だけを接続し、plain結果をstatusへ表示。key echoは消費しない。描画はカードを引かない。管理modal中は従来の入力停止を守る。

空白を除いた有効カードを残りプールへ複写しshuffleする。プール末尾をpopし、全カード消費まで再抽選しない。補充後の末尾が前回台詞と同じで2枚以上なら先頭と末尾を入れ替える。Pythonの現在の選択順に一致させる。単一カードは同じ台詞を繰り返す。重複カードは原本どおり残すため、内容が同じカードの連続まで完全回避する保証ではない。

空白除去はPython str.strip()と同じUnicode空白（全角/ノーブレーク等を含む）。台詞内部の空白やゼロ幅文字を勝手に除去しない。shuffleのseed列はPython/Godotで互換ではないため、検証は同じ方向/カード順を注入する。

## 正面停止と表示

話しかけるとモブの向きをプレイヤー向きの反対へ変える（left/right、front/back）。これによりプレイヤーがモブの正面マスにいる限り、既存controllerはRNGを消費せず移動しない。周期の締切は更新され、離れた後に次の締切で通常移動する。追いつき連打はない。既に開始した180msの表示補間と整数マス占有は従来の契約どおり。

会話の表示はmodalではなくstatus。移動キーで離れられ、別モブの時間更新は止めない。正面でなければ隣接していても話しかけない。住処のまる/かどかは取得/所有状態を理由に非表示にしない。

## 失敗と未移植

未設定、非配列、非文字列カード、有効カードなしは理由付き失敗。RNG/カードを消費せず、UIに理由を表示する。Pythonの不正型の文字列化や「……」fallbackは流用せず、Issueの明示診断条件を優先した。方向の変更は不正デッキの相手にも適用し、通常の正面停止は維持する。

interactionがtalk以外なら理由付き未移植で、会話カード/RNGを消費しない。会話後の消滅設定があるtalkは台詞と未移植注意を表示するが、実際には除去/フラグ保存しない。固定/野生戦闘、条件付き戦闘セリフ、湧き場の7文字暗号/仲間取得は別単位。

カード状態/前回台詞をmap.json・個体・AI・stateへ保存しない。再入場/読込で個別デッキも初期化する。正規JSON/画像/実セーブを検証に使わず、一時コピーを使う。

## 検証

`tests/test_gdscript_dialogue.py` が実Godot runnerでPythonとの順序/残数/前回カード/RNG消費を比較し、全巡回・境目・単一/重複/Unicode空白、不正診断を確認する。実SceneのEnter/Space/Eとecho、4方向の振り向き、正面対象/イベント優先、停止/占有/周期再開、管理modal、取得前後の住処2体、原本/個体AI/assetsのbyte不変を専用コピーで検証する。

性能検査は既存Pythonガードに加え、Godotの24体update+snapshotと5枚デッキのtalk効果生成を計測する。headless検証は手動ウィンドウの視認性・FPS・export済みbuildを証明しない。
