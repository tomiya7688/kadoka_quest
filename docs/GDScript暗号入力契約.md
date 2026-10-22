# GDScript湧き場の暗号入力契約（#224）

## 操作と境界

正規 `ghost_home` の `password_spring`（17,7）をEnter/Space/Eで調べると、7文字枠と46文字のかな仮想キーボードを開く。実際の通行可能な正面位置は（17,8）、向き `back`。イベントJSONに印や色、取得条件を追加しない。

- `engine/password_session.gd` が許可文字、上限、入力・案内・誤答メッセージ、activeを所有する。Python `apps/password_session.py` と同じ操作列を比較する。
- `ui/password_view.gd` は7枠の描画、native LineEditの確定文字/仮想Button/キーをplain文字・操作signalへ変換する。暗号文字列、許可/上限判定、保存、取得処理を持たない。
- `application/field_application.gd` が湧き場・Session・UI・結果signalを接続する。入力中は探索時計、固定モブ移動/補間、主人公長押し更新、調べる、F5/F9/F6を止める。直接の位置保存/読込・一覧/編成開始も拒否する。

暗号は `へいわなすみか`、許可文字はPython正本のKANA_KEYSと同じ46文字。`open`は入力を空にして案内を表示しactiveにする。`append`はactive・許可された1文字・上限未満の場合だけ追加し、メッセージを消す。非許可文字/複数文字/8文字目は変更しない。nativeの複数文字確定はUIで1文字ずつ渡すため、許可文字だけを先頭から7文字まで受理する。

`backspace`はactive中だけ末尾1文字を削除し、空でもメッセージを消す（返却boolは削除の有無）。`submit`はactiveかつ完全一致のときだけ終了し、それ以外は誤答メッセージを表示して入力を保持する。閉じたSessionへのsubmitもPython同様に失敗メッセージを設定する。`cancel`は文字とメッセージを空にして終了する。再openは新しい入力としてリセットする。Sessionのsnapshotに暗号そのものは含めない。

## UI入力

かな入力欄へ日本語を入力するか、仮想キーをクリックする。Enter/テンキーEnterで決定、Backspaceでけす、Escで取消。Tab/Shift+Tabは入力欄→かなキー→けす/決定/やめるを巡回し、Spaceはフォーカス中の仮想Buttonを押す。Buttonフォーカス中もUnicode文字を入力できる。決定/取消のechoは無視し、キーとnative Buttonで二重実行しない。

LineEditの確定文字signalだけをSessionへ渡し、入力欄フォーカス時に同じUnicodeキーを二度渡さない。IME変換中のEnter/Backspace/Escはnative側に委ねる。IME関連APIの根拠は[Godot LineEdit](https://docs.godotengine.org/en/stable/classes/class_lineedit.html#class-lineedit-method-has-ime-text)。実際のWindows IME候補/確定動作は手動未検証。

開閉時に長押しの繰返し時間をリセットする。探索時計は停止中のwall-clockを足さず、閉じた後のdeltaだけを進める。住処のまる/かどかを隠したり消したりしない。

## 一致結果と未移植

一致は `password_finished({"kind": "password_matched"})`、取消は `password_cancelled` のplain結果。誤答はsignalを出さず、入力画面に残る。#224単独では取得/保存が未接続だった。#225の[おばけ取得契約](GDScriptおばけ取得契約.md)でapplicationサービスへ接続し、保存を確認してから加入成功を表示する。入力UI自体は取得処理を持たない。

入力状態や結果は実行時だけ。入力/誤答/取消は進行フラグ・所有個体・AI・items・partyを変更せず、初期保存フォルダも作らない。一致時の取得/フラグ保存は#225の独立サービスの責務で、未保存なら先にF5を案内する。データの暗号化やエディタ専用形式は追加しない。

## 検証

`tests/test_gdscript_password.py` →実Godot `tests/run_password_probe.gd`。純粋Sessionの同一操作列（開く/追記/削除/一致/不一致/取消/終了後/許可文字/Unicode）をPythonと比較する。専用コンテンツ/保存コピーで正規湧き場→実Unicodeキー/native LineEdit→仮想Buttonのmouse click/Tab/Space/各操作→停止/再開、960×540内のControl矩形を確認する。確定文字の複数文字signalはadapter検証で、OS IMEを再現したものではない。

一致前後・取得前後のfixtureで、入力/取消/取得済み再入力の不変と、#225の許可された新規個体・フラグだけの変更を分けて比較する。実セーブは使わない。Godot未指定時のskipは成功ではない。手動画面の見やすさ、IME実入力、exportは未検証。入力は7文字の低頻度操作で新しいホットパスではなく、既存Python/Godotの標準性能ガードで退行を検証する。
