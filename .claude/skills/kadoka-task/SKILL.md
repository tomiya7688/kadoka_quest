---
name: kadoka-task
description: Kadoka Questで1つのIssueまたはGDScript移行単位を、リモート確認・単位選択・実装・検証・コミットまで進める共有手順です。Kadoka Questの実装・修正・移行作業を始めるとき、または「次」「実装を進める」と依頼されたときに使ってください。
---

# Kadoka Questの1作業スキル

このスキルは、Codex・Claude Code・GitHub Copilotなどの実装AIが、共有ワークフローを同じ順序で実行するための入口です。手順と規約の本文は正本の文書にあり、このスキルへ複写しません。

1. 実装AIは、リポジトリ直下の `AGENTS.md`、`docs/開発者向け/README.md` が指定する三つの必読規約、`docs/ワークフロー/ワークフロー.md` を読んでください。
2. 実装AIは、作業開始時に `python tools/remote-context/script/sync_remote_context.py` を実行し、mainとの差分と、他の作業者が進行中の未統合リモートブランチを確認してください。
3. 実装AIは、`docs/ワークフロー/GDScript移行実装単位.md` の「次候補」と公開中のPRを照合し、他の作業者と重ならない単位を一つ選んでください。
4. 実装AIは、`docs/CODEMAP.md` の該当行だけから実装・関連テスト・仕様書を特定し、mainの最新から作業者の接頭辞付きブランチを作ってください。
5. 実装AIは、集中テスト・全体テスト・`python tools/comment-check/script/check_comments.py`・`python tools/project-integrity/script/check_project_rules.py`・`git diff --check` を実行してください。Godotを使う検証は、`KADOKA_GODOT_EXECUTABLE` を設定して実行し、未設定によるskipを成功と報告しないでください。
6. 実装AIは、コミット直前にリモート同期スクリプトを再実行し、mainが進んでいれば取り込んでから再検証してください。
7. 実装AIは、対象ファイルだけをコミットしてください。push・PR作成・Issue変更は、利用者の明示的な指示がある場合だけ行ってください。
8. 実装AIは、変更内容・実行した検証と結果・未検証の範囲・未実行の外部操作を区別して報告してください。
