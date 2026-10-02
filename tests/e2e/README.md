# Source E2E（準備段階）

期待動作と未対応一覧の正本は [E2E_EXPECTATIONS.md](../../docs/testing/E2E_EXPECTATIONS.md)。この領域にはまだ実行可能なE2Eはない。#201で本番composition rootに近いharnessを構築し、#202～#204でシナリオを追加する。

各テストはカタログIDとGiven/When/Thenを示し、操作を本番runtime/command境界へ渡す。RNG・clock・SDL・セーブ/インポート領域を隔離し、永続化項目はruntime/Storeを作り直して再読込する。ゲーム結果を生成する専用ロジックやsleepによる待機を作らない。

E2E追加後は成功したテストのnode IDをカタログに登録する。通常のunit/integration/smokeを移動しただけでcovered扱いにしない。
