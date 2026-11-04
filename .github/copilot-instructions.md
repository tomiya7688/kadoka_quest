# GitHub Copilot向けの入口

GitHub Copilotは、Kadoka Questを変更する前に、共有ルールの正本であるリポジトリ直下の[AGENTS.md](../AGENTS.md)と、[1作業単位のワークフロー](../docs/ワークフロー/ワークフロー.md)を読んでください。この入口へ規約本文を複写しないでください。

Kadoka Questは、利用者・Codex・Claude Code・GitHub Copilot・ChatGPTが並行して開発します。GitHub Copilotは、作業開始時とコミット直前に `python tools/remote-context/script/sync_remote_context.py` を実行し、mainの差分と他の作業者の進行中ブランチを確認してください。
