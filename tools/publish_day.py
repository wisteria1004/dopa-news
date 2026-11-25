#!/usr/bin/env python3
"""その日の号を過去号として保存し、過去号の一覧ページを作り直す。

使い方（リポジトリの一番上で）:  python3 tools/publish_day.py
- index.html の ISSUE.date から日付を読み、archive/YYYY-MM-DD/index.html にそのままコピーする。
- archive/ 以下の全号から archive/index.html（過去号の一覧）と archive/days.json（号の目録）を作り直す。
- 各号の記事ごとに、共有用の入口ページ archive/YYYY-MM-DD/nXX/index.html を作る。
  SNSにURLを貼ると、その記事の見出しと要約がリンクカードに出る。開くと記事へ移る。
"""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from card import make_card
except Exception:
    make_card = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = os.path.join(ROOT, "archive")
WD = "月火水木金土日"
SITE = "https://wisteria1004.github.io/dopa-news/"   # 公開URL（末尾の / まで）
SITE_NAME = "DOPE"
OG_IMAGE = SITE + "assets/og.png"
CARD_VER = "2"   # カード画像を作り直したときに上げる（アプリに残った古い画像を読み直させるため）


def read_issue(path):
    s = open(path, encoding="utf-8").read()
    m = re.search(r'const ISSUE = \{date:"(\d{4})\.(\d{2})\.(\d{2})[^"]*"', s)
    if not m:
        raise SystemExit(f"ISSUE.date が見つかりません: {path}")
    y, mo, d = m.groups()
    i = s.index("const NEWS = [")
    j = s.index("const ORDER", i)
    block = s[i:j]
    raw_titles = [json.loads('"' + t + '"') for t in re.findall(r'"?title"?\s*:\s*"((?:[^"\\]|\\.)*)"', block)]
    titles = [re.sub(r"<[^>]+>", "", t) for t in raw_titles]
    accents = re.findall(r'"?accent"?\s*:\s*"(#[0-9a-fA-F]{6})"', block)
    if len(accents) != len(titles):
        accents = ["#ff2e88"] * len(titles)
    leads = [re.sub(r"<[^>]+>", "", json.loads('"' + t + '"')) for t in re.findall(r'"?lead"?\s*:\s*"((?:[^"\\]|\\.)*)"', block)]
    if len(leads) != len(titles):
        leads = [""] * len(titles)
    om = re.search(r"const ORDER = \[([^\]]*)\]", s)
    order = [int(x) for x in om.group(1).split(",") if x.strip()] if om else list(range(len(titles)))
    cats = re.findall(r'"?cat"?\s*:\s*"(world|tech|sports)"', block)
    return dict(iso=f"{y}-{mo}-{d}", y=int(y), m=int(mo), d=int(d),
                titles=[titles[k] for k in order if k < len(titles)],
                leads=[leads[k] for k in order if k < len(leads)],
                raw_titles=[raw_titles[k] for k in order if k < len(raw_titles)],
                accents=[accents[k] for k in order if k < len(accents)],
                cats=[cats[k] for k in order if k < len(cats)])


def weekday(y, m, d):
    import datetime
    return WD[datetime.date(y, m, d).weekday()]


def build_entries(day, it):
    """記事ごとの共有用入口ページを作る（リンクカード用）。"""
    base = os.path.join(ARCH, day)
    for n, (title, lead) in enumerate(zip(it["titles"], it["leads"]), 1):
        no = f"n{n:02d}"
        url = f"{SITE}archive/{day}/{no}/"
        # 見出し入りのカード画像（まだなければ作る）。作れなければ共通画像を使う
        card = os.path.join(base, no, "card.png")
        if not os.path.exists(card) and make_card:
            try:
                make_card(card, it["raw_titles"][n - 1], it["accents"][n - 1], it["cats"][n - 1], it["m"], it["d"], SITE_NAME)
            except Exception as e:
                print(f"カード画像を作れませんでした（{day} {no}）：{e}")
        image = f"{url}card.png?v={CARD_VER}" if os.path.exists(card) else OG_IMAGE
        t, l = html.escape(title), html.escape(lead)
        page = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t}｜{SITE_NAME}</title>
