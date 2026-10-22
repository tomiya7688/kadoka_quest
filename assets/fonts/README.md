# Player用の日本語フォント

Kadoka QuestのPython版Playerは、DotGothic16を同梱して日本語のピクセル字形を統一します。Playerは DotGothic16-Regular.ttf を16pxで読み込み、アンチエイリアスを使用せず、必要な場合に最近傍法で整数拡大します。開発者向けエディターのシステムフォント設定は、この同梱フォントへの置換対象に含みません。

- フォント: DotGothic16 Regular
- 著作権表示: Copyright 2020 The DotGothic16 Project Authors
- 配布元: [Google Fonts内のDotGothic16](https://github.com/google/fonts/tree/9a6cc6b8ce992aff77b69c857c46af0b42cdff76/ofl/dotgothic16)
- 取得元コミット: 9a6cc6b8ce992aff77b69c857c46af0b42cdff76
- 同梱TTFのSHA-256: 3AD9AF88726D42B40F7F365F0DCAC785AF73CF20EA6F1D5B44E57CC21150B8F1
- ライセンス: SIL Open Font License 1.1。全文は同じディレクトリの [OFL.txt](OFL.txt) にあります。
- 元プロジェクト: [Fontworks DotGothic16](https://github.com/fontworks-fonts/DotGothic16)

Godot版には、同じTTFとライセンスを gdscript/assets/fonts/ にもう一部同梱します。Python版は配布時の assets を参照し、Godot版は自身のプロジェクト内の res://assets/fonts/ をimportするためです。両方のファイルは同じ字形を使うためのコピーであり、異なる改変版ではありません。

フォントを更新する開発者は、両方のTTFとOFL.txtを同じ出典から更新してください。取得元コミットとSHA-256を両方のREADMEへ記録し、日本語の表示、行高、整数拡大、配布物への同梱を再確認してください。Player利用者による追加のフォントインストールは不要です。
