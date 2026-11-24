#!/usr/bin/env python3
"""その日の号を過去号として保存し、過去号の一覧ページを作り直す。

使い方（リポジトリの一番上で）:  python3 tools/publish_day.py
- index.html の ISSUE.date から日付を読み、archive/YYYY-MM-DD/index.html にそのままコピーする。
- archive/ 以下の全号から archive/index.html（過去号の一覧）を作り直す。
"""
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = os.path.join(ROOT, "archive")
WD = "月火水木金土日"


def read_issue(path):
    s = open(path, encoding="utf-8").read()
    m = re.search(r'const ISSUE = \{date:"(\d{4})\.(\d{2})\.(\d{2})[^"]*"', s)
    if not m:
        raise SystemExit(f"ISSUE.date が見つかりません: {path}")
    y, mo, d = m.groups()
    i = s.index("const NEWS = [")
    j = s.index("const ORDER", i)
    block = s[i:j]
    titles = [json.loads('"' + t + '"') for t in re.findall(r'"?title"?\s*:\s*"((?:[^"\\]|\\.)*)"', block)]
    titles = [re.sub(r"<[^>]+>", "", t) for t in titles]
    om = re.search(r"const ORDER = \[([^\]]*)\]", s)
    order = [int(x) for x in om.group(1).split(",") if x.strip()] if om else list(range(len(titles)))
    cats = re.findall(r'"?cat"?\s*:\s*"(world|tech|sports)"', block)
    return dict(iso=f"{y}-{mo}-{d}", y=int(y), m=int(mo), d=int(d),
                titles=[titles[k] for k in order if k < len(titles)],
                cats=[cats[k] for k in order if k < len(cats)])


def weekday(y, m, d):
    import datetime
    return WD[datetime.date(y, m, d).weekday()]


def build_list():
    days = sorted([d for d in os.listdir(ARCH) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)
                   and os.path.exists(os.path.join(ARCH, d, "index.html"))], reverse=True)
    items = []
    for d in days:
        it = read_issue(os.path.join(ARCH, d, "index.html"))
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
<title>過去の号｜ドパガキニュース</title>
<meta name="description" content="ドパガキニュースの過去の号の一覧">
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
    return days


def main():
    src = os.path.join(ROOT, "index.html")
    it = read_issue(src)
    dst = os.path.join(ARCH, it["iso"])
    os.makedirs(dst, exist_ok=True)
    shutil.copyfile(src, os.path.join(dst, "index.html"))
    days = build_list()
    print(f"保存: archive/{it['iso']}/index.html（{len(it['titles'])}本）。過去号は全{len(days)}号。")


if __name__ == "__main__":
    sys.exit(main())