<meta name="description" content="{l}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:locale" content="ja_JP">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{l}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{l}">
<meta name="twitter:image" content="{image}">
<meta property="og:image:alt" content="{t}">
<script>location.replace("../#{no}");</script>
<style>body{{margin:0;background:#08080d;color:#f5f3ee;font:500 16px/1.7 system-ui,sans-serif}}main{{max-width:620px;margin:0 auto;padding:40px 20px}}small{{color:#a39da8}}h1{{font-size:26px;line-height:1.4}}a{{color:#ffd60a;font-weight:700}}</style>
</head>
<body>
<main>
<small>{SITE_NAME}・{it["m"]}月{it["d"]}日号</small>
<h1>{t}</h1>
<p>{l}</p>
<p><a href="../#{no}">記事を読む</a></p>
</main>
</body>
</html>
'''
        os.makedirs(os.path.join(base, no), exist_ok=True)
        with open(os.path.join(base, no, "index.html"), "w", encoding="utf-8") as f:
            f.write(page)


def build_list():
    days = sorted([d for d in os.listdir(ARCH) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)
                   and os.path.exists(os.path.join(ARCH, d, "index.html"))], reverse=True)
    items, catalog = [], []
    for d in days:
        it = read_issue(os.path.join(ARCH, d, "index.html"))
        build_entries(d, it)
        catalog.append(dict(date=d, wd=weekday(it["y"], it["m"], it["d"]), n=len(it["titles"]),
                            top=it["titles"][0] if it["titles"] else ""))
        cnt = {k: it["cats"].count(k) for k in ("world", "tech", "sports")}
        tops = "".join(f"<li>{html.escape(t)}</li>" for t in it["titles"][:3])
        items.append(f'''<a class="day" href="{d}/">
  <div class="date"><b>{it["m"]}月{it["d"]}日</b><small>{weekday(it["y"], it["m"], it["d"])}曜日・{len(it["titles"])}本（世界{cnt["world"]}・テック科学{cnt["tech"]}・スポーツ{cnt["sports"]}）</small></div>
  <ol>{tops}</ol>
</a>''')
    page = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>過去の号｜{SITE_NAME}</title>
<meta name="description" content="{SITE_NAME}の過去の号の一覧">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Zen+Kaku+Gothic+New:wght@500;700;900&display=swap" rel="stylesheet">
<style>
:root{{color-scheme:dark;--bg:#08080d;--ink:#f5f3ee;--mute:#a39da8;--line:#34303b;--pink:#ff2e88;--yel:#ffd60a}}
*{{box-sizing:border-box;min-width:0}}
body{{margin:0;background:radial-gradient(80% 40% at 90% 0%,rgba(255,46,136,.35),transparent 70%),var(--bg);color:var(--ink);font:500 16px/1.7 "Zen Kaku Gothic New",system-ui,sans-serif;min-height:100vh}}
main{{max-width:620px;margin:0 auto;padding:calc(20px + env(safe-area-inset-top,0px)) 18px 48px}}
.back{{display:inline-flex;align-items:center;min-height:40px;padding:0 16px;border:1px solid var(--line);border-radius:999px;color:var(--yel);font-weight:900;font-size:14px;text-decoration:none}}
h1{{font-weight:900;font-size:clamp(28px,8vw,40px);line-height:1.2;margin:22px 0 6px}}
h1 span{{color:var(--pink)}}
.lead{{color:var(--mute);font-size:14px;margin:0 0 18px}}
.day{{display:block;text-decoration:none;color:inherit;border-top:1px solid var(--line);padding:16px 4px}}
.day:hover,.day:focus-visible{{background:rgba(255,255,255,.04);outline:none}}
.date b{{font:400 30px/1 Anton,"Zen Kaku Gothic New",sans-serif;margin-right:10px}}
.date small{{color:var(--mute);font-size:13px}}
ol{{margin:8px 0 0;padding-left:1.4em;font-size:15px;line-height:1.6}}
ol li::marker{{color:var(--pink);font-family:Anton,sans-serif}}
.empty{{color:var(--mute)}}
</style>
</head>
<body>
<main>
  <a class="back" href="../">最新号へ</a>
  <h1>過去の<span>号</span></h1>
  <p class="lead">日付を押すと、その日の号がそのまま読めます。各号の記事は公開時点の内容です。</p>
  {"".join(items) if items else '<p class="empty">まだ過去の号はありません。</p>'}
</main>
</body>
</html>
'''
    open(os.path.join(ARCH, "index.html"), "w", encoding="utf-8").write(page)
    # 号の目録（新しい順）。各号のページ上部の「号をえらぶ」パネルが読み込む
    with open(os.path.join(ARCH, "days.json"), "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(",", ":"))
    return days


def main():
    src = os.path.join(ROOT, "index.html")
    it = read_issue(src)
    dst = os.path.join(ARCH, it["iso"])
    os.makedirs(dst, exist_ok=True)
    # 保存する号では、共有時のURL（og:url）をその日のページにする
    s = open(src, encoding="utf-8").read().replace(
        f'<meta property="og:url" content="{SITE}">',
        f'<meta property="og:url" content="{SITE}archive/{it["iso"]}/">', 1)
    with open(os.path.join(dst, "index.html"), "w", encoding="utf-8") as f:
        f.write(s)
    days = build_list()
    print(f"保存: archive/{it['iso']}/index.html（{len(it['titles'])}本）。過去号は全{len(days)}号。")


if __name__ == "__main__":
    sys.exit(main())
