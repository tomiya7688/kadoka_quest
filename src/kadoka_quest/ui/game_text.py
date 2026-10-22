# {
#   責務: [game_text: Player画面の日本語を同梱16pxフォントで描き、整数拡大と描画領域を守る]
#   フィールド: []
# }
from __future__ import annotations

from functools import lru_cache

import pygame

from kadoka_quest.paths import ASSET_ROOT


TEXT = (245, 245, 245)
NATIVE_SIZE = 16


# {
#   責務: [PixelFont: 16pxの字形と整数倍率の文字画像を所有し、pygame互換の計測・描画を提供する]
#   フィールド: [
#     scale: 元の16px字形へ適用する整数倍率
#     native: 同梱日本語フォントの16px字形
#     bold: フォントを再読込する場合にも保持する太字指定
#   ]
# }
class PixelFont:
    # {
    #   責務: [__init__: 同梱フォントを一度読み込み、指定倍率の文字描画を準備する]
    #   処理: [1: フォント機能を初期化して16pxの字形と倍率を保持する]
    #   引数: [
    #     self: 文字画像を所有するPixelFont
    #     scale: 16px字形へ適用する正の整数倍率
    #     bold: 太字の字形を使用するか
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, scale: int, bold: bool = False) -> None:
        # フォント探索をフレームごとに繰り返さず、同梱した日本語字形を使用する。
        if not pygame.font.get_init():
            pygame.font.init()
        self.scale = scale
        self.bold = bold
        self.native = pygame.font.Font(str(ASSET_ROOT / "fonts" / "DotGothic16-Regular.ttf"), NATIVE_SIZE)
        self.native.set_bold(bold)

    # {
    #   責務: [_call_native: pygame終了で無効になった字形を再読込し、フォント操作を実行する]
    #   処理: [
    #     1: 保持している字形へ計測または描画を依頼する
    #     2: SDLフォントの失敗時は字形を再読込して一度だけ再試行する
    #   ]
    #   引数: [
    #     self: 元字形と太字指定を保持するPixelFont
    #     method: pygame.Fontの計測または描画メソッド名
    #     arguments: 指定メソッドへそのまま渡す引数
    #   ]
    #   戻り値: [result: 指定したフォント操作の結果。再試行も失敗する場合は例外を返す]
    # }
    def _call_native(self, method: str, *arguments):
        # 外部呼び出し元がpygame.quit/initを直接実行しても、古いSDL字形を使い続けない。
        try:
            return getattr(self.native, method)(*arguments)
        except pygame.error:
            if not pygame.font.get_init():
                pygame.font.init()
            self.native = pygame.font.Font(str(ASSET_ROOT / "fonts" / "DotGothic16-Regular.ttf"), NATIVE_SIZE)
            self.native.set_bold(self.bold)
            return getattr(self.native, method)(*arguments)

    # {
    #   責務: [size: 文字列の整数拡大後の幅と高さを返す]
    #   処理: [1: 元字形の計測結果を整数倍する]
    #   引数: [
    #     self: 計測するPixelFont
    #     text: 幅と高さを計測する文字列
    #   ]
    #   戻り値: [result: 文字列画像の幅と高さを画素数で表した組]
    # }
    def size(self, text: str) -> tuple[int, int]:
        # 描画と同じ倍率を使い、配置計算と画面表示の不一致を防ぐ。
        width, height = self._call_native("size", str(text))
        return width * self.scale, height * self.scale

    # {
    #   責務: [get_height: 一行の文字画像の高さを画素数で返す]
    #   処理: [1: 元字形の高さへ整数倍率を適用する]
    #   引数: [self: 計測するPixelFont]
    #   戻り値: [result: 拡大後の字形の高さ]
    # }
    def get_height(self) -> int:
        # 呼び出し元はpygameのFontと同じ方法で行の高さを取得できる。
        return self._call_native("get_height") * self.scale

    # {
    #   責務: [get_linesize: 複数行を配置する際の行送りを画素数で返す]
    #   処理: [1: 元字形の行送りへ整数倍率を適用する]
    #   引数: [self: 計測するPixelFont]
    #   戻り値: [result: 拡大後の行送り]
    # }
    def get_linesize(self) -> int:
        # 文字の下端を次の行が覆わない行送りを提供する。
        return self._call_native("get_linesize") * self.scale

    # {
    #   責務: [_image: 文字列を補間なしで描き、再利用する文字画像を返す]
    #   処理: [
    #     1: アンチエイリアスなしで元の16px字形を描く
    #     2: 必要な場合だけ最近傍法で整数拡大する
    #   ]
    #   引数: [
    #     self: 文字画像を生成するPixelFont
    #     text: 描く文字列
    #     color: 字形のRGBA色
    #     background: 背景のRGBA色、または透明背景を示すNone
    #   ]
    #   戻り値: [result: 呼び出し元が変更しない共有文字画像]
    # }
    @lru_cache(maxsize=256)
    def _image(self, text: str, color: tuple, background: tuple | None) -> pygame.Surface:
        # キャッシュは直近256画像に制限し、変化する数値表示で無制限に増やさない。
        image = self._call_native("render", text, False, color, background)
        if self.scale > 1:
            image = pygame.transform.scale(image, (image.get_width() * self.scale, image.get_height() * self.scale))
        return image

    # {
    #   責務: [render: 呼び出し元が自由に変更できる文字画像を返す]
    #   処理: [1: 色を正規化してキャッシュ画像の独立コピーを返す]
    #   引数: [
    #     self: 文字画像を生成するPixelFont
    #     text: 描く文字列
    #     antialias: pygame互換の引数。ピクセル字形では常に補間を無効にする
    #     color: 字形のpygame互換色
    #     background: 背景色。省略時は透明
    #   ]
    #   戻り値: [result: キャッシュと画素を共有しない文字画像]
    # }
    def render(self, text: str, antialias: bool, color, background=None) -> pygame.Surface:
        # pygame.Font.renderと同様に新しいSurfaceを返し、利用者の加工からキャッシュを守る。
        foreground = tuple(pygame.Color(color))
        backdrop = tuple(pygame.Color(background)) if background is not None else None
        return self._image(str(text), foreground, backdrop).copy()


