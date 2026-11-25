#!/usr/bin/env python3
"""記事ごとの共有カード画像（1200×630）を作る。publish_day.py から呼ばれる。

デザイン：記事の色（accent）一色の背景に、黒い太字で見出し。見出しの強調語句（<span>）には白い蛍光ペン。
左上に DOPE、右上にカテゴリと日付、左下にキャッチコピー。
Pillow かフォントが見つからないときは何もしない（共通の assets/og.png が使われる）。
"""
import os
import re
import subprocess

W, H = 1200, 630
INK = (10, 10, 12)
WHITE = (245, 243, 238)
CATCH = "縦スクロールでニュースを読む。"
CAT_EN = {"world": "WORLD", "tech": "TECH & SCIENCE", "sports": "SPORTS"}

# 見出しの改行：文節（助詞・句読点のあと）でまとまりを作る。サイトの見出しと同じ規則
PHRASE = re.compile(r'([^、。！？」）]*?(?:から|まで|より|とは|では|には|へは|は|が|を|に|で|と|の|へ|も|や|、|。|！|？|」|）)(?=[^ぁ-んー、。！？」）]|$)|[^、。！？」）]+$)')


def _font_path(family, fallback_paths):
    for p in fallback_paths:
        if os.path.exists(p):
            return p, 0
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}|%{index}", family], capture_output=True, text=True, timeout=10).stdout
        f, i = out.split("|")
        if os.path.exists(f):
            return f, int(i or 0)
    except Exception:
        pass
    return None, 0


def _fonts():
    from PIL import ImageFont
    jp, jpi = _font_path("Noto Sans CJK JP:style=Black", ["/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"])
    en, _ = _font_path("Archivo Black", ["/usr/share/fonts/truetype/google-fonts/ofl/archivoblack/ArchivoBlack-Regular.ttf"])
    lab, _ = _font_path("DejaVu Sans:style=Bold", ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"])
    if not (jp and en and lab):
        return None
    # Noto Sans CJK の .ttc は 0 番が日本語（JP）
    jp_index = 0 if jp.endswith(".ttc") and "NotoSansCJK" in jp else jpi
    return dict(jp=lambda s: ImageFont.truetype(jp, s, index=jp_index),
                en=lambda s: ImageFont.truetype(en, s),
                lab=lambda s: ImageFont.truetype(lab, s))


def _runs(title_html):
    """見出しを [(文字, 強調か)] にする。"""
    out, emph = [], False
    for tok in re.split(r"(<[^>]+>)", title_html):
        if tok.startswith("<"):
            if tok.startswith("</"):
                emph = False
            elif tok.lower().startswith("<span"):
                emph = True
            continue
        out += [(ch, emph) for ch in tok]
    return out


def _phrases(text):
    parts = []
    for x in re.split(r"(?=「|（)", text):
        if x:
            parts += [m for m in PHRASE.findall(x) if m] or [x]
    return parts if "".join(parts) == text else list(text)


def _wrap(text, font, width):
    """文節単位で行を詰める。1文節が行より長いときだけ文字単位で折る。"""
    lines, cur = [], ""
    for ph in _phrases(text):
        if font.getlength(cur + ph) <= width:
            cur += ph
            continue
        if cur:
            lines.append(cur)
            cur = ""
        while font.getlength(ph) > width:
            k = len(ph)
            while k > 1 and font.getlength(ph[:k]) > width:
                k -= 1
            lines.append(ph[:k])
            ph = ph[k:]
        cur = ph
    if cur:
        lines.append(cur)
    return lines


def _spaced(draw, xy, text, font, fill, spacing):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + spacing
    return x


def _spaced_len(text, font, spacing):
    return sum(font.getlength(ch) for ch in text) + spacing * max(0, len(text) - 1)


def make_card(path, title_html, accent, cat, m, d, site_name="DOPE"):
    """カード画像を path に保存する。作れたら True。"""
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return False
    F = _fonts()
    if not F:
        return False
    try:
        bg = tuple(int(accent.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        bg = (255, 46, 136)
    im = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(im)
    X = 64

    # 上の段：DOPE と、カテゴリ・日付
    dr.text((X, 44), site_name, font=F["en"](52), fill=INK)
    label = f"{CAT_EN.get(cat, '')}  ·  {m}.{d:02d}"
    lf = F["lab"](22)
    _spaced(dr, (W - X - _spaced_len(label, lf, 5), 62), label, lf, INK, 5)

    # 見出し：3行に収まる最大の大きさで
    runs = _runs(title_html)
    text = "".join(ch for ch, _ in runs)
    top, bottom, width = 150, 520, W - X * 2
    for size in range(96, 47, -4):
        f = F["jp"](size)
        lines = _wrap(text, f, width)
        lh = int(size * 1.32)
        if len(lines) <= 3 and lh * len(lines) <= bottom - top:
            break
    y = top + ((bottom - top) - lh * len(lines)) // 2
    # 強調語句は、どの背景色でも読めるよう「白い蛍光ペン」を下半分に引いて黒字で書く
    k = 0
    for line in lines:
        x = X
        marks = []
        for ch in line:
            w = f.getlength(ch)
            if runs[k][1]:
                marks.append((x, x + w))
            x += w
            k += 1
        for x0, x1 in marks:
            dr.rectangle([x0 - 2, y + int(size * 0.62), x1 + 2, y + int(size * 1.16)], fill=WHITE)
        x = X
        for ch in line:
            dr.text((x, y), ch, font=f, fill=INK)
            x += f.getlength(ch)
        y += lh

    # 下の段：キャッチコピー
    dr.text((X, H - 74), CATCH, font=F["jp"](26), fill=INK)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.quantize(colors=48, method=Image.Quantize.MEDIANCUT).save(path, optimize=True)
    return True
