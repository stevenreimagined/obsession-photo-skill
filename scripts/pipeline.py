#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline.py — 一键工作流 / one-command workflows (把各脚本串起来)

newshoot     拍摄前：建标准目录结构(调用 organize scaffold)
postprocess  拍摄后：素材初检 → 选片初筛 → 生成HTML报告(triage→cull→report)

用法 / Usage:
  python3 pipeline.py newshoot --name "Drama Festival" --date 2026-06-27
  python3 pipeline.py postprocess 照片文件夹/ [-o 输出目录]

依赖：随所调用的脚本(cull/triage 需 opencv 等)。
"""
import argparse, os, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, *a):
    print(f"\n{'='*54}\n▶ {script} {' '.join(a)}\n{'='*54}")
    return subprocess.run([sys.executable, os.path.join(HERE, script), *a]).returncode


def newshoot(args):
    a = ["scaffold", "--name", args.name]
    if args.date:
        a += ["--date", args.date]
    if args.cameras:
        a += ["--cameras", *args.cameras]
    if args.outdir:
        a += ["-o", args.outdir]
    run("organize.py", *a)
    print("\n下一步：把素材导入对应机位文件夹后，可用")
    print("  python3 organize.py rename ... --apply   统一命名")
    print("  python3 recommend_settings.py --scene ...  查拍摄参数")


def postprocess(args):
    folder = args.folder
    outdir = args.outdir or folder
    print("拍后流水线：素材初检 → 选片初筛 → 报告")
    run("triage.py", folder, "--csv", os.path.join(outdir, "triage_report.csv"))
    run("cull.py", folder, "-o", outdir)
    run("report.py", folder, "--csv", os.path.join(outdir, "cull_report.csv"),
        "-o", os.path.join(outdir, "selection_report.html"))
    print(f"\n✅ 完成。看这几个产物：")
    print(f"   · {os.path.join(outdir,'selection_report.html')}  (可分享的选片报告)")
    print(f"   · {os.path.join(outdir,'cull_contactsheet.jpg')}  (彩框标注拼图)")
    print(f"   · {os.path.join(outdir,'cull_report.csv')} / triage_report.csv (明细)")
    print("   提醒：以上为技术初筛，表情/情绪/故事性请你人工复核定稿。")


def main():
    ap = argparse.ArgumentParser(description="一键工作流")
    sub = ap.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("newshoot", help="拍前：建目录结构")
    n.add_argument("--name", required=True)
    n.add_argument("--date", default=None)
    n.add_argument("--cameras", nargs="+", default=None)
    n.add_argument("-o", "--outdir", default=None)
    n.set_defaults(func=newshoot)

    p = sub.add_parser("postprocess", help="拍后：初检→选片→报告")
    p.add_argument("folder")
    p.add_argument("-o", "--outdir", default=None)
    p.set_defaults(func=postprocess)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