# {
#   責務: [_scaled_font: 同じ整数倍率と太字指定のフォントを共有する]
#   処理: [1: 未作成の倍率だけ同梱フォントを読み込む]
#   引数: [
#     scale: 16px字形へ適用する整数倍率
#     bold: 太字の字形を使用するか
#   ]
#   戻り値: [result: 指定した倍率と太字指定のPixelFont]
# }
@lru_cache(maxsize=16)
def _scaled_font(scale: int, bold: bool) -> PixelFont:
    # 旧画面の14、18、22px指定も同じ16pxフォントを共有して読み込み回数を抑える。
    return PixelFont(scale, bold)


# {
#   責務: [font: 指定された文字サイズに対応するPlayer専用フォントを再利用する]
#   処理: [1: 指定サイズを16px単位へ切り下げてフォントを返す]
#   引数: [
#     size: 希望する文字サイズ。16未満は16px、32未満は16pxになる
#     bold: 太字の字形を使用するか
#   ]
#   戻り値: [result: pygame互換の計測・描画を持つPixelFont]
# }
@lru_cache(maxsize=32)
def font(size: int, bold: bool = False) -> PixelFont:
    # 非整数倍率を作らず、細い画素がぼけることを防ぐ。
    return _scaled_font(max(1, int(size) // NATIVE_SIZE), bold)


# {
#   責務: [reset_text_cache: Playerのウィンドウを開き直す際に文字画像とフォントを破棄する]
#   処理: [1: 文字画像とフォントのキャッシュを空にする]
#   引数: []
#   戻り値: [result: なし（None）]
# }
def reset_text_cache() -> None:
    # 終了したpygameのフォントを保持せず、次の描画で新しい字形を読み込む。
    PixelFont._image.cache_clear()
    wrap_lines.cache_clear()
    font.cache_clear()
    _scaled_font.cache_clear()


# {
#   責務: [draw_text: Playerの文字列を整数拡大した字形で描く]
#   処理: [1: キャッシュ済みの文字画像を指定座標へ描く]
#   引数: [
#     surface: 描画先の画面
#     value: 文字列へ変換して表示する値
#     position: 文字画像の左上座標
#     size: 希望する文字サイズ
#     color: 文字の色
#     bold: 太字の字形を使用するか
#   ]
#   戻り値: [result: 画面へ実際に描画した矩形]
# }
def draw_text(surface, value, position, size: int = 22, color=TEXT, bold: bool = False) -> pygame.Rect:
    # 通常描画ではコピーを作らず、読み取り専用の文字画像を直接転送する。
    image = font(size, bold)._image(str(value), tuple(pygame.Color(color)), None)
    return surface.blit(image, position)


# {
#   責務: [draw_text_clipped: 長い個体名や項目名を指定矩形の内側だけへ描く]
#   処理: [
#     1: 呼び出し元の描画範囲と指定矩形の共通部分を設定する
#     2: 文字を描き、呼び出し元の描画範囲を復元する
#   ]
#   引数: [
#     surface: 描画先の画面
#     value: 文字列へ変換して表示する値
#     rect: 文字を描いてよい矩形
#     size: 希望する文字サイズ
#     color: 文字の色
#     bold: 太字の字形を使用するか
#   ]
#   戻り値: [result: 画面へ実際に描画した矩形]
# }
def draw_text_clipped(surface, value, rect, size: int = 16, color=TEXT, bold: bool = False) -> pygame.Rect:
    # 長い日本語名でも隣の項目へ文字を重ねず、外側のクリップも維持する。
    previous = surface.get_clip()
    surface.set_clip(previous.clip(rect))
    try:
        return draw_text(surface, value, rect.topleft, size, color, bold)
    finally:
        surface.set_clip(previous)


# {
#   責務: [wrap_lines: 明示改行を保ちながら日本語を指定横幅で折り返す]
#   処理: [
#     1: 明示改行ごとの文字列を左から順に計測する
#     2: 横幅を超える直前で行を分割して全行を返す
#   ]
#   引数: [
#     value: 改行を含めて表示する文字列
#     width: 一行に表示できる横幅の画素数
#     size: 希望する文字サイズ
#   ]
#   戻り値: [result: 入力文字列の順序を保った表示行の不変な組]
# }
@lru_cache(maxsize=128)
def wrap_lines(value: str, width: int, size: int = 16) -> tuple[str, ...]:
    # 改行位置の計算を共用し、会話のページ送りと画面描画の境界を一致させる。
    if width <= 0 or not value:
        return ()
    current_font = font(size)
    widths: dict[str, int] = {}
    lines: list[str] = []
    for paragraph in str(value).split("\n"):
        line = ""
        line_width = 0
        for character in paragraph:
            if character not in widths:
                widths[character] = current_font.size(character)[0]
            character_width = widths[character]
            if line and line_width + character_width > width:
                lines.append(line)
                line, line_width = "", 0
            line += character
            line_width += character_width
        lines.append(line)
    return tuple(lines)


# {
#   責務: [draw_wrapped: 明示改行と文字幅で折り返し、指定矩形内に収まる行だけを描く]
#   処理: [
#     1: 文字ごとの幅を計測し、改行または横幅の上限で行を区切る
#     2: 矩形の高さまで文字を描いて描画範囲を復元する
#   ]
#   引数: [
#     surface: 描画先の画面
#     value: 改行を含めて表示する文字列
#     rect: 表示を許可する矩形
#     size: 希望する文字サイズ
#     color: 文字の色
#     line_gap: 行間の画素数
#   ]
#   戻り値: [result: 最後に描いた行の次のY座標]
# }
def draw_wrapped(surface, value: str, rect, size: int = 20, color=TEXT, line_gap: int = 4) -> int:
    # 小さい表示領域は空描画にし、負の横幅で不正な折り返しを作らない。
    area = pygame.Rect(rect)
    if area.width <= 0 or area.height <= 0:
        return area.y
    current_font = font(size)
    line_height = current_font.get_height() + max(0, line_gap)
    y = area.y
    previous = surface.get_clip()
    surface.set_clip(previous.clip(area))
    try:
        # ページ送りと同じ行分割を使い、矩形内へ一行分が収まる場合だけ描く。
        for line in wrap_lines(str(value), area.width, size):
            if y + current_font.get_height() > area.bottom:
                break
            draw_text(surface, line, (area.x, y), size, color)
            y += line_height
    finally:
        surface.set_clip(previous)
    return y
