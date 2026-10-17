# Godot Player用の日本語フォント

Kadoka QuestのGodot版Playerは、プロジェクト内の res://assets/fonts/DotGothic16-Regular.ttf を使用します。Godot版は16pxのDotGothic16をアンチエイリアスなしで表示し、960×540の描画結果を整数倍率で拡大します。

- フォント: DotGothic16 Regular
- 著作権表示: Copyright 2020 The DotGothic16 Project Authors
- 配布元: [Google Fonts内のDotGothic16](https://github.com/google/fonts/tree/9a6cc6b8ce992aff77b69c857c46af0b42cdff76/ofl/dotgothic16)
- 取得元コミット: 9a6cc6b8ce992aff77b69c857c46af0b42cdff76
- 同梱TTFのSHA-256: 3AD9AF88726D42B40F7F365F0DCAC785AF73CF20EA6F1D5B44E57CC21150B8F1
- ライセンス: SIL Open Font License 1.1。全文は [OFL.txt](OFL.txt) にあります。
- 元プロジェクト: [Fontworks DotGothic16](https://github.com/fontworks-fonts/DotGothic16)

Python版にも同じTTFとライセンスを assets/fonts/ に同梱します。Godotのimportとexportがプロジェクト外のPython用パスへ依存しないように、Godotプロジェクト内にも同じフォントを置いています。コピー間に字形の変更はありません。

フォントを更新する開発者は、[Python版フォントの説明](../../../assets/fonts/README.md)に従って両方のTTFとOFL.txtを同時に更新してください。利用者がOSへフォントを追加する操作は不要です。
