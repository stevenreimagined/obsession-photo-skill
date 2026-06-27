#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report.py — 选片报告(HTML) / shareable selection report

把 cull.py 的选片结果做成一个**自包含的 HTML 报告**(缩略图内嵌，可直接发给别人，
或用浏览器"打印为 PDF")。按 推荐保留 / 可选 / 建议淘汰 / 技术问题 分区展示，
每张带分数、问题标记、连拍★。

用法 / Usage:
  python3 report.py 照片文件夹/                      # 自动跑cull并出报告
  python3 report.py 照片文件夹/ --csv cull_report.csv # 用已有的cull结果
  python3 report.py 照片文件夹/ -o 报告.html
依赖：pillow(+ 若需现跑cull: opencv/numpy)。
"""
import argparse, os, sys, csv, base64, io, subprocess, html, datetime
from PIL import Image, ImageOps

CATS = ["推荐保留", "可选", "建议淘汰", "技术问题"]
COLOR = {"推荐保留": "#3cb44b", "可选": "#f5c518",
         "建议淘汰": "#8c8c8c", "技术问题": "#e23b3b"}


def thumb_b64(path, px=380):
    try:
        im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        im.thumbnail((px, px))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=80)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser(description="生成HTML选片报告")
    ap.add_argument("folder")
    ap.add_argument("--csv", default=None, help="cull_report.csv路径(没有则自动跑cull)")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--title", default=None)
    args = ap.parse_args()
    if not os.path.isdir(args.folder):
        sys.exit(f"不是文件夹: {args.folder}")

    csv_path = args.csv
    if not csv_path:
        cand = os.path.join(args.folder, "cull_report.csv")
        if os.path.exists(cand):
            csv_path = cand
        else:
            print("未找到 cull_report.csv，正在自动运行 cull.py …")
            here = os.path.dirname(os.path.abspath(__file__))
            subprocess.run([sys.executable, os.path.join(here, "cull.py"),
                            args.folder, "-o", args.folder], check=True)
            csv_path = cand
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    if not rows:
        sys.exit("CSV 为空")

    title = args.title or f"选片报告 · {os.path.basename(os.path.abspath(args.folder))}"
    out = args.output or os.path.join(args.folder, "selection_report.html")

    # 统计
    counts = {c: 0 for c in CATS}
    for r in rows:
        counts[r.get("cat", "可选")] = counts.get(r.get("cat", "可选"), 0) + 1

    parts = [f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>
*{{box-sizing:border-box}} body{{font-family:-apple-system,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif;margin:0;background:#16181c;color:#e8e8e8}}
header{{padding:24px 28px;background:#1f2228;border-bottom:1px solid #333}}
h1{{margin:0 0 6px;font-size:20px}} .sub{{color:#9aa0a6;font-size:13px}}
.summary{{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}}
.pill{{padding:6px 12px;border-radius:20px;font-size:13px;font-weight:600;color:#111}}
section{{padding:18px 28px}}
h2{{font-size:16px;border-left:5px solid;padding-left:10px;margin:24px 0 12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px}}
.card{{background:#23262c;border-radius:10px;overflow:hidden;border:2px solid transparent}}
.card img{{width:100%;display:block;background:#000;aspect-ratio:3/2;object-fit:cover}}
.meta{{padding:8px 10px;font-size:12px;line-height:1.5}}
.fn{{color:#fff;font-weight:600;word-break:break-all}}
.score{{float:right;font-weight:700}} .flags{{color:#c0843a}} .why{{color:#9aa0a6}}
.star{{color:#ffd24a;font-weight:700}}
footer{{padding:18px 28px;color:#777;font-size:12px;border-top:1px solid #333}}
@media print{{body{{background:#fff;color:#000}} .card{{break-inside:avoid}} header,section{{padding:10px}}}}
</style></head><body>
<header><h1>{html.escape(title)}</h1>
<div class="sub">生成时间 {datetime.datetime.now():%Y-%m-%d %H:%M} · 共 {len(rows)} 张 · 仅技术初筛建议，最终由你决定</div>
<div class="summary">"""]
    for c in CATS:
        parts.append(f'<span class="pill" style="background:{COLOR[c]}">{c} {counts.get(c,0)}</span>')
    parts.append("</div></header>")

    for c in CATS:
        items = [r for r in rows if r.get("cat") == c]
        if not items:
            continue
        parts.append(f'<section><h2 style="border-color:{COLOR[c]}">{c}（{len(items)}）</h2><div class="grid">')
        items.sort(key=lambda r: float(r.get("score", 0) or 0), reverse=True)
        for r in items:
            p = os.path.join(args.folder, r["file"])
            b = thumb_b64(p)
            img = f'<img src="data:image/jpeg;base64,{b}">' if b else '<div style="height:140px;background:#000"></div>'
            star = ' <span class="star">★最佳</span>' if str(r.get("best")) == "True" else ""
            flags = html.escape(r.get("flags", "") or "")
            why = html.escape(r.get("why", "") or "")
            parts.append(
                f'<div class="card" style="border-color:{COLOR[c]}">{img}'
                f'<div class="meta"><span class="score" style="color:{COLOR[c]}">{r.get("score","")}</span>'
                f'<span class="fn">{html.escape(r["file"])}</span>{star}'
                f'{("<div class=flags>⚑ "+flags+"</div>") if flags else ""}'
                f'<div class="why">{why}</div></div></div>')
        parts.append("</div></section>")

    parts.append('<footer>Obsession 摄影插件 · 选片报告为技术初筛，表情/情绪/故事性请人工复核。</footer></body></html>')

    with open(out, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    print("✅ 报告已生成:", out)
    print("   用浏览器打开；想要 PDF 就在浏览器里『打印 → 存为 PDF』。")


if __name__ == "__main__":
    main()
